import streamlit as st
import pandas as pd
import requests
import re
from io import BytesIO

# 页面基础配置
st.set_page_config(page_title="多功能包车报价系统", layout="wide")

# 自定义 CSS 模拟“聊天框+号”风格
st.markdown("""
    <style>
    .stFileUploader section {
        padding: 0px !important;
    }
    .stFileUploader label {
        display: none;
    }
    /* 模拟一个带+号的上传区域 */
    .upload-container {
        border: 2px dashed #00a8ff;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        background-color: #f0f7ff;
        cursor: pointer;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚌 包车报价智能中心")

# --- 高德 Key ---
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74" 

# --- 侧边栏：单价设置 ---
with st.sidebar:
    st.header("⚙️ 价格参数设置")
    p39 = st.number_input("39座单价 (元/公里)", value=2.6)
    p56 = st.number_input("56座单价 (元/公里)", value=3.6)
    b39 = st.number_input("39座起步费 (元/天)", value=800.0)
    b56 = st.number_input("56座起步费 (元/天)", value=1000.0)

# --- 1️⃣ 多功能文件/粘贴区 ---
st.subheader("📎 文件处理中心 (支持多格式 & 粘贴)")

# 同时支持图片、PDF、Word、文本
all_files = st.file_uploader(
    "➕ 点击选择或直接 Ctrl+V 粘贴文件 (支持图片/PDF/DOCX/TXT)", 
    type=["jpg", "png", "jpeg", "pdf", "docx", "txt"],
    accept_multiple_files=True
)

if all_files:
    cols = st.columns(len(all_files))
    for idx, file in enumerate(all_files):
        with cols[idx]:
            if file.type.startswith("image"):
                st.image(file, caption=f"图片: {file.name}", width=150)
            else:
                st.info(f"📄 已载入: {file.name}")
    st.success(f"已成功加载 {len(all_files)} 个文件，请手动提取文字粘贴在下方。")

# --- 2️⃣ 智能文本输入区 ---
st.subheader("⌨️ 行程文字粘贴")
smart_text = st.text_area(
    "在此粘贴识别出的行程内容：", 
    height=150, 
    placeholder="在此 Ctrl+V 粘贴您从 PDF、Word 或图片中提取的文字..."
)

# 核心函数：地名智能提取
def smart_extract(text):
    if not text: return ""
    noise = [r"第\d+天", r"车程约[\d\.]+h", r"住[^\s]+", r"下午", r"上午", r"返程", r"接送", r"行程", r"约", r"h", r"车程", r"入住", r"前往", r"接引", r"小时", r"接"]
    temp_text = text
    for n in noise:
        temp_text = re.sub(n, " ", temp_text)
    raw_words = re.findall(r'[\u4e00-\u9fa5]{2,6}', temp_text)
    forbidden = ["可以", "到了", "选择", "需要", "提示", "进行", "返回"]
    result = []
    for w in raw_words:
        if w not in result and len(w) > 1 and w not in forbidden:
            result.append(w)
    return " ".join(result)

identified_names = smart_extract(smart_text)

# --- 3️⃣ 确认选点 ---
st.divider()
final_input = st.text_input("📍 识别出的站点关键词（可手动微调）：", value=identified_names)

final_locations = []
if final_input:
    names = final_input.split()
    # 采用更紧凑的横向布局显示选点
    grid = st.columns(min(len(names), 4))
    for i, name in enumerate(names):
        with grid[i % 4]:
            try:
                search_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}&location=115.89,28.67"
                tips = requests.get(search_url).json().get('tips', [])
                options = [f"{t['name']} ({t.get('district','')})" for t in tips if t.get('location')]
                if not options: options = [f"{name} (未搜到)"]
                
                chosen = st.selectbox(f"第{i+1}站: {name}", options, key=f"sel_{i}")
                actual_name = chosen.split(" (")[0]
                loc = next((t['location'] for t in tips if t['name'] == actual_name and t.get('location')), None)
                if loc: final_locations.append({"name": actual_name, "coord": loc})
            except: pass

# --- 4️⃣ 计算里程与报价 ---
st.divider()
auto_dist = 0
if len(final_locations) >= 2:
    try:
        origin = final_locations[0]['coord']
        dest = final_locations[-1]['coord']
        ways = ";".join([l['coord'] for l in final_locations[1:-1]])
        route_url = f"https://restapi.amap.com/v3/direction/driving?origin={origin}&destination={dest}&key={AMAP_KEY}&strategy=2"
        if ways: route_url += f"&waypoints={ways}"
        
        r = requests.get(route_url).json()
        if r['status'] == '1':
            auto_dist = int(round(int(r['route']['paths'][0]['distance']) / 1000))
            st.info(f"📏 智能规划路线成功，全程约 {auto_dist} 公里")
    except: st.error("计算失败，请检查地点")

col_a, col_b = st.columns(2)
with col_a:
    final_km = st.number_input("最终里程确认", value=int(auto_dist), step=1)
with col_b:
    days = st.number_input("用车天数", min_value=1, value=4)

f39 = int(final_km * p39 + days * b39)
f56 = int(final_km * p56 + days * b56)

st.table(pd.DataFrame({
    "车型": ["39座", "56座"],
    "里程": [f"{final_km} KM"] * 2,
    "天数": [f"{days} 天"] * 2,
    "报价": [f"{f39} 元", f"{f56} 元"]
}))

if final_locations:
    route_str = " - ".join([l['name'] for l in final_locations])
    msg = f"【包车报价单】\n路线：{route_str}\n里程：约{final_km}公里\n天数：{days}天\n---\n39座：{f39}元\n56座：{f56}元"
    st.text_area("点击全选复制报价信息：", msg, height=120)
