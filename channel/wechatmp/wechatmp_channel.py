# -*- coding: utf-8 -*-
import asyncio
import imghdr
import io
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
from common.utils import split_string_by_utf8_length, remove_markdown_symbol
from config import conf
from voice.audio_convert import any_to_mp3, split_audio
import base64

# If using SSL, uncomment the following lines, and modify the certificate path.
# from cheroot.server import HTTPServer
# from cheroot.ssl.builtin import BuiltinSSLAdapter
# HTTPServer.ssl_adapter = BuiltinSSLAdapter(
#         certificate='/ssl/cert.pem',
#         private_key='/ssl/cert.key')

class BackendMessage:
    def __init__(self, receiver, content):
        self.receiver = receiver
        self.content = content
@singleton
class WechatMPChannel(ChatChannel):
    def __init__(self, passive_reply=True):
        super().__init__()
        self.passive_reply = passive_reply
        self.NOT_SUPPORT_REPLYTYPE = []
        self.text_after_voice = conf().get("text_after_voice", False)
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
        self.backend_task_loop = asyncio.new_event_loop()
        self.message_queue = asyncio.Queue(maxsize=1000)
        t = threading.Thread(target=self.start_loop, args=(self.backend_task_loop,))
        t.setDaemon(True)
        t.start()
        asyncio.run_coroutine_threadsafe(self.handle_message(), self.backend_task_loop)

    def startup(self):
        # 创建自定义菜单
        self.create_menu()

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

    def send(self, reply: Reply, context: Context):
        context['wait_for_reply'] = False
        receiver = context["receiver"]
        if self.passive_reply:
            if reply.type == ReplyType.TEXT or reply.type == ReplyType.INFO or reply.type == ReplyType.ERROR:
                reply_text = remove_markdown_symbol(reply.content)
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
            elif reply.type == ReplyType.VIDEO_URL:  # 从网络下载视频
                video_url = reply.content
                video_res = requests.get(video_url, stream=True)
                video_storage = io.BytesIO()
                for block in video_res.iter_content(1024):
                    video_storage.write(block)
                video_storage.seek(0)
                video_type = 'mp4'
                filename = receiver + "-" + str(context["msg"].msg_id) + "." + video_type
                content_type = "video/" + video_type
                try:
                    response = self.client.material.add("video", (filename, video_storage, content_type))
                    logger.debug("[wechatmp] upload video response: {}".format(response))
                except WeChatClientException as e:
                    logger.error("[wechatmp] upload video failed: {}".format(e))
                    return
                media_id = response["media_id"]
                logger.info("[wechatmp] video uploaded, receiver {}, media_id {}".format(receiver, media_id))
                self.cache_dict[receiver].append(("video", media_id))

            elif reply.type == ReplyType.VIDEO:  # 从文件读取视频
                video_storage = reply.content
                video_storage.seek(0)
                video_type = 'mp4'
                filename = receiver + "-" + str(context["msg"].msg_id) + "." + video_type
                content_type = "video/" + video_type
                try:
                    response = self.client.material.add("video", (filename, video_storage, content_type))
                    logger.debug("[wechatmp] upload video response: {}".format(response))
                except WeChatClientException as e:
                    logger.error("[wechatmp] upload video failed: {}".format(e))
                    return
                media_id = response["media_id"]
                logger.info("[wechatmp] video uploaded, receiver {}, media_id {}".format(receiver, media_id))
                self.cache_dict[receiver].append(("video", media_id))

        else:
            if reply.type == ReplyType.TEXT or reply.type == ReplyType.INFO or reply.type == ReplyType.ERROR:
                reply_text = reply.content
                texts = split_string_by_utf8_length(reply_text, MAX_UTF8_LEN)
                if len(texts) > 1:
                    logger.info("[wechatmp] text too long, split into {} parts".format(len(texts)))
                for i, text in enumerate(texts):
                    self.send_text_message(receiver, text)
                    if i != len(texts) - 1:
                        time.sleep(0.5)  # 休眠0.5秒，防止发送过快乱序
                logger.info("[wechatmp] Do send text to {}: {}".format(receiver, reply_text))
            elif reply.type == ReplyType.VOICE:
                try:
                    file_path = reply.content
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
                    logger.info("[wechatmp] file_name: {}, file_type: {} ".format(file_name, file_type))
                    media_ids = []
                    duration, files = split_audio(file_path, 60 * 1000)
                    if len(files) > 1:
                        logger.info("[wechatmp] voice too long {}s > 60s , split into {} parts".format(duration / 1000.0, len(files)))
                    for path in files:
                        # support: <2M, <60s, AMR\MP3
                        response = self.client.media.upload("voice", (os.path.basename(path), open(path, "rb"), file_type))
                        logger.debug("[wechatcom] upload voice response: {}".format(response))
                        media_ids.append(response["media_id"])
                        os.remove(path)
                except WeChatClientException as e:
                    logger.error("[wechatmp] upload voice failed: {}".format(e))
                    return

                try:
                    os.remove(file_path)
                except Exception:
                    pass

                for media_id in media_ids:
                    self.client.message.send_voice(receiver, media_id)
                    time.sleep(1)
                logger.info("[wechatmp] Do send voice to {}".format(receiver))

                # if need text_after_voice
                if self.text_after_voice and reply.orig_content:
                    logger.debug("[wechatmp] send text after voice: {}".format(reply.orig_content))
                    self.client.message.send_text(receiver, reply.orig_content)

            elif reply.type == ReplyType.IMAGE_URL:  # 从网络下载图片
                img_url = reply.content

                # open_ai接口
                # pic_res = requests.get(img_url, stream=True)
                # image_storage = io.BytesIO()
                # for block in pic_res.iter_content(1024):
                #     image_storage.write(block)
                # image_storage.seek(0)

                # sd接口
                image_storage = io.BytesIO(base64.b64decode(img_url))

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
            elif reply.type == ReplyType.VIDEO_URL:  # 从网络下载视频
                video_url = reply.content
                video_res = requests.get(video_url, stream=True)
                video_storage = io.BytesIO()
                for block in video_res.iter_content(1024):
                    video_storage.write(block)
                video_storage.seek(0)
                video_type = 'mp4'
                filename = receiver + "-" + str(context["msg"].msg_id) + "." + video_type
                content_type = "video/" + video_type
                try:
                    response = self.client.media.upload("video", (filename, video_storage, content_type))
                    logger.debug("[wechatmp] upload video response: {}".format(response))
                except WeChatClientException as e:
                    logger.error("[wechatmp] upload video failed: {}".format(e))
                    return
                self.client.message.send_video(receiver, response["media_id"])
                logger.info("[wechatmp] Do send video to {}".format(receiver))
            elif reply.type == ReplyType.VIDEO:  # 从文件读取视频
                video_storage = reply.content
                video_storage.seek(0)
                video_type = 'mp4'
                filename = receiver + "-" + str(context["msg"].msg_id) + "." + video_type
                content_type = "video/" + video_type
                try:
                    response = self.client.media.upload("video", (filename, video_storage, content_type))
                    logger.debug("[wechatmp] upload video response: {}".format(response))
                except WeChatClientException as e:
                    logger.error("[wechatmp] upload video failed: {}".format(e))
                    return
                self.client.message.send_video(receiver, response["media_id"])
                logger.info("[wechatmp] Do send video to {}".format(receiver))
        return

    async def put_message(self, msg : BackendMessage):
        logger.debug("[wechatmp] before put message, queue size: {}".format(self.message_queue.qsize()))
        await asyncio.sleep(600)
        await self.message_queue.put(msg)
        logger.debug("[wechatmp] after put message, queue size: {}".format(self.message_queue.qsize()))

    async def handle_message(self):
        logger.debug("[wechatmp] handle_message started.")
        while True:
            logger.debug("[wechatmp] handle_message running")
            msg = await self.message_queue.get()
            logger.debug("[wechatmp] handle message: {}, content: {}, receiver: {} ".format(msg, msg.content, msg.receiver))
            # self.client.message.send_text(msg.receiver, msg.content)

    def send_text_message(self, receiver, content):
        asyncio.run_coroutine_threadsafe(self.put_message(BackendMessage(receiver, "[重播]" + content)), self.backend_task_loop)
        return self.client.message.send_text(receiver, content)

    def _success_callback(self, session_id, context, **kwargs):  # 线程异常结束时的回调函数
        logger.debug("[wechatmp] Success to generate reply, msgId={}".format(context["msg"].msg_id))
        if self.passive_reply:
            self.running.remove(session_id)

    def _fail_callback(self, session_id, exception, context, **kwargs):  # 线程异常结束时的回调函数
        logger.exception("[wechatmp] Fail to generate reply to user, msgId={}, exception={}".format(context["msg"].msg_id, exception))
        if self.passive_reply:
            assert session_id not in self.cache_dict
            self.running.remove(session_id)

    def create_menu(self):
        """创建自定义菜单"""
        try:
            menu_data = {
                "button": [
                    {
                        "type": "click",
                        "name": "智能对话",
                        "key": "CHAT_MODE"
                    },
                    {
                        "name": "立志管理",
                        "sub_button": [
                            {
                                "type": "click",
                                "name": "立志",
                                "key": "SET_GOAL"
                            },
                            {
                                "type": "click",
                                "name": "打卡",
                                "key": "CHECK_IN"
                            },
                            {
                                "type": "click",
                                "name": "我的目标",
                                "key": "MY_GOALS"
                            },
                            {
                                "type": "click",
                                "name": "目标统计",
                                "key": "GOAL_STATS"
                            }
                        ]
                    },
                    {
                        "name": "帮助",
                        "sub_button": [
                            {
                                "type": "click",
                                "name": "使用说明",
                                "key": "HELP"
                            },
                            {
                                "type": "click",
                                "name": "联系客服",
                                "key": "CONTACT"
                            }
                        ]
                    }
                ]
            }
            result = self.client.menu.create(menu_data)
            logger.info(f"[wechatmp] 创建自定义菜单成功: {result}")
            return result
        except Exception as e:
            logger.error(f"[wechatmp] 创建自定义菜单失败: {e}")
            return None

    def handle_click_event(self, msg):
        """处理菜单点击事件"""
        event_key = msg.key
        user_id = msg.source

        logger.info(f"[wechatmp] Received click event: {event_key} from user: {user_id}")

        # 构造上下文，模拟文本消息
        context = Context()
        context.type = ContextType.TEXT

        # 根据不同的菜单项设置不同的内容
        if event_key == "SET_GOAL":
            context.content = "立志"
        elif event_key == "CHECK_IN":
            context.content = "打卡"
        elif event_key == "MY_GOALS":
            context.content = "我的目标"
        elif event_key == "GOAL_STATS":
            context.content = "目标统计"
        elif event_key == "HELP":
            context.content = "使用说明"  # 或者提供具体的帮助内容
        elif event_key == "CONTACT":
            context.content = "联系客服"  # 或者提供具体的联系方式            
        else:
            context.content = event_key  # 将事件key作为消息内容

        context['session_id'] = user_id
        context['receiver'] = user_id
        context['msg'] = msg

        # 发送到插件系统处理
        self._handle(context)
