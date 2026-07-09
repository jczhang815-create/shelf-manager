"""
实验室原材料货架管理系统 — Streamlit 主应用
"""

import streamlit as st
import os
from datetime import datetime

from database import init_db, insert_record, query_by_material_code, get_all_records
from utils import parse_location_from_filename

# ============================================================
# 常量 & 初始化
# ============================================================
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
init_db()

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

page = st.sidebar.radio(
    "导航",
    ["📸 扫码入库", "🔍 查询材料", "📋 浏览记录"],
)

# ---- AI 设置 ----
st.sidebar.divider()
st.sidebar.subheader("🤖 AI 设置")

# 优先从 secrets 读取（Streamlit Cloud），否则用本地存储
_default_key = ""
try:
    _default_key = st.secrets["API_KEY"]
except Exception:
    _default_key = st.session_state.get("api_key", "")

api_key = st.sidebar.text_input(
    "API Key",
    type="password",
    value=_default_key,
    placeholder="sk-...",
)
if api_key:
    st.session_state["api_key"] = api_key

api_base = st.sidebar.text_input(
    "API 地址",
    value="https://api.siliconflow.cn/v1",
)

ai_model = st.sidebar.text_input(
    "模型",
    value="Qwen/Qwen3-VL-8B-Instruct",
)

# ============================================================
# 页面1：📸 扫码入库
# ============================================================
if page == "📸 扫码入库":
    st.title("📸 扫码入库")

    # ---- 货架位置 ----
    shelf_input = st.text_input(
        "📍 货架位置",
        value="S02-L01",
        placeholder="例如：S02-L01",
    ).strip().upper()

    loc_info = parse_location_from_filename(shelf_input + ".jpg")
    if loc_info:
        st.caption(f"当前扫描：货架 {loc_info['shelf']} — 层 {loc_info['layer']}")
    else:
        st.warning("格式：S架号-L层号")

    st.divider()

    # ---- 批量拍照 ----
    uploaded_files = st.file_uploader(
        "📷 选择照片，可多选（手机端可选「拍照」一次一张，再继续添加）",
        type=["jpg", "jpeg", "png", "bmp", "webp"],
        accept_multiple_files=True,
        key=f"scanner_{st.session_state.uploader_key}",
    )

    if uploaded_files:
        if not api_key:
            st.warning("⚠️ 请在侧边栏填写 API Key")
        elif not loc_info:
            st.warning("⚠️ 请先设定货架位置")
        else:
            # ---- 批量 AI 识别 ----
            st.subheader(f"📊 共 {len(uploaded_files)} 张照片，AI 识别中...")

            results = []
            progress = st.progress(0)

            for i, uf in enumerate(uploaded_files):
                # 保存
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                saved_path = os.path.join(UPLOAD_DIR, f"scan_{ts}_{i}.jpg")
                with open(saved_path, "wb") as f:
                    f.write(uf.getbuffer())
                    f.flush()
                    os.fsync(f.fileno())

                # AI 识别（支持一图多码）
                import time
                t0 = time.time()
                try:
                    from vision_ocr import extract_codes_by_vision
                    codes = extract_codes_by_vision(
                        saved_path, api_key=api_key,
                        base_url=api_base, model=ai_model,
                    )
                    elapsed = time.time() - t0
                except Exception as e:
                    codes = []
                    elapsed = time.time() - t0

                # 一图可能识别到多个编号，每个编号一行
                for code in (codes if codes else [""]):
                    results.append({
                        "name": uf.name,
                        "path": saved_path,
                        "code": code.strip(),
                        "time": elapsed,
                        "ok": bool(codes),
                    })

                progress.progress((i + 1) / len(uploaded_files))

            progress.empty()

            # ---- 展示结果表格 ----
            st.subheader(f"📋 识别结果（共 {len(results)} 条）")

            # 全选/取消
            toggle_cols = st.columns(4)
            if toggle_cols[0].button("☑ 全选", key=f"all_{st.session_state.uploader_key}"):
                st.session_state[f"select_all_{st.session_state.uploader_key}"] = True
            if toggle_cols[1].button("☐ 取消全选", key=f"none_{st.session_state.uploader_key}"):
                st.session_state[f"select_all_{st.session_state.uploader_key}"] = False

            select_all = st.session_state.get(f"select_all_{st.session_state.uploader_key}", True)

            selected_items = []
            edited_codes = []
            for i, r in enumerate(results):
                c1, c2, c3, c4 = st.columns([1, 2, 0.5, 0.8])
                with c1:
                    st.image(r["path"], width=100)
                with c2:
                    code = st.text_input(
                        f"编号 #{i+1}",
                        value=r["code"],
                        key=f"batch_code_{st.session_state.uploader_key}_{i}",
                        label_visibility="collapsed",
                    ).strip()
                    edited_codes.append(code)
                with c3:
                    checked = st.checkbox(
                        "入库",
                        value=select_all and bool(code),
                        key=f"chk_{st.session_state.uploader_key}_{i}",
                        label_visibility="collapsed",
                    )
                    if checked:
                        selected_items.append(i)
                with c4:
                    if r["ok"]:
                        st.caption(f"{r['time']:.1f}s")
                    elif not r["code"]:
                        st.caption("未识别")
                    else:
                        st.caption("失败")

            # ---- 批量入库 ----
            st.divider()
            st.write(f"已勾选：**{len(selected_items)}** / {len(results)} 条")

            if st.button("✅ 批量入库", type="primary", key=f"batch_save_{st.session_state.uploader_key}"):
                count = 0
                for i in selected_items:
                    code = edited_codes[i]
                    if code:
                        insert_record(code, loc_info["location"], results[i]["path"])
                        count += 1
                st.session_state.scan_count += count
                st.success(f"✅ 已入库 **{count}** 条记录 → {loc_info['location']}")
                st.session_state.uploader_key += 1
                st.rerun()

    # ---- 统计 ----
    if st.session_state.scan_count > 0:
        st.divider()
        st.info(f"📊 本次已扫描入库：**{st.session_state.scan_count}** 个材料")

# ============================================================
# 页面2：🔍 查询材料
# ============================================================
elif page == "🔍 查询材料":
    st.title("🔍 查询材料位置")

    search_code = st.text_input("材料编号", placeholder="例如：B00445").strip()

    if search_code:
        results = query_by_material_code(search_code.upper())
        if not results:
            st.warning(f"未找到 {search_code.upper()}")
        else:
            st.success(f"找到 {len(results)} 条记录")
            st.metric("📍 当前所在位置", results[0]["location"])
            st.caption(f"最后更新：{results[0]['create_time']}")

            for i, r in enumerate(results):
                c1, c2 = st.columns([1, 2])
                c1.markdown(f"📍 **{r['location']}**")
                c1.caption(r["create_time"])
                with c2:
                    if os.path.exists(r["image_path"]):
                        st.image(r["image_path"], width=350)
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
        df.columns = ["ID", "材料编号", "位置", "图片路径", "录入时间"]
        st.dataframe(df, use_container_width=True, hide_index=True)
