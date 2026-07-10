"""
EasyOCR 备用（当前不使用，保留以备离线场景）
"""

import re
import os
import easyocr
import numpy as np
from PIL import Image, ImageFilter
from utils import normalize_material_code

_ocr_instance = None
MAX_IMAGE_SIZE = 2000


def get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        _ocr_instance = easyocr.Reader(["en", "ch_sim"], gpu=False, verbose=False)
    return _ocr_instance


def _prepare_image(image_path: str) -> np.ndarray:
    pil = Image.open(image_path).convert("RGB")
    w, h = pil.size
    if max(w, h) > MAX_IMAGE_SIZE:
        ratio = MAX_IMAGE_SIZE / max(w, h)
        pil = pil.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
    from PIL import ImageEnhance
    pil = ImageEnhance.Contrast(pil).enhance(1.5)
    pil = ImageEnhance.Sharpness(pil).enhance(2.0)
    return np.array(pil)


def detect_all_text(image_path: str) -> list[dict]:
    try:
        arr = _prepare_image(image_path)
        ocr = get_ocr()
        result = ocr.readtext(arr, min_size=5, text_threshold=0.2, low_text=0.1)
        if not result:
            return []
        items = []
        for bbox, text, conf in result:
            items.append({"text": text.strip(), "confidence": round(conf, 4)})
        items.sort(key=lambda x: x["confidence"], reverse=True)
        return items
    except Exception:
        return []


def extract_material_codes(image_path: str) -> list[str]:
    items = detect_all_text(image_path)
    codes = []
    seen = set()
    for item in items:
        t = re.sub(r"\s+", "", item["text"].strip().upper())
        if len(t) < 2 or t in seen:
            continue
        if re.search(r"[一-鿿]", t) and not re.search(r"[A-Z0-9]", t):
            continue
        seen.add(t)
        codes.append(item["text"].strip())
    return codes
