# -*- coding=utf-8 -*-
import io
import os
import time

import requests
import web
from wechatpy.enterprise import create_reply, parse_message
from wechatpy.enterprise.crypto import WeChatCrypto
from wechatpy.enterprise.exceptions import InvalidCorpIdException
from wechatpy.exceptions import InvalidSignatureException, WeChatClientException

from bridge.context import Context
from bridge.reply import Reply, ReplyType
from channel.chat_channel import ChatChannel
from channel.wechatcom.wechatcomapp_client import WechatComAppClient
from channel.wechatcom.wechatcomapp_message import WechatComAppMessage
from common.log import logger
from common.singleton import singleton
from common.utils import compress_imgfile, fsize, split_string_by_utf8_length
from config import conf, subscribe_msg
from voice.audio_convert import any_to_amr, split_audio

import json
import xml.etree.ElementTree as ET

MAX_UTF8_LEN = 2048


@singleton
class WechatComAppChannel(ChatChannel):
    NOT_SUPPORT_REPLYTYPE = []

    def __init__(self):
        super().__init__()
        self.corp_id = conf().get("wechatcom_corp_id")
        self.secret = conf().get("wechatcomapp_secret")
        self.agent_id = conf().get("wechatcomapp_agent_id")
        self.token = conf().get("wechatcomapp_token")
        self.aes_key = conf().get("wechatcomapp_aes_key")
        print(self.corp_id, self.secret, self.agent_id, self.token, self.aes_key)
        logger.info(
            "[wechatcom] init: corp_id: {}, secret: {}, agent_id: {}, token: {}, aes_key: {}".format(self.corp_id, self.secret, self.agent_id, self.token, self.aes_key)
        )
        self.crypto = WeChatCrypto(self.token, self.aes_key, self.corp_id)
        self.client = WechatComAppClient(self.corp_id, self.secret)
        self.text_after_voice = conf().get("text_after_voice", False)
        self.customer_servcie_mode = False

    def startup(self):
        # start message listener
        urls = (conf().get("wechatcomapp_url", "/wxcomapp"), "channel.wechatcom.wechatcomapp_channel.Query")
        app = web.application(urls, globals(), autoreload=False)
        port = conf().get("wechatcomapp_port", 9898)
        web.httpserver.runsimple(app.wsgifunc(), ("0.0.0.0", port))

    def send(self, reply: Reply, context: Context):
        receiver = context["receiver"]
        logger.debug("[wechatcom] context {} ".format(context.kwargs['msg']))
        external_userid = context.kwargs['msg'].external_userid  # from_user_id
        open_kfid = context.kwargs['msg'].open_kfid  # to_user_id,也就是客服id
        if open_kfid:
            self.customer_servcie_mode = True
            receiver = external_userid  # 客服模式下，external_userid 就是客户id
            self.agent_id = open_kfid  # 客服模式下，agent_id 就是客服id
        else:
            self.customer_servcie_mode = False

        if reply.type in [ReplyType.TEXT, ReplyType.ERROR, ReplyType.INFO]:
            reply_text = reply.content
            texts = split_string_by_utf8_length(reply_text, MAX_UTF8_LEN)
            if len(texts) > 1:
                logger.info("[wechatcom] text too long, split into {} parts".format(len(texts)))
            for i, text in enumerate(texts):
                self.send_text_message(self.agent_id, receiver, text)

                if i != len(texts) - 1:
                    time.sleep(0.5)  # 休眠0.5秒，防止发送过快乱序
            logger.info("[wechatcom] Do send text to {}: {}".format(receiver, reply_text))
        elif reply.type == ReplyType.VOICE:
            try:
                media_ids = []
                file_path = reply.content
                amr_file = os.path.splitext(file_path)[0] + ".amr"
                any_to_amr(file_path, amr_file)
                duration, files = split_audio(amr_file, 60 * 1000)
                if len(files) > 1:
                    logger.info("[wechatcom] voice too long {}s > 60s , split into {} parts".format(duration / 1000.0, len(files)))
                for path in files:
                    response = self.client.media.upload("voice", open(path, "rb"))
                    logger.debug("[wechatcom] upload voice response: {}".format(response))
                    media_ids.append(response["media_id"])
            except WeChatClientException as e:
                logger.error("[wechatcom] upload voice failed: {}".format(e))
                return
            try:
                os.remove(file_path)
                if amr_file != file_path:
                    os.remove(amr_file)
            except Exception:
                pass
            for media_id in media_ids:
                self.send_voice_message(self.agent_id, receiver, media_id)
                time.sleep(1)
            logger.info("[wechatcom] sendVoice={}, receiver={}".format(reply.content, receiver))

            # if need text_after_voice
            if self.text_after_voice and reply.orig_content:
                logger.debug("[wechatcom] send text after voice: {}".format(reply.orig_content))
                self.send_text_message(self.agent_id, receiver, reply.orig_content)

        elif reply.type == ReplyType.IMAGE_URL:  # 从网络下载图片
            img_url = reply.content
            pic_res = requests.get(img_url, stream=True)
            image_storage = io.BytesIO()
            for block in pic_res.iter_content(1024):
                image_storage.write(block)
            sz = fsize(image_storage)
            if sz >= 10 * 1024 * 1024:
                logger.info("[wechatcom] image too large, ready to compress, sz={}".format(sz))
                image_storage = compress_imgfile(image_storage, 10 * 1024 * 1024 - 1)
                logger.info("[wechatcom] image compressed, sz={}".format(fsize(image_storage)))
            image_storage.seek(0)
            try:
                response = self.client.media.upload("image", image_storage)
                logger.debug("[wechatcom] upload image response: {}".format(response))
            except WeChatClientException as e:
                logger.error("[wechatcom] upload image failed: {}".format(e))
                return

            self.send_image_message(self.agent_id, receiver, response["media_id"])
            logger.info("[wechatcom] sendImage url={}, receiver={}".format(img_url, receiver))
        elif reply.type == ReplyType.IMAGE:  # 从文件读取图片
            image_storage = reply.content
            sz = fsize(image_storage)
            if sz >= 10 * 1024 * 1024:
                logger.info("[wechatcom] image too large, ready to compress, sz={}".format(sz))
                image_storage = compress_imgfile(image_storage, 10 * 1024 * 1024 - 1)
                logger.info("[wechatcom] image compressed, sz={}".format(fsize(image_storage)))
            image_storage.seek(0)
            try:
                response = self.client.media.upload("image", image_storage)
                logger.debug("[wechatcom] upload image response: {}".format(response))
            except WeChatClientException as e:
                logger.error("[wechatcom] upload image failed: {}".format(e))
                return
            self.send_image_message(self.agent_id, receiver, response["media_id"])
            logger.info("[wechatcom] sendImage, receiver={}".format(receiver))

    def send_text_message(self, agent_id, receiver, content):
        if not self.customer_servcie_mode:
            return self.client.message.send_text(agent_id, receiver, content)            

        url = f"https://qyapi.weixin.qq.com/cgi-bin/kf/send_msg?access_token={self.client.fetch_access_token_cs()}"
        data = {
            "touser": receiver,
            "open_kfid": agent_id,
            "msgtype": "text",
            "text": {"content": content}
        }

        response = requests.post(url, json=data)
        return response.json()

    def send_image_message(self, agent_id, receiver, media_id):
        if not self.customer_servcie_mode:
            return self.client.message.send_image(agent_id, receiver, media_id)   
                
        url = f"https://qyapi.weixin.qq.com/cgi-bin/kf/send_msg?access_token={self.client.fetch_access_token_cs()}"
        data = {
            "touser": receiver,
            "open_kfid": agent_id,
            "msgtype": "image",
            "image": {"media_id": media_id}
        }

        response = requests.post(url, json=data).json()
        if response['errmsg'] == 'ok':
            logger.debug(f"Send IMAGE Message Success")
        else:
            logger.error(f"Something error:{response}")
        return response

    def send_voice_message(self, agent_id, receiver, media_id):
        if not self.customer_servcie_mode:
            return self.client.message.send_voice(agent_id, receiver, media_id)   
                
        url = f"https://qyapi.weixin.qq.com/cgi-bin/kf/send_msg?access_token={self.client.fetch_access_token_cs()}"
        data = {
            "touser": receiver,
            "open_kfid": agent_id,
            "msgtype": "voice",
            "voice": {"media_id": media_id}
        }

        response = requests.post(url, json=data).json()
        if response['errmsg'] == 'ok':
            logger.debug(f"Send VOICE Message Success")
        else:
            logger.error(f"Something error:{response}")
        return response

    def get_latest_message(self, token, open_kfid, next_cursor=""):
        url = f"https://qyapi.weixin.qq.com/cgi-bin/kf/sync_msg?access_token={self.client.fetch_access_token_cs()}"
        data = {
            "token": token,
            "open_kfid": open_kfid,
            "limit": 1000
        }
        if next_cursor:
            data["cursor"] = next_cursor

        response = requests.post(url, json=data)
        response_data = response.json()

        # 检查是否有错误码并打印相关错误信息
        if response_data.get("errcode") != 0:
            logger.error(
                f"[ERROR][{response_data.get('errcode')}][{response_data.get('errmsg')}] - Failed to fetch messages, more info at {response_data.get('more_info') or 'https://open.work.weixin.qq.com/devtool/query?e=' + str(response_data.get('errcode'))}")
            return None

        logger.debug(f"response_data:{response_data}")
        if response_data.get("msg_list"):
            return response_data["msg_list"][-1]  # 返回最新的一条消息
        else:
            return None
