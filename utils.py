"""
工具函数：文件名解析、OCR 文本中提取位置、编号校验
"""

import re
import os

# 货架标签正则：
# 严格模式：S02-L01（用于文件名解析）
# 容错模式：处理 OCR 常见误读（S→5/9, L→1/I, 0→O, 连字符丢失等）
_LOCATION_STRICT = re.compile(r'[sS](\d+)\s*-\s*[lL](\d+)')

# 模糊匹配：前缀[S/s/5/9] + 数字 + 分隔符 + 层前缀[L/l/1/I] + 数字
# 数字中允许 O/o 出现（OCR 将 0 误读为 O）——调用侧负责修正
_LOCATION_FUZZY = re.compile(
    r'[sS59]'           # 货架前缀：S/s 或 OCR 误读 5/9
    r'([Oo\d]+)'        # 货架编号（允许 O→0）
    r'\s*[-—_\s]*\s*'   # 分隔符
    r'[lL1Ii]'          # 层前缀：L/l 或 OCR 误读 1/I
    r'([Oo\d]+)',       # 层编号（允许 O→0）
    re.IGNORECASE,
)


def _try_match_location(text: str):
    """尝试从文本中匹配货架位置标签，严格优先，再模糊匹配"""
    text = text.strip()
    # 1) 严格匹配
    m = _LOCATION_STRICT.search(text)
    if m:
        return m
    # 2) 模糊匹配（容错 OCR 误读）
    m = _LOCATION_FUZZY.search(text)
    if m:
        # 修正常见误读：数字中 O/o → 0，L/l/I/i → L
        shelf = m.group(1).replace('O', '0').replace('o', '0')
        layer = m.group(2).replace('O', '0').replace('o', '0')
        if shelf.isdigit() and layer.isdigit():
            return m
    return None


def parse_location_from_filename(filename: str) -> dict:
    """
    从文件名解析货架位置。

    规则示例：
      S02-L01.jpg → Shelf=S02, Layer=L01
      S02-L01-extra.jpg → Shelf=S02, Layer=L01
      s03-L02.png → Shelf=S03, Layer=L02

    返回 {"shelf": "S02", "layer": "L01", "location": "S02-L01"}
    解析失败返回 None
    """
    name = os.path.splitext(filename)[0]
    match = _LOCATION_STRICT.match(name)
    if not match:
        return None
    return _build_location_dict(match)


def extract_location_from_text(text: str) -> dict | None:
    """
    从 OCR 识别的文本中提取货架位置标签。

    支持 OCR 常见误读容错：
      "S02-L01"   → 标准格式
      "92 - LO1"  → S→9, L→1 误读，自动修正
      "502-L01"   → S→5 误读

    返回格式同 parse_location_from_filename，失败返回 None
    """
    match = _try_match_location(text)
    if not match:
        return None
    return _build_location_dict(match)


def _build_location_dict(match) -> dict:
    shelf_num = match.group(1).replace('O', '0').replace('o', '0')
    layer_num = match.group(2).replace('O', '0').replace('o', '0')
    return {
        "shelf": f"S{shelf_num}",
        "layer": f"L{layer_num}",
        "location": f"S{shelf_num}-L{layer_num}",
    }


def normalize_material_code(text: str) -> str:
    """
    清洗 OCR 识别结果，去掉空白字符，转为大写。
    """
    return re.sub(r'\s+', '', text).strip().upper()


def is_valid_material_code(code: str) -> bool:
    """
    判断是否为有效的材料编号。

    规则（收紧以过滤误识别）：
      - 5~15 个字符
      - 只含大写字母和数字
      - 必须包含至少一个数字
      - 不能全是同一个字符（如 AAAAAA）
    """
    code = normalize_material_code(code)
    if len(code) < 5 or len(code) > 15:
        return False
    if not re.match(r'^[A-Z0-9]+$', code):
        return False
    if not re.search(r'\d', code):
        return False
    if len(set(code)) == 1:
        return False
    return True
