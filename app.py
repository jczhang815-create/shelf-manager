"""
实验室原材料货架管理系统 — Streamlit 主应用
"""

import streamlit as st
import os
from datetime import datetime

from database import init_db, insert_record, query_by_code, get_all_records
from utils import parse_location_from_filename

# ============================================================
# 常量
# ============================================================
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
init_db()

# 预设货架选项
SHELF_OPTIONS = [
    "S01-L01", "S01-L02", "S01-L03",
    "S02-L01", "S02-L02", "S02-L03",
    "S03-L01", "S03-L02", "S03-L03",
    "S04-L01", "S04-L02", "S04-L03",
    "S05-L01", "S05-L02", "S05-L03",
]

# ngrok
_ngrok_url = None

def _start_ngrok():
    global _ngrok_url
    if _ngrok_url is not None:
        return _ngrok_url
    try:
        from pyngrok import ngrok, conf
        conf.get_default().ngrok_path = r"C:\ngrok\ngrok.exe"
        tunnel = ngrok.connect(8501, "http")
        _ngrok_url = tunnel.public_url
        return _ngrok_url
    except Exception:
        return None

_ngrok_url = _start_ngrok()

st.set_page_config(page_title="货架管理系统", page_icon="🧪", layout="wide")

# ============================================================
# Session State
# ============================================================
if "scan_count" not in st.session_state:
    st.session_state.scan_count = 0
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# ============================================================
# 侧边栏
# ============================================================
st.sidebar.title("🧪 货架管理系统")

if _ngrok_url:
    st.sidebar.success(f"📱 [{_ngrok_url}]({_ngrok_url})")

page = st.sidebar.radio("导航", ["📸 扫码入库", "🔍 查询材料", "📋 浏览记录"])

# AI 设置
st.sidebar.divider()
st.sidebar.subheader("🤖 AI 设置")

api_key = st.sidebar.text_input(
    "API Key", type="password",
    value=st.session_state.get("api_key", "sk-xtxfhovabfbicmrmcibbtifgeszwmfmypfzbupvtnjzmngnk"),
    placeholder="sk-...",
)
if api_key:
    st.session_state["api_key"] = api_key

api_base = st.sidebar.text_input("API 地址", value="https://api.siliconflow.cn/v1")
ai_model = st.sidebar.text_input("模型", value="Qwen/Qwen3-VL-8B-Instruct")

