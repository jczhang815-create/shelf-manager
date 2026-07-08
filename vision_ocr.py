"""
AI 视觉识别：调用大模型从照片中提取材料编号
支持任何 OpenAI 兼容的 API
"""

import base64
import io
import os
from PIL import Image
from openai import OpenAI

# AI 用的小图尺寸（无需原图，800px 足够看手写字）
AI_MAX_SIZE = 800
AI_JPEG_QUALITY = 65


def _preprocess_for_ai(image_path: str) -> str:
    """
    读取图片 → 缩小 → 转 JPEG 压缩 → base64 编码
    手机原图 4MB → 处理后 ~80KB，速度提升 50 倍
    """
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    if max(w, h) > AI_MAX_SIZE:
        ratio = AI_MAX_SIZE / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=AI_JPEG_QUALITY)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def extract_code_by_vision(
    image_path: str,
    api_key: str,
    base_url: str = "https://api.siliconflow.cn/v1",
    model: str = "Qwen/Qwen3-VL-8B-Instruct",
) -> str | None:
    """
    调用 AI 视觉模型识别图片中的材料编号。

    参数:
        image_path: 图片路径
        api_key: API Key
        base_url: API 地址
        model: 模型名称

    返回: 识别到的编号字符串，失败返回 None
    """
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        b64 = _preprocess_for_ai(image_path)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                        },
                        {
                            "type": "text",
                            "text": (
                                "瓶子上有一张手写贴纸写着材料编号，"
                                "也可能在「代码：」或「CODE」后面。"
                                "格式如 B00445、AK0328P、YZ-Y1722-0500G。"
                                "只返回编号本身。如果找不到，返回 NONE。"
                            ),
                        },
                    ],
                }
            ],
            max_tokens=50,
            temperature=0,
        )

        result = response.choices[0].message.content.strip()
        if result and result.upper() != "NONE":
            return result
        return None

    except Exception as e:
        raise e
