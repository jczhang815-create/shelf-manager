"""
实验室原材料货架管理系统 — Streamlit 主应用
"""

import streamlit as st
import os
import time
from datetime import datetime

from database import init_db, insert_record, query_by_code, get_all_records
from utils import parse_location_from_filename, normalize_material_code

# ============================================================
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
init_db()

SHELF_OPTIONS = [
    "S01-L01", "S01-L02", "S01-L03",
    "S02-L01", "S02-L02", "S02-L03",
    "S03-L01", "S03-L02", "S03-L03",
    "S04-L01", "S04-L02", "S04-L03",
    "S05-L01", "S05-L02", "S05-L03",
]

# ngrok（环境变量 ENABLE_NGROK=1 才启动）
_ngrok_url = None
if os.getenv("ENABLE_NGROK", "").lower() in {"1", "true", "yes"}:
    try:
        from pyngrok import ngrok, conf
        ngrok_path = os.getenv("NGROK_PATH", r"C:\ngrok\ngrok.exe")
        if os.path.exists(ngrok_path):
            conf.get_default().ngrok_path = ngrok_path
        _ngrok_url = ngrok.connect(8501, "http").public_url
    except Exception:
        pass

# ============================================================
st.set_page_config(page_title="货架管理系统", page_icon="🧪", layout="wide")

# Session State
for key, default in [("scan_count", 0), ("uploader_key", 0), ("pairs", []), ("img_path", ""), ("codes", [])]:
    if key not in st.session_state:
        st.session_state[key] = default

# ============================================================
# 侧边栏
# ============================================================
st.sidebar.title("🧪 货架管理系统")
if _ngrok_url:
    st.sidebar.success(f"📱 [{_ngrok_url}]({_ngrok_url})")

page = st.sidebar.radio("导航", ["📸 扫码入库", "🔍 查询材料", "📋 浏览记录"])

st.sidebar.divider()
st.sidebar.subheader("🤖 AI 设置")

default_key = os.getenv("SHELF_MANAGER_API_KEY", "")
try:
    default_key = st.secrets.get("API_KEY", default_key)
except Exception:
    pass

api_key = st.sidebar.text_input(
    "API Key", type="password",
    value=st.session_state.get("api_key") or default_key,
    placeholder="sk-...",
)
if api_key:
    st.session_state["api_key"] = api_key

api_base = st.sidebar.text_input(
    "API 地址",
    value=os.getenv("SHELF_MANAGER_API_BASE") or "https://api.siliconflow.cn/v1",
)
ai_model = st.sidebar.text_input(
    "模型",
    value=os.getenv("SHELF_MANAGER_AI_MODEL") or "Qwen/Qwen3-VL-8B-Instruct",
)

