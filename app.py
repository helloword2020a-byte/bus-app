import streamlit as st
import pandas as pd
import requests
import re

# 页面基础配置
st.set_page_config(page_title="包车报价中心", layout="wide")

# --- 强制注入 CSS 模拟聊天输入体验 ---
st.markdown("""
    <style>
    /* 让上传框看起来像一个大型接收区 */
    .stFileUploader {
        border: 2px dashed #00a8ff;
        border-radius: 15px;
        background-color: #f0f7ff;
    }
    /* 隐藏多余的文字提示 */
    .stFileUploader section > label {
        display: none;
    }
    /* 鼠标悬停变色，暗示可以点击粘贴 */
    .stFileUploader:hover {
        border-color: #0077cc;
        background-color: #e6f2ff;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚌 包车报价智能中心")

# --- 高德 Key ---
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74" 

# --- 侧边栏：价格参数 ---
with st.sidebar:
    st.header("⚙️ 价格参数设置")
    p39 = st.number_input("39座单价 (元/公里)", value=2.6)
    p56 = st.number_input("56座单价 (元/公里)", value=3.6)
    b39 = st.number_input("39座起步费 (元/天)", value=800.0)
    b56 = st.number_input("56座起步费 (元/天)", value=1000.0)

# --- 1️⃣ 核心上传区（支持粘贴、PDF、DOCX、TXT） ---
st.subheader("📎 文件/粘贴接收区")
st.write("👉 **点击下方蓝色区域使其获得焦点后，直接按 Ctrl+V 粘贴截图，或点右侧按钮选文件。**")

uploaded_files = st.file_uploader(
    "接收区", 
    type=["jpg", "png", "jpeg", "pdf", "docx", "txt"],
    accept_multiple_files=True,
    help="点击此处后直接 Ctrl+V 粘贴剪贴板内容"
)

# 展示已上传内容
if uploaded_files:
    cols = st.columns(len(uploaded_files))
    for i, file in enumerate(uploaded_files):
        with cols[i]:
            if file.type.startswith("image"):
                st.image(file, caption=f"已粘贴图片", width=200)
            else:
                st.success(f"已载入文件: {file.name}")

# --- 2️⃣ 文字识别粘贴区 ---
st.divider()
st.subheader("⌨️ 行程文字识别")
input_text = st.text_area(
    "请在此粘贴行程文字（系统将自动提取地名）：", 
    height=150, 
    placeholder="在此粘贴您从图片或文档中提取的行程详情..."
)

def smart_extract(text):
    if not text: return ""
    # 过滤杂词
    noise = [r"第\d+天", r"车程约[\d\.]+h", r"住[^\s]+", r"下午", r"上午", r"返程", r"接送", r"行程", r"约", r"h", r"车程", r"入住", r"前往", r"接引", r"小时", r"接"]
    temp = text
    for n in noise: temp = re.sub(n, " ", temp)
    # 提取汉字
    found = re.findall(r'[\u4e00-\u9fa5]{2,6}', temp)
    forbidden = ["可以", "到了", "选择", "需要", "提示", "进行", "返回"]
    return " ".join([w for w in found if w not in forbidden and len(w) > 1])

keywords = smart_extract(input_text)

# --- 3️⃣ 选点与报价 ---
st.divider()
final_input = st.text_input("📍 确认关键词（空格分隔）：", value=keywords)

final_locations = []
if final_input:
    names = final_input.split()
    grid = st.columns(min(len(names), 4))
    for i, name in enumerate(names):
        with grid[i % 4]:
            try:
                url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}&location=115.89,28.67"
                tips = requests.get(url).json().get('tips', [])
                options = [f"{t['name']} ({t.get('district','')})" for t in tips if t.get('location')]
                if not options: options = [f"{name} (未搜到)"]
                
                chosen = st.selectbox(f"站点{i+1}: {name}", options, key=f"pos_{i}")
                act_name = chosen.split(" (")[0]
                loc = next((t['location'] for t in tips if t['name'] == act_name and t.get('location')), None)
                if loc: final_locations.append({"name": act_name, "coord": loc})
            except: pass

# --- 4️⃣ 计算结果 ---
st.divider()
auto_km = 0
if len(final_locations) >= 2:
    try:
        origin = final_locations[0]['coord']
        dest = final_locations[-1]['coord']
        ways = ";".join([l['coord'] for l in final_locations[1:-1]])
        r_url = f"https://restapi.amap.com/v3/direction/driving?origin={origin}&destination={dest}&key={AMAP_KEY}&strategy=2"
        if ways: r_url += f"&waypoints={ways}"
        res = requests.get(r_url).json()
        if res['status'] == '1':
            auto_km = int(round(int(res['route']['paths'][0]['distance']) / 1000))
    except: pass

col1, col2 = st.columns(2)
with col1: km = st.number_input("确认公里数", value=int(auto_km), step=1)
with col2: d = st.number_input("用车天数", min_value=1, value=4)

f39 = int(km * p39 + d * b39)
f56 = int(km * p56 + d * b56)

st.table(pd.DataFrame({
    "车型": ["39座", "56座"],
    "里程": [f"{km} KM"] * 2,
    "总报价": [f"{f39} 元", f"{f56} 元"]
}))

if final_locations:
    route_str = " - ".join([l['name'] for l in final_locations])
    msg = f"【包车报价单】\n路线：{route_str}\n里程：{km}公里\n天数：{d}天\n---\n39座：{f39}元\n56座：{f56}元"
    st.text_area("报价单一键复制：", msg, height=100)
