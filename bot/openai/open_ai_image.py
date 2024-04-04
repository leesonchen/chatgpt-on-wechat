import time

import openai
import openai.error

from common.log import logger
from common.token_bucket import TokenBucket
from config import conf
import requests
import base64
import tempfile
import os
import io
from PIL import Image
# OPENAI提供的画图接口
class OpenAIImage(object):
    def __init__(self):
        openai.api_key = conf().get("open_ai_api_key")
        if conf().get("rate_limit_dalle"):
            self.tb4dalle = TokenBucket(conf().get("rate_limit_dalle", 50))

    def create_img(self, query, retry_count=0, api_key=None, api_base=None):
        try:
            SD_API_URL = 'http://sd.leeson.top'
            SD_AUTH_CODE = 'Y2hlbjpsZWVzb24x'

            if conf().get("rate_limit_dalle") and not self.tb4dalle.get_token():
                return False, "请求太快了，请休息一下再问我吧"
            logger.info("[OPEN_AI] image_query={}".format(query))
            # response = openai.Image.create(
            #     api_key=api_key,
            #     prompt=query,  # 图片描述
            #     n=1,  # 每次生成图片的数量
            #     model=conf().get("text_to_image") or "dall-e-2",
            #     # size=conf().get("image_create_size", "256x256"),  # 图片大小,可选有 256x256, 512x512, 1024x1024
            # )
            # image_url = response["data"][0]["url"]
            # logger.info("[OPEN_AI] image_url={}".format(image_url))


            headers = {
                # "Authorization": "Basic {}".format(SD_AUTH_CODE),
            }
            logger.info(f"headers={str(headers)}")
            payload = {"prompt": query, "steps": 10, "batch_size": 1}
            response = requests.post(url=f"{SD_API_URL}/sdapi/v1/txt2img/", headers=headers, json=payload)
            ret = response.json()
            logger.info(f"response={str(ret)}")

            urls = []
            for i in ret['images']:
                base64_data = i.split(",",1)[0]
                image = Image.open(io.BytesIO(base64.b64decode(base64_data)))
                newfile = tempfile.NamedTemporaryFile(delete=False).name
                newfile = os.path.basename(newfile)
                image.save(f'saved_pic\\output-{newfile}.png', format='PNG')
                filename = f'{os.getcwd()}\\saved_pic\\output-{newfile}.png'
                filename = filename.replace('\\','/')
                urls.append(base64_data)

            logger.info(f"Urls: {urls}")
            image_url = urls[0]

            return True, image_url
        except openai.error.RateLimitError as e:
            logger.warn(e)
            if retry_count < 1:
                time.sleep(5)
                logger.warn("[OPEN_AI] ImgCreate RateLimit exceed, 第{}次重试".format(retry_count + 1))
                return self.create_img(query, retry_count + 1)
            else:
                return False, "画图出现问题，请休息一下再问我吧"
        except Exception as e:
            logger.exception(e)
            return False, "画图出现问题，请休息一下再问我吧"