# ============================================================
# 扫码入库
# ============================================================
if page == "📸 扫码入库":
    st.title("📸 扫码入库")

    # 货架位置
    c1, c2 = st.columns([1, 1])
    with c1:
        shelf = st.selectbox(
            "📍 货架位置",
            SHELF_OPTIONS,
            index=SHELF_OPTIONS.index("S02-L01") if "S02-L01" in SHELF_OPTIONS else 0,
        )
    with c2:
        custom = st.text_input("或手动输入", placeholder="S06-L01")
    shelf_input = (custom or shelf).strip().upper()
    loc = parse_location_from_filename(shelf_input + ".jpg") if shelf_input else None
    if loc:
        st.caption(f"当前：货架 {loc['shelf']} — 层 {loc['layer']}")
    elif shelf_input:
        st.warning("格式：S架号-L层号")

    st.divider()

    # 拍照 / 相册
    tab1, tab2 = st.tabs(["📷 拍照", "📁 相册"])
    images = []

    with tab1:
        cam = st.camera_input("点击拍照", key="cam_input")
        if cam:
            images.append(cam.getvalue())

    with tab2:
        ufs = st.file_uploader("选择照片（可多选）", type=["jpg", "jpeg", "png", "bmp", "webp"], accept_multiple_files=True, key="file_uploader")
        if ufs:
            for uf in ufs:
                images.append(uf.getbuffer())

    # ---- AI 识别 & 缓存 ----
    cache_key = f"scan_{st.session_state.uploader_key}"

    if images and api_key and loc:
        st.subheader(f"📊 {len(images)} 张照片，AI 识别中...")
        codes = []
        paths = []
        errors = []
        bar = st.progress(0)

        for i, data in enumerate(images):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            sp = os.path.join(UPLOAD_DIR, f"scan_{loc['location']}_{ts}_{i}.jpg")
            with open(sp, "wb") as f:
                f.write(bytes(data))
                f.flush()
                os.fsync(f.fileno())
            paths.append(sp)

            t0 = time.time()
            try:
                from vision_ocr import extract_codes_by_vision
                found = extract_codes_by_vision(sp, api_key=api_key, base_url=api_base, model=ai_model)
                elapsed = time.time() - t0
            except Exception as e:
                found = []
                elapsed = time.time() - t0
                errors.append(f"照片{i+1}: {e}")

            st.caption(f"照片 {i+1}：{elapsed:.1f}s，{len(found)} 个")
            for c in found:
                c = normalize_material_code(c)
                if c and c not in codes:
                    codes.append(c)
            bar.progress((i + 1) / len(images))
        bar.empty()

        if errors:
            with st.expander("⚠️ 识别错误"):
                for e in errors:
                    st.code(e)

        st.session_state[cache_key] = {"codes": codes, "paths": paths}

    # ---- 显示缓存结果 ----
    if cache_key in st.session_state:
        data = st.session_state[cache_key]
        codes = data["codes"]
        paths = data["paths"]

        if not codes:
            st.warning("未识别到编号")
        else:
            st.divider()
            st.subheader("🏷️ 选择类型（可多选）")

            # 先渲染所有 checkbox，再从 session_state 统一读取（避免 SW 丢失 bug）
            for i, code in enumerate(codes):
                c1, c2, c3 = st.columns([2, 0.6, 0.6])
                with c1:
                    st.markdown(f"**`{code}`**")
                with c2:
                    st.checkbox("RH", key=f"rh_{i}")
                with c3:
                    st.checkbox("SW", key=f"sw_{i}")

            # 读取勾选状态
            rh_codes = [codes[i] for i in range(len(codes)) if st.session_state.get(f"rh_{i}")]
            sw_codes = [codes[i] for i in range(len(codes)) if st.session_state.get(f"sw_{i}")]

            st.divider()
            st.subheader("📋 入库预览")

            n = max(len(rh_codes), len(sw_codes))
            if n == 0:
                st.info("请至少勾选一个")
            else:
                for j in range(n):
                    rh_val = rh_codes[j] if j < len(rh_codes) else ""
                    sw_val = sw_codes[j] if j < len(sw_codes) else ""
                    c1, c2 = st.columns(2)
                    c1.text_input(f"RH #{j+1}", value=rh_val, key=f"rh_val_{j}")
                    c2.text_input(f"SW #{j+1}", value=sw_val, key=f"sw_val_{j}")

                if st.button("✅ 入库", type="primary"):
                    count = 0
                    img = paths[0] if paths else ""
                    for j in range(n):
                        rh = st.session_state.get(f"rh_val_{j}", "").strip().upper()
                        sw = st.session_state.get(f"sw_val_{j}", "").strip().upper()
                        if rh or sw:
                            insert_record(rh, sw, loc["location"], img)
                            count += 1
                    st.session_state.scan_count += count
                    st.success(f"✅ 已入库 {count} 条 → {loc['location']}")
                    del st.session_state[cache_key]
                    st.session_state.uploader_key += 1
                    st.rerun()

    # 统计
    if st.session_state.scan_count:
        st.divider()
        st.info(f"📊 本次入库：{st.session_state.scan_count} 个")

# ============================================================
# 查询材料
# ============================================================
elif page == "🔍 查询材料":
    st.title("🔍 查询材料")
    q = st.text_input("输入 RH 或 SW 编码", placeholder="B00445").strip()
    if q:
        rows = query_by_code(q.upper())
        if not rows:
            st.warning(f"未找到 {q.upper()}")
        else:
            st.success(f"找到 {len(rows)} 条")
            for r in rows:
                c1, c2 = st.columns([1, 1])
                c1.metric("📍 位置", r["location"])
                c2.markdown(f"RH: `{r['rh_code']}`  \nSW: `{r['sw_code']}`")
                st.caption(r["create_time"])
                if os.path.exists(r["image_path"]):
                    st.image(r["image_path"], width=300)
                st.divider()

# ============================================================
# 浏览记录
# ============================================================
else:
    st.title("📋 浏览记录")
    rows = get_all_records(200)
    if not rows:
        st.info("暂无")
    else:
        from collections import Counter
        sc = Counter(r["location"] for r in rows)
        st.subheader("📊 按货架统计")
        cols = st.columns(min(len(sc), 6))
        for i, (loc, cnt) in enumerate(sorted(sc.items())):
            cols[i % 6].metric(loc, f"{cnt} 件")

        st.divider()
        st.subheader("📜 详细")
        import pandas as pd
        df = pd.DataFrame(rows)
        df.columns = ["ID", "RH", "SW", "位置", "图片", "时间"]
        st.dataframe(df, use_container_width=True, hide_index=True)
