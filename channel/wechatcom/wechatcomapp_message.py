from wechatpy.enterprise import WeChatClient

from bridge.context import ContextType
from channel.chat_message import ChatMessage
from common.log import logger
from common.tmp_dir import TmpDir


class WechatComAppMessage(ChatMessage):
    def __init__(self, msg, client: WeChatClient, is_group=False, customer_service_mode=False):
        super().__init__(msg)
        self.create_time = msg.time
        self.is_group = is_group
        self.client = client

        if customer_service_mode:
            self.msg_id = msg['msgid']
            self.external_userid = msg['external_userid']
            self.create_time = msg['send_time']
            self.origin = msg['origin']
            self.msgtype = msg['msgtype']
            self.open_kfid = msg['open_kfid']
        else:
            self.msg_id = msg.id
            self.msgtype = msg.type

        if self.msgtype == "text":
            self.ctype = ContextType.TEXT
            self.content = msg['text']['content'] if customer_service_mode else msg.content
        elif self.msgtype == "voice":
            self.ctype = ContextType.VOICE
            logger.debug(f"[wechatcom] voice message: {msg}")
            self.media_id = msg['voice']['media_id'] if customer_service_mode else msg.media_id
            # msg.get("voice", {}).get("media_id", "")
            media_format = ".mp3" if customer_service_mode else msg.format

            self.content = TmpDir().path() +  self.media_id + media_format  # content直接存临时目录路径
            self._prepare_fn = self.download_media
        elif msg.type == "image":
            self.ctype = ContextType.IMAGE
            logger.debug(f"[wechatcom] image message: {msg}")
            self.media_id = msg['image']['media_id'] if customer_service_mode else msg.media_id
            media_format = ".jpg" if customer_service_mode else ".png"

            self.content = TmpDir().path() +  self.media_id + media_format  # content直接存临时目录路径

            # def download_image():
            #     # 下载图片逻辑
            #     response = client.media.download(msg.media_id)
            #     if response.status_code == 200:
            #         with open(self.content, "wb") as f:
            #             f.write(response.content)
            #     else:
            #         logger.info(f"[wechatcom] Failed to download image file, {response.content}")

            self._prepare_fn = self.download_media
        else:
            raise NotImplementedError("Unsupported message type: Type:{} ".format(msg.type))

        self.from_user_id = msg.source
        self.to_user_id = msg.target
        self.other_user_id = msg.source

    def download_media(self):
        # 如果响应状态码是200，则将响应内容写入本地文件
        response = self.client.media.download(self.media_id)
        if response.status_code == 200:
            with open(self.content, "wb") as f:
                f.write(response.content)
        else:
            logger.info(f"[wechatcom] Failed to download voice file, {response.content}")