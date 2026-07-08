"""
OCR 封装：EasyOCR + DeepSeek 文字筛选
"""

import re
import easyocr
import numpy as np
from PIL import Image, ImageFilter

_ocr_instance = None
MAX_IMAGE_SIZE = 2000       # 提高分辨率保留小字
CONFIDENCE_THRESHOLD = 0.0  # 不过滤，全部返回


def get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        _ocr_instance = easyocr.Reader(
            ["en", "ch_sim"],
            gpu=False,
            verbose=False,
        )
    return _ocr_instance


def _prepare_image(image_path: str) -> np.ndarray:
    pil = Image.open(image_path).convert("RGB")
    w, h = pil.size
    if max(w, h) > MAX_IMAGE_SIZE:
        ratio = MAX_IMAGE_SIZE / max(w, h)
        pil = pil.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
    # 增强对比度让小字更清晰
    from PIL import ImageEnhance
    pil = ImageEnhance.Contrast(pil).enhance(1.5)
    pil = ImageEnhance.Sharpness(pil).enhance(2.0)
    return np.array(pil)


def detect_all_text(image_path: str) -> list[dict]:
    """返回所有识别文字"""
    try:
        arr = _prepare_image(image_path)
        ocr = get_ocr()
        result = ocr.readtext(
            arr,
            min_size=5,           # 最小文字 5px
            text_threshold=0.2,   # 低门槛
            low_text=0.1,         # 接受低置信度文字
        )
        if not result:
            return []
        items = []
        for bbox, text, conf in result:
            items.append({"text": text.strip(), "confidence": round(conf, 4)})
        items.sort(key=lambda x: x["confidence"], reverse=True)
        return items
    except Exception:
        return []


def detect_all_text_multi_scale(image_path: str) -> list[dict]:
    """
    多尺度检测：原图 + 放大裁剪小块，捕捉小贴纸文字
    """
    all_items = detect_all_text(image_path)

    # 如果原图已经找到不少文字，直接返回
    if len(all_items) >= 5:
        return all_items

    # 否则尝试把图片切成 2×2 格子分别 OCR
    try:
        pil = Image.open(image_path).convert("RGB")
        w, h = pil.size
        seen = {item["text"] for item in all_items}

        for row in range(2):
            for col in range(2):
                left = col * w // 2
                top = row * h // 2
                right = (col + 1) * w // 2
                bottom = (row + 1) * h // 2
                crop = pil.crop((left, top, right, bottom))

                # 放大到原图尺寸
                crop = crop.resize((w, h), Image.LANCZOS)

                temp_path = image_path + f"_crop_{row}_{col}.jpg"
                crop.save(temp_path)

                sub_items = detect_all_text(temp_path)
                for item in sub_items:
                    if item["text"] not in seen:
                        seen.add(item["text"])
                        all_items.append(item)

                # 清理临时文件
                import os
                try:
                    os.remove(temp_path)
                except:
                    pass

        all_items.sort(key=lambda x: x["confidence"], reverse=True)
    except Exception:
        pass

    return all_items


def extract_material_codes(image_path: str) -> list[str]:
    """兼容旧接口"""
    items = detect_all_text(image_path)
    codes = []
    seen = set()
    for item in items:
        t = re.sub(r'\s+', '', item["text"].strip().upper())
        if len(t) < 2:
            continue
        if re.search(r'[一-鿿]', t) and not re.search(r'[A-Z0-9]', t):
            continue
        if t in seen:
            continue
        seen.add(t)
        codes.append(item["text"].strip())
    return codes


def analyze_shelf_image(image_path: str) -> dict:
    from utils import extract_location_from_text
    items = detect_all_text(image_path)
    location = None
    for item in items:
        if location is None:
            location = extract_location_from_text(item["text"])
    codes = extract_material_codes(image_path)
    return {"location": location, "codes": codes, "all_text": items}
