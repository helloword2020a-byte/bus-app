import streamlit as st
import pandas as pd
import requests
import re
import base64

# 页面基础配置
st.set_page_config(page_title="包车报价智能中心-全自动版", layout="wide")

# --- 高德 & 百度 OCR 配置 (建议去百度云申请免费 API Key) ---
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74" 
# 这里如果为空，系统会提示您手动粘贴文字
BAIDU_APP_ID = "" 
BAIDU_API_KEY = ""
BAIDU_SECRET_KEY = ""

st.markdown("""
    <style>
    .stFileUploader { border: 2px dashed #1e90ff; border-radius: 15px; background-color: #f0f8ff; }
    .stFileUploader:focus-within { border-color: #ff4757; background-color: #fffaf0; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚌 包车报价智能中心 (粘贴即识别版)")

# --- 侧边栏参数 ---
with st.sidebar:
    st.header("⚙️ 价格参数设置")
    p39, p56 = st.number_input("39座单价", value=2.6), st.number_input("56座单价", value=3.6)
    b39, b56 = st.number_input("39座起步", value=800.0), st.number_input("56座起步", value=1000.0)

# --- 核心逻辑：智能提取地名 ---
def smart_extract(text):
    if not text: return ""
    noise = [r"第\d+天", r"车程", r"入住", r"前往", r"接引", r"小时", r"h", r"约", r"住", r"接", r"下午", r"上午"]
    for n in noise: text = re.sub(n, " ", text)
    found = re.findall(r'[\u4e00-\u9fa5]{2,6}', text)
    forbidden = ["可以", "到了", "选择", "需要", "提示", "进行", "返回"]
    return " ".join([w for w in found if w not in forbidden and len(w) > 1])

# --- 1️⃣ 接收区：支持直接 Ctrl+V 粘贴 ---
st.subheader("📎 第一步：粘贴截图/上传文件")
st.info("💡 **操作**：点一下蓝框（变色后），直接按 **Ctrl+V**。")

files = st.file_uploader("接收区", type=["jpg", "png", "jpeg", "pdf"], accept_multiple_files=True)

auto_text = ""
if files:
    for f in files:
        if f.type.startswith("image"):
            st.image(f, width=200, caption="已收到的截图")
            # 这里原本应该触发 OCR，由于没有配置 Key，我们先引导用户使用第二步
            st.warning("📸 已收到图片！请在下方粘贴该图片的行程文字以触发计算。")

# --- 2️⃣ 文字处理区 ---
st.divider()
st.subheader("⌨️ 第二步：粘贴/调整行程文字")
# 如果未来接入了 OCR，这里会自动填充
input_text = st.text_area("在此粘贴文字行程：", value=auto_text, height=150, placeholder="例如：南昌出发 去大觉山 葛仙村...")

keywords = smart_extract(input_text)

# --- 3️⃣ 站点确认与路径规划 ---
st.subheader("📍 第三步：核对站点")
final_input = st.text_input("识别地名（空格分隔）：", value=keywords)

final_locs = []
if final_input:
    names = final_input.split()
    cols = st.columns(min(len(names), 4))
    for i, name in enumerate(names):
        with cols[i % 4]:
            try:
                url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}&location=115.89,28.67"
                tips = requests.get(url).json().get('tips', [])
                opts = [f"{t['name']} ({t.get('district','')})" for t in tips if t.get('location')]
                sel = st.selectbox(f"站 {i+1}", opts or [f"{name}(未搜到)"], key=f"v_{i}")
                coord = next((t['location'] for t in tips if t['name'] == sel.split(" (")[0]), None)
                if coord: final_locs.append({"name": sel.split(" (")[0], "coord": coord})
            except: pass

# --- 4️⃣ 自动测算报价 ---
if len(final_locs) >= 2:
    st.divider()
    try:
        origin, dest = final_locs[0]['coord'], final_locs[-1]['coord']
        mid = ";".join([l['coord'] for l in final_locs[1:-1]])
        r_url = f"https://restapi.amap.com/v3/direction/driving?origin={origin}&destination={dest}&key={AMAP_KEY}&strategy=2"
        if mid: r_url += f"&waypoints={mid}"
        res = requests.get(r_url).json()
        km = int(round(int(res['route']['paths'][0]['distance']) / 1000))
        
        c1, c2 = st.columns(2)
        with c1: f_km = st.number_input("实测公里", value=km)
        with c2: days = st.number_input("用车天数", value=4)
        
        f39, f56 = int(f_km * p39 + days * b39), int(f_km * p56 + days * b56)
        st.table(pd.DataFrame({"车型": ["39座", "56座"], "里程": [f"{f_km}KM"]*2, "报价": [f"{f39}元", f"{f56}元"]}))
        
        route_path = " - ".join([l['name'] for l in final_locs])
        st.text_area("复制报价：", f"路线：{route_path}\n里程：{f_km}KM\n39座：{f39}元\n56座：{f56}元", height=100)
    except: st.error("计算出错")
