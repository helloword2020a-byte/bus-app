import streamlit as st
import pandas as pd
import requests
import re

# 页面基础配置
st.set_page_config(page_title="包车报价智能中心", layout="wide")

# --- 增强版 CSS：解决“粘贴没反应”的视觉反馈问题 ---
st.markdown("""
    <style>
    /* 让上传框看起来像一个超大的“捕捉网” */
    .stFileUploader {
        border: 3px dashed #1e90ff !important;
        border-radius: 15px;
        background-color: #f0f8ff;
        transition: all 0.3s ease;
    }
    /* 当你点击它准备粘贴时，它会变色提醒你焦点已到位 */
    .stFileUploader:active, .stFileUploader:focus-within {
        border-color: #ff4757 !important;
        background-color: #fffaf0;
        box-shadow: 0 0 15px rgba(255, 71, 87, 0.3);
    }
    .stFileUploader label {
        font-size: 1.2rem !important;
        color: #1e90ff !important;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚌 包车报价智能中心 (粘贴优化版)")

# --- 高德 Key ---
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74" 

# --- 1️⃣ 侧边栏：参数调节 ---
with st.sidebar:
    st.header("⚙️ 价格参数设置")
    p39 = st.number_input("39座单价 (元/公里)", value=2.6)
    p56 = st.number_input("56座单价 (元/公里)", value=3.6)
    b39 = st.number_input("39座起步费 (元/天)", value=800.0)
    b56 = st.number_input("56座起步费 (元/天)", value=1000.0)

# --- 2️⃣ 接收区：请务必【点击】后再【粘贴】 ---
st.subheader("📎 第一步：文件/截图接收区")
st.warning("💡 **操作技巧**：先用鼠标**点一下**下方蓝色方框（框变色即激活），然后按 **Ctrl+V**。如果粘贴不灵，说明系统拦截了，请直接将文件**拖进去**。")

# 增加 accept_multiple_files 提高兼容性
files = st.file_uploader(
    "👉 请在此处点击并粘贴截图，或上传 PDF/Word/TXT", 
    type=["jpg", "png", "jpeg", "pdf", "docx", "txt"],
    accept_multiple_files=True
)

if files:
    st.success(f"✅ 已成功接收 {len(files)} 个文件/截图！")
    with st.expander("查看已上传文件列表"):
        for f in files:
            st.write(f"📄 {f.name} ({f.type})")

# --- 3️⃣ 行程识别区 ---
st.divider()
st.subheader("⌨️ 第二步：粘贴行程文字")
raw_text = st.text_area("请在这里粘贴您从行程单（图片/PDF）中提取出的文字：", height=150, placeholder="例如：4.12 南昌接 前往葛仙村...")

# 智能提取函数
def quick_extract(text):
    if not text: return ""
    # 过滤掉行程单中常见的干扰杂词
    stop_words = [r"第\d+天", r"车程", r"入住", r"前往", r"接引", r"小时", r"h", r"约", r"住", r"接"]
    temp = text
    for sw in stop_words:
        temp = re.sub(sw, " ", temp)
    # 仅提取2-6字的汉字（通常是地名）
    names = re.findall(r'[\u4e00-\u9fa5]{2,6}', temp)
    return " ".join(dict.fromkeys(names)) # 去重并保持顺序

keywords = quick_extract(raw_text)

# --- 4️⃣ 站点确认 ---
st.subheader("📍 第三步：核对站点")
final_input = st.text_input("您可以手动修正提取出的地名（用空格隔开）：", value=keywords)

final_locs = []
if final_input:
    names = final_input.split()
    cols = st.columns(min(len(names), 4))
    for i, name in enumerate(names):
        with cols[i % 4]:
            try:
                # 优先定位江西周边坐标
                url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}&location=115.89,28.67"
                tips = requests.get(url).json().get('tips', [])
                opts = [f"{t['name']} ({t.get('district','')})" for t in tips if t.get('location')]
                if not opts: opts = [f"{name} (未搜到)"]
                
                sel = st.selectbox(f"站点 {i+1}", opts, key=f"loc_{i}")
                act_name = sel.split(" (")[0]
                coord = next((t['location'] for t in tips if t['name'] == act_name and t.get('location')), None)
                if coord: final_locs.append({"name": act_name, "coord": coord})
            except: pass

# --- 5️⃣ 自动计算与报价 ---
st.divider()
km_calc = 0
if len(final_locs) >= 2:
    try:
        origin, dest = final_locs[0]['coord'], final_locs[-1]['coord']
        mid = ";".join([l['coord'] for l in final_locs[1:-1]])
        r_url = f"https://restapi.amap.com/v3/direction/driving?origin={origin}&destination={dest}&key={AMAP_KEY}&strategy=2"
        if mid: r_url += f"&waypoints={mid}"
        res = requests.get(r_url).json()
        if res['status'] == '1':
            km_calc = int(round(int(res['route']['paths'][0]['distance']) / 1000))
    except: st.error("计算失败，请检查站点是否选择准确")

c1, c2 = st.columns(2)
with c1: final_km = st.number_input("实测公里数", value=km_calc, step=1)
with c2: days = st.number_input("用车天数", min_value=1, value=4)

f39 = int(final_km * p39 + days * b39)
f56 = int(final_km * p56 + days * b56)

st.table(pd.DataFrame({
    "车型": ["39座", "56座"],
    "里程": [f"{final_km} KM"] * 2,
    "天数": [f"{days} 天"] * 2,
    "总报价": [f"{f39} 元", f"{f56} 元"]
}))

if final_locs:
    route_text = " - ".join([l['name'] for l in final_locs])
    final_msg = f"【包车报价单】\n路线：{route_text}\n全程：约{final_km}公里\n时长：{days}天\n---\n39座：{f39}元\n56座：{f56}元"
    st.text_area("点击下方全选复制报价：", final_msg, height=120)
