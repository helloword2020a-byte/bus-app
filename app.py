import streamlit as st
import pandas as pd
import requests
import re
import base64
import json

# ==================== 1. 核心密钥配置 ====================
AI_API_KEY_V2 = "bce-v3/ALTAK-EMZixkEbLJ0iEkFcaJCFc/74514893890101d198dd642b3b95ea68bed95897"
BAIDU_OCR_AK = "1vBiCqNtSYFRx6GYsGwpwXdM"         
BAIDU_OCR_SK = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统", layout="wide")

# ==================== 2. 初始化“记忆库” (防止重复刷新) ====================
if 'km_cache' not in st.session_state: st.session_state['km_cache'] = 0
if 'sites_cache' not in st.session_state: st.session_state['sites_cache'] = ""
if 'ocr_cache' not in st.session_state: st.session_state['ocr_cache'] = ""

# ==================== 3. 功能引擎 ====================

def get_ocr_token():
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={BAIDU_OCR_AK}&client_secret={BAIDU_OCR_SK}"
    try: return requests.get(url).json().get("access_token")
    except: return None

def ocr_engine(file_bytes):
    token = get_ocr_token()
    if not token: return "OCR 授权失败"
    img64 = base64.b64encode(file_bytes).decode()
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token={token}"
    res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
    text = "".join([i['words'] for i in res.get('words_result', [])])
    st.session_state['ocr_cache'] = text
    return text

def ai_extract_v3(text):
    """强力智能提取：精准、去噪、拆分"""
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-pro-128k"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {AI_API_KEY_V2}"}
    prompt = f"请从行程中提取地名（包括城市、景点）。要求：只输出地名，地名间用空格分开。严禁输出数字、日期、括号和动作词。原文：{text}"
    payload = {"messages": [{"role": "user", "content": prompt}]}
    try:
        res = requests.post(url, headers=headers, json=payload).json()
        clean = res.get("result", "").strip()
        st.session_state['sites_cache'] = clean
        return clean
    except: return "AI提取失败"

def rule_extract_v3(text):
    """极致规则提取：正则表达式暴力去除非地名文字"""
    if not text: return ""
    # 1. 删掉所有括号及其内部内容 (如: 车程3h)
    text = re.sub(r'\(.*?\)', ' ', text)
    text = re.sub(r'（.*?）', ' ', text)
    # 2. 删掉所有数字和日期 (如: 4.11)
    text = re.sub(r'\d+\.?\d*', ' ', text)
    # 3. 删掉所有标点符号
    text = re.sub(r'[^\u4e00-\u9fa5\s]', ' ', text)
    # 4. 过滤掉常见动作词
    for word in ['接', '送', '住', '前往', '返程', '第', '天', '高铁', '酒店', '下午', '早上']:
        text = text.replace(word, ' ')
    clean = " ".join(text.split())
    st.session_state['sites_cache'] = clean
    return clean

# ==================== 4. 侧边栏：报价核算 (现在修改这里不会导致地图重跑) ====================
with st.sidebar:
    st.header("📊 报价核算中心")
    st.subheader("⚙️ 计费标准设置")
    col_a, col_b = st.columns(2)
    b39 = col_a.number_input("39座起步费", value=800)
    p39 = col_b.number_input("39座单价", value=2.6)
    b56 = col_a.number_input("56座起步费", value=1000)
    p56 = col_b.number_input("56座单价", value=3.6)

    st.divider()
    # 这里的实测公里优先读取地图计算的记忆值
    f_km = st.number_input("实测总公里 (KM)", value=st.session_state['km_cache'])
    f_days = st.number_input("用车总天数 (天)", value=4)
    
    res_39 = int(f_km * p39 + f_days * b39)
    res_56 = int(f_km * p56 + f_days * b56)
    
    st.markdown("### 💰 实时总报单")
    st.success(f"🚌 **39座大巴：{res_39} 元**")
    st.info(f"🚌 **56座大巴：{res_56} 元**")

    st.divider()
    st.markdown("📄 **报价发送文案**")
    quote_text = f"【九江祥隆旅游报价】\n里程：{f_km}KM | 天数：{f_days}天\n---\n39座：{res_39}元\n56座：{res_56}元"
    st.text_area("复制发送：", value=quote_text, height=120)

# ==================== 5. 主页面 ====================
st.header("🚌 九江祥隆旅游运输报价系统")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.markdown("### 1️⃣ 文字识别")
    up_file = st.file_uploader("上传截图", type=["jpg", "png", "jpeg"])
    if up_file and st.button("🚀 开始识别"):
        ocr_engine(up_file.read())
    
    raw_txt = st.text_area("文本核对：", value=st.session_state['ocr_cache'], height=150)
    
    st.markdown("#### **站点提取方案**")
    c1, c2 = st.columns(2)
    if c1.button("✨ 智能 AI 提取"):
        ai_extract_v3(raw_txt)
    if c2.button("🤖 自动规则提取"):
        rule_extract_v3(raw_txt)

with m_right:
    st.markdown("### 2️⃣ 测距规划")
    site_input = st.text_input("待匹配地名：", value=st.session_state['sites_cache'])
    
    confirmed_locs = []
    if site_input:
        names = site_input.split()
        for i, name in enumerate(names):
            url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
            try:
                tips = requests.get(url).json().get('tips', [])
                valid_tips = [t for t in tips if t.get('location')]
                if valid_tips:
                    sel = st.selectbox(f"站{i+1}: {name}", [f"{t['name']} ({t.get('district','')})" for t in valid_tips], key=f"s_{i}")
                    confirmed_locs.append(next(t['location'] for t in valid_tips if sel.startswith(t['name'])))
            except: pass

    if len(confirmed_locs) >= 2:
        if st.button("🗺️ 计算总公里数"):
            org, des, way = confirmed_locs[0], confirmed_locs[-1], ";".join(confirmed_locs[1:-1])
            r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way}"
            res = requests.get(r_url).json()
            if res['status'] == '1':
                km = int(round(int(res['route']['paths'][0]['distance']) / 1000))
                st.session_state['km_cache'] = km # 存入记忆，不再重跑
                st.success(f"规划成功：{km} KM")
                st.rerun()
