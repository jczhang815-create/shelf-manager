"""
AI 视觉识别：调用大模型从照片中提取材料编号
"""

import base64
import io
from PIL import Image
from openai import OpenAI

AI_MAX_SIZE = 1200
AI_JPEG_QUALITY = 80


def _preprocess_for_ai(image_path: str) -> str:
    """读取图片 → 缩小 → JPEG 压缩 → base64"""
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    if max(w, h) > AI_MAX_SIZE:
        ratio = AI_MAX_SIZE / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=AI_JPEG_QUALITY)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def extract_codes_by_vision(
    image_path: str,
    api_key: str,
    base_url: str = "https://api.siliconflow.cn/v1",
    model: str = "Qwen/Qwen3-VL-8B-Instruct",
) -> list[str]:
    """
    调用 AI 视觉模型识别图片中 ALL 材料编号（支持多瓶同框）。

    返回: 识别到的编号列表，失败返回空列表
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
                                "这是实验室化学品瓶子的照片，可能包含多个瓶子。"
                                "每个瓶子上有一张手写贴纸写着材料编号，"
                                "也可能印在标签「代码：」或「CODE」后面。"
                                "格式如 B00445、AK0328P、YZ-Y1722-0500G。"
                                "请找出照片中 ALL 的材料编号，用换行分隔，每行一个编号。"
                                "不要编号以外的任何文字。"
                                "如果找不到编号，返回 NONE。"
                            ),
                        },
                    ],
                }
            ],
            max_tokens=200,
            temperature=0,
        )

        result = response.choices[0].message.content.strip()
        if not result or result.upper() == "NONE":
            return []

        # 按换行拆分，过滤空行和 NONE
        codes = []
        for line in result.split("\n"):
            code = line.strip()
            if code and code.upper() != "NONE":
                codes.append(code)
        return codes

    except Exception as e:
        raise e


def extract_code_by_vision(
    image_path: str,
    api_key: str,
    base_url: str = "https://api.siliconflow.cn/v1",
    model: str = "Qwen/Qwen3-VL-8B-Instruct",
) -> str | None:
    """
    兼容旧接口：单编号识别（返回第一个结果）。
    """
    codes = extract_codes_by_vision(image_path, api_key, base_url, model)
    return codes[0] if codes else None
