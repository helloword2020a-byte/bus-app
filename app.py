import streamlit as st
import pandas as pd
import requests
import re
from PIL import Image

# 页面基础配置
st.set_page_config(page_title="包车报价-图片识别版", layout="wide")
st.title("🚌 包车报价系统（图片+文字智能识别）")

# --- 高德 Key ---
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74" 

# --- 侧边栏：单价设置 ---
st.sidebar.header("单价/起步费调节")
p39 = st.sidebar.number_input("39座单价", value=2.6)
p56 = st.sidebar.number_input("56座单价", value=3.6)
b39 = st.sidebar.number_input("39座起步费", value=800.0)
b56 = st.sidebar.number_input("56座起步费", value=1000.0)

# --- 核心函数：智能提取地名 ---
def smart_extract(text):
    if not text: return ""
    # 过滤掉杂词、时间、住宿等描述
    noise = [
        r"第\d+天", r"车程约[\d\.]+h", r"住[^\s]+", r"下午", r"上午", r"返程", r"接送", 
        r"简易行程", r"行程", r"约", r"h", r"车程", r"入住", r"前往", r"接引"
    ]
    temp_text = text
    for n in noise:
        temp_text = re.sub(n, " ", temp_text)
    # 提取2-6字汉字
    raw_words = re.findall(r'[\u4e00-\u9fa5]{2,6}', temp_text)
    # 去重保留顺序
    result = []
    for w in raw_words:
        if w not in result and len(w) > 1:
            result.append(w)
    return " ".join(result)

# --- 新增：图片上传功能 ---
st.subheader("📸 方式一：上传行程图片")
uploaded_file = st.file_uploader("上传行程截图（支持jpg/png）", type=["asm", "jpg", "png", "jpeg"])

ocr_text = ""
if uploaded_file is not None:
    st.image(uploaded_file, caption='已上传图片', width=300)
    st.warning("ℹ️ 提示：云端 OCR 需要配置高级接口。目前建议您：截图后长按图片“提取文字”，然后粘贴到下方。")

# --- 方式二：粘贴文本 ---
st.subheader("⌨️ 方式二：粘贴行程文本")
smart_text = st.text_area("直接粘贴行程内容：", height=100, placeholder="例如：4.11 南昌接 前往大觉山...")

# 汇总提取结果
identified_names = smart_extract(smart_text)

# --- 第一步：确认线路 ---
st.divider()
st.subheader("1️⃣ 确认线路关键词")
final_input = st.text_input("识别出的地名（如有误请在此手动增减）", value=identified_names)

# --- 第二步：精确选点 ---
st.subheader("2️⃣ 确认精确位置")
final_locations = []
if final_input:
    names = final_input.split()
    for i, name in enumerate(names):
        try:
            # 增加江西区域偏好，避免搜到外省
            search_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}&location=115.89,28.67"
            tips = requests.get(search_url).json().get('tips', [])
            options = [f"{t['name']} ({t.get('district','')})" for t in tips if t.get('location')]
            if not options: options = [f"{name} (未搜到)"]
            
            chosen = st.selectbox(f"📍 第{i+1}站: {name}", options, key=f"sel_{i}")
            
            # 拿坐标
            actual_name = chosen.split(" (")[0]
            loc = next((t['location'] for t in tips if t['name'] == actual_name), None)
            if loc: final_locations.append({"name": actual_name, "coord": loc})
        except: pass

# --- 第三步：测算 ---
st.divider()
auto_dist = 0
if len(final_locations) >= 2:
    origin = final_locations[0]['coord']
    dest = final_locations[-1]['coord']
    ways = ";".join([l['coord'] for l in final_locations[1:-1]])
    
    route_url = f"https://restapi.amap.com/v3/direction/driving?origin={origin}&destination={dest}&key={AMAP_KEY}&strategy=2&waypoints={ways}"
    r = requests.get(route_url).json()
    if r['status'] == '1':
        auto_dist = int(round(int(r['route']['paths'][0]['distance']) / 1000))
        st.success(f"✅ 测算里程：{auto_dist} KM")

# --- 第四步：报价 ---
c1, c2 = st.columns(2)
with c1:
    final_km = st.number_input("里程修正", value=auto_dist, step=1)
with c2:
    days = st.number_input("用车天数", min_value=1, value=4)

f39 = int(final_km * p39 + days * b39)
f56 = int(final_km * p56 + days * b56)

st.table(pd.DataFrame({"车型":["39座","56座"], "里程":[f"{final_km}KM"]*2, "总报价":[f"{f39}元", f"{f56}元"]}))

# 复制区域
if final_locations:
    route_str = " - ".join([l['name'] for l in final_locations])
    msg = f"【包车报价单】\n路线：{route_str}\n里程：约{final_km}公里\n天数：{days}天\n---\n39座：{f39}元\n56座：{f56}元"
    st.text_area("复制文本：", msg)
