import streamlit as st
import pandas as pd
import requests
import re

# 页面基础配置
st.set_page_config(page_title="包车报价-拖拽识别版", layout="wide")

# 自定义样式：让上传组件更醒目
st.markdown("""
    <style>
    .stFileUploader {
        border: 2px dashed #4CAF50;
        border-radius: 10px;
        padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚌 包车报价系统（支持图片拖拽）")

# --- 高德 Key ---
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74" 

# --- 侧边栏：单价设置 ---
st.sidebar.header("⚙️ 价格参数设置")
p39 = st.sidebar.number_input("39座单价 (元/公里)", value=2.6)
p56 = st.sidebar.number_input("56座单价 (元/公里)", value=3.6)
b39 = st.sidebar.number_input("39座起步费 (元/天)", value=800.0)
b56 = st.sidebar.number_input("56座起步费 (元/天)", value=1000.0)

# --- 1️⃣ 拖拽上传区 ---
st.subheader("📸 第一步：上传/拖拽行程图")
uploaded_file = st.file_uploader("👉 直接把行程截图拖到这里 (支持 JPG, PNG)", type=["jpg", "png", "jpeg"])

if uploaded_file:
    st.image(uploaded_file, caption='已加载图片', width=400)
    st.info("💡 识别提示：请使用手机或电脑自带的‘提取图中文字’功能，将识别出的文字粘贴在下方框内。")

# --- 2️⃣ 智能粘贴区 ---
st.subheader("⌨️ 第二步：粘贴行程文本")
smart_text = st.text_area("在此粘贴行程文字，系统将自动抠取地名：", height=120)

# 智能提取逻辑
def smart_extract(text):
    if not text: return ""
    # 过滤噪音词
    noise = [r"第\d+天", r"车程约[\d\.]+h", r"住[^\s]+", r"下午", r"上午", r"返程", r"接送", r"简易行程", r"行程", r"约", r"h", r"车程", r"入住", r"前往", r"接引", r"小时", r"约"]
    temp_text = text
    for n in noise:
        temp_text = re.sub(n, " ", temp_text)
    # 提取汉字
    raw_words = re.findall(r'[\u4e00-\u9fa5]{2,6}', temp_text)
    # 去重保留顺序
    result = []
    for w in raw_words:
        if w not in result and len(w) > 1:
            result.append(w)
    return " ".join(result)

identified_names = smart_extract(smart_text)

# --- 3️⃣ 确认线路与选点 ---
st.divider()
st.subheader("3️⃣ 确认线路与精确选点")
final_input = st.text_input("识别出的关键词（可手动增减）：", value=identified_names)

final_locations = []
if final_input:
    names = final_input.split()
    for i, name in enumerate(names):
        try:
            # 搜索建议
            search_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}&location=115.89,28.67"
            tips = requests.get(search_url).json().get('tips', [])
            options = [f"{t['name']} ({t.get('district','')})" for t in tips if t.get('location')]
            if not options: options = [f"{name} (未搜到)"]
            
            chosen = st.selectbox(f"📍 第{i+1}站: {name}", options, key=f"sel_{i}")
            
            # 解析坐标
            actual_name = chosen.split(" (")[0]
            loc = next((t['location'] for t in tips if t['name'] == actual_name and t.get('location')), None)
            if loc: final_locations.append({"name": actual_name, "coord": loc})
        except: pass

# --- 4️⃣ 里程计算与报价 ---
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
            st.success(f"🗺️ 路线已串联，测算里程：{auto_dist} KM")
    except: st.error("计算失败")

c1, c2 = st.columns(2)
with c1:
    final_km = st.number_input("最终里程 (可微调)", value=auto_dist, step=1)
with c2:
    days = st.number_input("用车天数", min_value=1, value=4)

f39 = int(final_km * p39 + days * b39)
f56 = int(final_km * p56 + days * b56)

st.table(pd.DataFrame({
    "车型": ["39座", "56座"],
    "里程": [f"{final_km} KM"] * 2,
    "总报价": [f"{f39} 元", f"{f56} 元"]
}))

# 复制区域
if final_locations:
    route_str = " - ".join([l['name'] for l in final_locations])
    msg = f"【包车报价单】\n路线：{route_str}\n里程：约{final_km}公里\n天数：{days}天\n---\n39座报价：{f39}元\n56座报价：{f56}元\n(报价含路桥费，不含司机食宿)"
    st.text_area("点击全选复制报价：", msg, height=150)