class Query:
    def GET(self):
        channel = WechatComAppChannel()
        params = web.input()
        logger.info("[wechatcom] receive params: {}".format(params))
        try:
            signature = params.msg_signature
            timestamp = params.timestamp
            nonce = params.nonce
            echostr = params.echostr
            echostr = channel.crypto.check_signature(signature, timestamp, nonce, echostr)
        except InvalidSignatureException:
            logger.error("[wechatcom] Invalid signature in GET request")
            raise web.Forbidden()
        return echostr

    def POST(self):
        channel = WechatComAppChannel()
        params = web.input()
        logger.info("[wechatcom] receive params: {}".format(params))
        customer_service_mode = False
        try:
            signature = params.msg_signature
            timestamp = params.timestamp
            nonce = params.nonce
            message = channel.crypto.decrypt_message(web.data(), signature, timestamp, nonce)
            logger.debug("[wechatcom] receive message: {}".format(message))

            try:
                xml_tree = ET.fromstring(message)
                logger.debug("[wechatcom] xml_tree: {}".format(xml_tree))            
                if xml_tree.tag == "xml":
                    # 客服消息
                    customer_service_mode = True
                    # msg_type = xml_tree.find("MsgType").text
                    # event = xml_tree.find("Event").text if xml_tree.find("Event") is not None else ""                    
                    return self.POST_customer_service(channel, xml_tree)
            except ET.ParseError as e:
                logger.debug(f"[wechatcs] XML Parse Error: {e}")

        except (InvalidSignatureException, InvalidCorpIdException):
            raise web.Forbidden()
        
        msg = parse_message(message)
        logger.debug("[wechatcom] receive message: {}, msg= {}".format(message, msg))
        if msg.type == "event":
            if msg.event == "subscribe":
                reply_content = subscribe_msg()
                if reply_content:
                    reply = create_reply(reply_content, msg).render()
                    res = channel.crypto.encrypt_message(reply, nonce, timestamp)
                    return res
        else:
            try:
                wechatcom_msg = WechatComAppMessage(msg, client=channel.client)
            except NotImplementedError as e:
                logger.debug("[wechatcom] " + str(e))
                return "success"
            context = channel._compose_context(
                wechatcom_msg.ctype,
                wechatcom_msg.content,
                isgroup=False,
                msg=wechatcom_msg,
            )
            if context:
                channel.produce(context)
        return "success"

    def POST_customer_service(self, channel, xml_tree):
        # 解析XML格式的消息
        msg_type = xml_tree.find("MsgType").text
        event = xml_tree.find("Event").text if xml_tree.find("Event") is not None else ""

        if msg_type == "event" and event == "kf_msg_or_event":
            # 在这里处理特定事件
            # 示例代码，根据实际情况修改
            token = xml_tree.find("Token").text
            open_kfid = xml_tree.find("OpenKfId").text
            next_cursor = ""  # 第一次请求时不需要提供 cursor

            latest_message = channel.get_latest_message(token, open_kfid, next_cursor)
            logger.debug(f"[wechatcs] latest_message: {latest_message}")
            try:
                wechatcom_copy_msg = WechatComAppMessage(msg=latest_message, client=channel.client, customer_service_mode=True)
                logger.debug(f"[wechatcs] wechatcom_copy_msg: {wechatcom_copy_msg}")
            except NotImplementedError as e:
                logger.debug("[wechatcs] " + str(e))
                return "success"
            context = channel._compose_context(
                wechatcom_copy_msg.ctype,
                wechatcom_copy_msg.content,
                isgroup=False,
                msg=wechatcom_copy_msg,
            )
            logger.debug(f"[wechatcs] context: {context}")
            if context:
                channel.produce(context)
            logger.debug(f"[wechatcs] get latest message: {latest_message}")
            return json.dumps({"status": "success"})
        else:
            return "Unsupported event type"

