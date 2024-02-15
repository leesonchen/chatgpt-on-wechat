# -*- coding: utf-8 -*-
import asyncio
import imghdr
import io
import json
import os
import threading
import time

import requests
import web
from wechatpy.crypto import WeChatCrypto
from wechatpy.exceptions import WeChatClientException
from collections import defaultdict

from bridge.context import *
from bridge.reply import *
from channel.chat_channel import ChatChannel
from channel.wechatmp.common import *
from channel.wechatmp.wechatmp_client import WechatMPClient
from common.log import logger
from common.singleton import singleton
from common.utils import split_string_by_utf8_length
from config import conf
from voice.audio_convert import any_to_mp3, split_audio

# If using SSL, uncomment the following lines, and modify the certificate path.
# from cheroot.server import HTTPServer
# from cheroot.ssl.builtin import BuiltinSSLAdapter
# HTTPServer.ssl_adapter = BuiltinSSLAdapter(
#         certificate='/ssl/cert.pem',
#         private_key='/ssl/cert.key')


@singleton
class WechatMPChannel(ChatChannel):
    def __init__(self, passive_reply=True):
        super().__init__()
        self.passive_reply = passive_reply
        self.NOT_SUPPORT_REPLYTYPE = []
        self.text_after_voice = conf().get("text_after_voice", False)
        self.voice_as_file = conf().get("voice_as_file", False)
        appid = conf().get("wechatmp_app_id")
        secret = conf().get("wechatmp_app_secret")
        token = conf().get("wechatmp_token")
        aes_key = conf().get("wechatmp_aes_key")
        self.client = WechatMPClient(appid, secret)
        self.crypto = None
        if aes_key:
            self.crypto = WeChatCrypto(token, aes_key, appid)
        if self.passive_reply:
            # Cache the reply to the user's first message
            self.cache_dict = defaultdict(list)
            # Record whether the current message is being processed
            self.running = set()
            # Count the request from wechat official server by message_id
            self.request_cnt = dict()
            # The permanent media need to be deleted to avoid media number limit
            self.delete_media_loop = asyncio.new_event_loop()
            t = threading.Thread(target=self.start_loop, args=(self.delete_media_loop,))
            t.setDaemon(True)
            t.start()
        else:
            thumb_path = 'voice_pic.png'
            thumb_type = 'image/png'
            # self.voice_thumb_id = self.client.media.upload("thumb", (thumb_path, open(thumb_path, "rb"), thumb_type))["thumb_media_id"]
            self.voice_thumb_id = self.client.material.add("image", (thumb_path, open(thumb_path, "rb"), thumb_type))["media_id"]
            logger.info("[wechatmp] thumb uploaded, thumb_id={}".format(self.voice_thumb_id))

    def startup(self):
        if self.passive_reply:
            urls = ("/wx", "channel.wechatmp.passive_reply.Query")
        else:
            urls = ("/wx", "channel.wechatmp.active_reply.Query")
        app = web.application(urls, globals(), autoreload=False)
        port = conf().get("wechatmp_port", 8080)
        web.httpserver.runsimple(app.wsgifunc(), ("0.0.0.0", port))

    def start_loop(self, loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    async def delete_media(self, media_id):
        logger.debug("[wechatmp] permanent media {} will be deleted in 10s".format(media_id))
        await asyncio.sleep(10)
        self.client.material.delete(media_id)
        logger.info("[wechatmp] permanent media {} has been deleted".format(media_id))

    def delete_file(self, path, wait_seconds=10):
        import threading
        thread = threading.Thread(target=self._delete_file, args=(path, wait_seconds))
        thread.start()

    def _delete_file(self, path, wait_seconds):
        logger.debug("[wechatmp] file {} will be deleted in 10s".format(path))
        time.sleep(wait_seconds)
        try:
            os.remove(path)
            logger.info("[wechatmp] file {} has been deleted".format(path))
        except Exception as e:
            logger.error("[wechatmp] file {} delete failed: {}".format(path, e))

    def send(self, reply: Reply, context: Context):
        context['wait_for_reply'] = False
        receiver = context["receiver"]
        if self.passive_reply:
            if reply.type == ReplyType.TEXT or reply.type == ReplyType.INFO or reply.type == ReplyType.ERROR:
                reply_text = reply.content
                logger.info("[wechatmp] text cached, receiver {}\n{}".format(receiver, reply_text))
                self.cache_dict[receiver].append(("text", reply_text))
            elif reply.type == ReplyType.VOICE:
                voice_file_path = reply.content
                duration, files = split_audio(voice_file_path, 60 * 1000)
                if len(files) > 1:
                    logger.info("[wechatmp] voice too long {}s > 60s , split into {} parts".format(duration / 1000.0, len(files)))

                for path in files:
                    # support: <2M, <60s, mp3/wma/wav/amr
                    try:
                        with open(path, "rb") as f:
                            response = self.client.material.add("voice", f)
                            logger.debug("[wechatmp] upload voice response: {}".format(response))
                            f_size = os.fstat(f.fileno()).st_size
                            time.sleep(1.0 + 2 * f_size / 1024 / 1024)
                            # todo check media_id
                    except WeChatClientException as e:
                        logger.error("[wechatmp] upload voice failed: {}".format(e))
                        return
                    media_id = response["media_id"]
                    logger.info("[wechatmp] voice uploaded, receiver {}, media_id {}".format(receiver, media_id))
                    self.cache_dict[receiver].append(("voice", media_id))

            elif reply.type == ReplyType.IMAGE_URL:  # 从网络下载图片
                img_url = reply.content
                pic_res = requests.get(img_url, stream=True)
                image_storage = io.BytesIO()
                for block in pic_res.iter_content(1024):
                    image_storage.write(block)
                image_storage.seek(0)
                image_type = imghdr.what(image_storage)
                filename = receiver + "-" + str(context["msg"].msg_id) + "." + image_type
                content_type = "image/" + image_type
                try:
                    response = self.client.material.add("image", (filename, image_storage, content_type))
                    logger.debug("[wechatmp] upload image response: {}".format(response))
                except WeChatClientException as e:
                    logger.error("[wechatmp] upload image failed: {}".format(e))
                    return
                media_id = response["media_id"]
                logger.info("[wechatmp] image uploaded, receiver {}, media_id {}".format(receiver, media_id))
                self.cache_dict[receiver].append(("image", media_id))
            elif reply.type == ReplyType.IMAGE:  # 从文件读取图片
                image_storage = reply.content
                image_storage.seek(0)
                image_type = imghdr.what(image_storage)
                filename = receiver + "-" + str(context["msg"].msg_id) + "." + image_type
                content_type = "image/" + image_type
                try:
                    response = self.client.material.add("image", (filename, image_storage, content_type))
                    logger.debug("[wechatmp] upload image response: {}".format(response))
                except WeChatClientException as e:
                    logger.error("[wechatmp] upload image failed: {}".format(e))
                    return
                media_id = response["media_id"]
                logger.info("[wechatmp] image uploaded, receiver {}, media_id {}".format(receiver, media_id))
                self.cache_dict[receiver].append(("image", media_id))
        else:
            if reply.type == ReplyType.TEXT or reply.type == ReplyType.INFO or reply.type == ReplyType.ERROR:
                reply_text = reply.content
                texts = split_string_by_utf8_length(reply_text, MAX_UTF8_LEN)
                if len(texts) > 1:
                    logger.info("[wechatmp] text too long, split into {} parts".format(len(texts)))
                for i, text in enumerate(texts):
                    self.client.message.send_text(receiver, text)
                    if i != len(texts) - 1:
                        time.sleep(0.5)  # 休眠0.5秒，防止发送过快乱序
                logger.info("[wechatmp] Do send text to {}: {}".format(receiver, reply_text))
            elif reply.type == ReplyType.VOICE:
                send_voice_as_file = self.voice_as_file
                try:
                    file_path = reply.content
                    self.delete_file(file_path, 60)

                    file_name = os.path.basename(file_path)
                    file_type = os.path.splitext(file_name)[1]
                    if file_type == ".mp3":
                        file_type = "audio/mpeg"
                    elif file_type == ".amr":
                        file_type = "audio/amr"
                    else:
                        mp3_file = os.path.splitext(file_path)[0] + ".mp3"
                        any_to_mp3(file_path, mp3_file)
                        file_path = mp3_file
                        file_name = os.path.basename(file_path)
                        file_type = "audio/mpeg"
                        self.delete_file(file_path, 60)

                    logger.info("[wechatmp] file_name: {}, file_type: {} ".format(file_name, file_type))

                    # if send file rather than voice
                    if send_voice_as_file:
                        import requests
                        upload_url = conf().get('file_upload_url', '')  # 替换为你的Web服务器上传URL
                        if not upload_url:
                            logger.error("[wechatmp] file_upload_url is empty")
                            send_voice_as_file = False
                        else:
                            upload_token = conf().get('file_upload_token', '')
                            files = {'file': open(file_path, 'rb')}
                            data = {'token': upload_token}

                            response = requests.post(upload_url, data=data, files=files)
                            if response.status_code != 200:
                                logger.error("[wechatmp] file upload failed, status_code: {}; error: {}".format(response.status_code, response.text))
                                send_voice_as_file = False
                            else:
                                result = json.loads(response.text)
                                logger.info("[wechatmp] file upload result: {}; response={}".format(result, response.text))

                                download_url = result['download_url']
                                expire_seconds = result['expires']  # 文件有效期
                                expire_minute = int(expire_seconds / 60)
                                logger.info(f"文件下载链接：{download_url}")
                                self.client.message.send_music(receiver, download_url, download_url, self.voice_thumb_id, \
                                                               '语音消息', f'[有效期{expire_minute}分钟请尽快收听]')
                    if not send_voice_as_file:
                        media_ids = []
                        duration, files = split_audio(file_path, 60 * 1000)
                        if len(files) > 1:
                            logger.info("[wechatmp] voice too long {}s > 60s , split into {} parts".format(duration / 1000.0, len(files)))

                        for path in files:
                            # support: <2M, <60s, AMR\MP3
                            response = self.client.media.upload("voice", (os.path.basename(path), open(path, "rb"), file_type))
                            logger.debug("[wechatcom] upload voice response: {}".format(response))
                            media_ids.append(response["media_id"])
                            if len(files) > 1:
                                self.delete_file(path)

                        for media_id in media_ids:
                            self.client.message.send_voice(receiver, media_id)
                            time.sleep(1)

                except WeChatClientException as e:
                    logger.error("[wechatmp] upload voice failed: {}".format(e))
                    return
                except Exception as e:
                    logger.error("[wechatmp] send voice failed: {}".format(e))
                    return

                logger.info("[wechatmp] Do send voice to {}".format(receiver))

                # if need text_after_voice
                if self.text_after_voice and reply.orig_content:
                    self.client.message.send_text(receiver, reply.orig_content)

            elif reply.type == ReplyType.IMAGE_URL:  # 从网络下载图片
                img_url = reply.content
                pic_res = requests.get(img_url, stream=True)
                image_storage = io.BytesIO()
                for block in pic_res.iter_content(1024):
                    image_storage.write(block)
                image_storage.seek(0)
                image_type = imghdr.what(image_storage)
                filename = receiver + "-" + str(context["msg"].msg_id) + "." + image_type
                content_type = "image/" + image_type
                try:
                    response = self.client.media.upload("image", (filename, image_storage, content_type))
                    logger.debug("[wechatmp] upload image response: {}".format(response))
                except WeChatClientException as e:
                    logger.error("[wechatmp] upload image failed: {}".format(e))
                    return
                self.client.message.send_image(receiver, response["media_id"])
                logger.info("[wechatmp] Do send image to {}".format(receiver))
            elif reply.type == ReplyType.IMAGE:  # 从文件读取图片
                image_storage = reply.content
                image_storage.seek(0)
                image_type = imghdr.what(image_storage)
                filename = receiver + "-" + str(context["msg"].msg_id) + "." + image_type
                content_type = "image/" + image_type
                try:
                    response = self.client.media.upload("image", (filename, image_storage, content_type))
                    logger.debug("[wechatmp] upload image response: {}".format(response))
                except WeChatClientException as e:
                    logger.error("[wechatmp] upload image failed: {}".format(e))
                    return
                self.client.message.send_image(receiver, response["media_id"])
                logger.info("[wechatmp] Do send image to {}".format(receiver))
        return

    def _success_callback(self, session_id, context, **kwargs):  # 线程异常结束时的回调函数
        logger.debug("[wechatmp] Success to generate reply, msgId={}".format(context["msg"].msg_id))
        if self.passive_reply:
            self.running.remove(session_id)

    def _fail_callback(self, session_id, exception, context, **kwargs):  # 线程异常结束时的回调函数
        logger.exception("[wechatmp] Fail to generate reply to user, msgId={}, exception={}".format(context["msg"].msg_id, exception))
        if self.passive_reply:
            assert session_id not in self.cache_dict
            self.running.remove(session_id)