# ============================================================
# 页面1：📸 扫码入库
# ============================================================
if page == "📸 扫码入库":
    st.title("📸 扫码入库")

    # ---- 货架位置（下拉 + 手动） ----
    shelf_col1, shelf_col2 = st.columns([1, 1])
    with shelf_col1:
        shelf_preset = st.selectbox(
            "📍 选择货架位置",
            SHELF_OPTIONS,
            index=SHELF_OPTIONS.index("S02-L01") if "S02-L01" in SHELF_OPTIONS else 0,
            key=f"shelf_select_{st.session_state.uploader_key}",
        )
    with shelf_col2:
        shelf_custom = st.text_input(
            "或手动输入",
            placeholder="自定义位置，如 S06-L01",
            key=f"shelf_custom_{st.session_state.uploader_key}",
        )

    shelf_input = (shelf_custom or shelf_preset).strip().upper()
    loc_info = parse_location_from_filename(shelf_input + ".jpg") if shelf_input else None

    if loc_info:
        st.caption(f"当前扫描：货架 {loc_info['shelf']} — 层 {loc_info['layer']}")
    else:
        if shelf_input:
            st.warning("格式：S架号-L层号")

    st.divider()

    # ---- 拍照 + 相册 ----
    tab1, tab2 = st.tabs(["📷 直接拍照（秒传）", "📁 从相册上传"])
    images_to_process = []

    with tab1:
        cam = st.camera_input("点击拍照", key=f"cam_{st.session_state.uploader_key}")
        if cam is not None:
            images_to_process.append(("camera.jpg", cam.getvalue()))

    with tab2:
        ufs = st.file_uploader(
            "选择照片（可多选）", type=["jpg", "jpeg", "png", "bmp", "webp"],
            accept_multiple_files=True, key=f"scanner_{st.session_state.uploader_key}",
        )
        if ufs:
            for uf in ufs:
                images_to_process.append((uf.name, uf.getbuffer()))

    if images_to_process:
        if not api_key:
            st.warning("⚠️ 请在侧边栏填写 API Key")
        elif not loc_info:
            st.warning("⚠️ 请先设定货架位置")
        else:
            # ---- AI 识别（结果缓存在 session state） ----
            cache_key = f"ai_result_{st.session_state.uploader_key}"
            if cache_key not in st.session_state:
                st.subheader(f"📊 共 {len(images_to_process)} 张照片，AI 识别中...")
                all_codes = []
                saved_paths = []
                progress = st.progress(0)

                for i, (name, data) in enumerate(images_to_process):
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    sp = os.path.join(UPLOAD_DIR, f"scan_{ts}_{i}.jpg")
                    with open(sp, "wb") as f:
                        f.write(data)
                        f.flush()
                        os.fsync(f.fileno())
                    saved_paths.append(sp)

                    import time
                    t0 = time.time()
                    try:
                        from vision_ocr import extract_codes_by_vision
                        codes = extract_codes_by_vision(
                            sp, api_key=api_key, base_url=api_base, model=ai_model,
                        )
                        elapsed = time.time() - t0
                    except Exception:
                        codes = []
                        elapsed = time.time() - t0

                    st.caption(f"照片 {i+1}：{elapsed:.1f}s，{len(codes)} 个编号")
                    for code in codes:
                        c = code.strip()
                        if c and c not in all_codes:
                            all_codes.append(c)
                    progress.progress((i + 1) / len(images_to_process))
                progress.empty()

                st.session_state[cache_key] = {
                    "all_codes": all_codes,
                    "saved_paths": saved_paths,
                }
            else:
                cached = st.session_state[cache_key]
                all_codes = cached["all_codes"]
                saved_paths = cached["saved_paths"]

            # ---- 编码分配 ----
            if not all_codes:
                st.warning("未识别到任何编号")
            else:
                st.divider()
                st.subheader("🏷️ 为每个编号选择类型")

                for i, code in enumerate(all_codes):
                    c1, c2, c3 = st.columns([2, 0.6, 0.6])
                    with c1:
                        st.markdown(f"**`{code}`**")
                    with c2:
                        st.checkbox("RH", key=f"rh_chk_{st.session_state.uploader_key}_{i}", value=False)
                    with c3:
                        st.checkbox("SW", key=f"sw_chk_{st.session_state.uploader_key}_{i}", value=False)

                st.divider()
                st.subheader("📋 配对预览")

                # 读取角色分配
                rh_list = [all_codes[i] for i in range(len(all_codes))
                           if st.session_state.get(f"rh_chk_{st.session_state.uploader_key}_{i}")]
                sw_list = [all_codes[i] for i in range(len(all_codes))
                           if st.session_state.get(f"sw_chk_{st.session_state.uploader_key}_{i}")]

                max_len = max(len(rh_list), len(sw_list))
                if max_len == 0:
                    st.info("请至少选择一个 RH 或 SW")
                else:
                    for j in range(max_len):
                        rh_default = rh_list[j] if j < len(rh_list) else ""
                        sw_default = sw_list[j] if j < len(sw_list) else ""
                        c1, c2 = st.columns(2)
                        c1.text_input(f"RH #{j+1}", value=rh_default,
                                      key=f"rhv_{st.session_state.uploader_key}_{j}")
                        c2.text_input(f"SW #{j+1}", value=sw_default,
                                      key=f"swv_{st.session_state.uploader_key}_{j}")

                    if st.button("✅ 批量入库", type="primary", key=f"save_{st.session_state.uploader_key}"):
                        count = 0
                        img = saved_paths[0] if saved_paths else ""
                        for j in range(max_len):
                            final_rh = st.session_state.get(f"rhv_{st.session_state.uploader_key}_{j}", "").strip()
                            final_sw = st.session_state.get(f"swv_{st.session_state.uploader_key}_{j}", "").strip()
                            if final_rh or final_sw:
                                insert_record(final_rh, final_sw, loc_info["location"], img)
                                count += 1
                        st.session_state.scan_count += count
                        st.success(f"✅ 已入库 {count} 条 → {loc_info['location']}")
                        # 清理缓存
                        del st.session_state[cache_key]
                        st.session_state.uploader_key += 1
                        st.rerun()

# ============================================================
# 页面2：🔍 查询材料
# ============================================================
elif page == "🔍 查询材料":
    st.title("🔍 查询材料位置")

    search_code = st.text_input("输入 RH 或 SW 编码", placeholder="例如：B00445").strip()

    if search_code:
        results = query_by_code(search_code.upper())
        if not results:
            st.warning(f"未找到 {search_code.upper()}")
        else:
            st.success(f"找到 {len(results)} 条记录")
            for i, r in enumerate(results):
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.metric("📍 位置", r["location"])
                c2.markdown(f"**RH**: `{r['rh_code']}`  \n**SW**: `{r['sw_code']}`")
                with c3:
                    st.caption(r["create_time"])
                    if os.path.exists(r["image_path"]):
                        with st.expander("🖼️"):
                            st.image(r["image_path"], width=300)
                if i < len(results) - 1:
                    st.divider()

# ============================================================
# 页面3：📋 浏览记录
# ============================================================
else:
    st.title("📋 浏览所有记录")
    records = get_all_records(limit=200)

    if not records:
        st.info("暂无记录")
    else:
        from collections import Counter
        sc = Counter(r["location"] for r in records)
        st.subheader("📊 按货架统计")
        cols = st.columns(min(len(sc), 6))
        for i, (loc, cnt) in enumerate(sorted(sc.items())):
            cols[i % 6].metric(loc, f"{cnt} 件")

        st.divider()
        st.subheader("📜 详细记录")
        import pandas as pd
        df = pd.DataFrame(records)
        df.columns = ["ID", "RH编码", "SW编码", "位置", "图片路径", "录入时间"]
        st.dataframe(df, use_container_width=True, hide_index=True)
