import streamlit as st
import pandas as pd
import requests
import re
import base64
import json

# ==================== 1. 核心密钥配置 (完整保留) ====================
AI_API_KEY_V2 = "bce-v3/ALTAK-EMZixkEbLJ0iEkFcaJCFc/74514893890101d198dd642b3b95ea68bed95897"
BAIDU_OCR_AK = "1vBiCqNtSYFRx6GYsGwpwXdM"         
BAIDU_OCR_SK = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统-旗舰版", layout="wide")

# ==================== 2. 三栏独立滚动样式定义 ====================
# 明确要求三个框单独分开并可滚动
st.markdown("""
    <style>
    /* 统一滚动容器样式 */
    .main-col-container {
        height: 85vh;
        overflow-y: auto;
        overflow-x: hidden;
        padding: 15px;
        border: 1px solid #e6e9ef;
        border-radius: 10px;
        background-color: #ffffff;
    }
    .preview-box {
        background-color: #fff4f4;
        padding: 12px;
        border-radius: 5px;
        border: 1px dashed #ff4b4b;
        margin: 10px 0;
        font-size: 0.9rem;
    }
    </style>
    """, unsafe_allow_html=True)

# 初始化状态
if 'ocr_raw' not in st.session_state: st.session_state['ocr_raw'] = ""
if 'extracted_sites' not in st.session_state: st.session_state['extracted_sites'] = [] # 提取后的临时存放
if 'final_stations' not in st.session_state: st.session_state['final_stations'] = []  # 填充后的正式站点
if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

# ==================== 3. 后端引擎 ====================
def get_ocr_token():
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={BAIDU_OCR_AK}&client_secret={BAIDU_OCR_SK}"
    try: return requests.get(url).json().get("access_token")
    except: return None

def ocr_engine(file_bytes):
    token = get_ocr_token()
    if not token: return "OCR 授权失败"
    img64 = base64.b64encode(file_bytes).decode()
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token={token}"
    try:
        res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
        return "".join([i['words'] for i in res.get('words_result', [])])
    except: return "识别异常"

def ai_extract(text):
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-128k"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {AI_API_KEY_V2}"}
    prompt = f"提取目的地地名，空格分隔。原文：{text}"
    try:
        res = requests.post(url, headers=headers, json={"messages": [{"role": "user", "content": prompt}]}).json()
        return re.sub(r'[^\u4e00-\u9fa5\s]', ' ', res.get("result", "")).split()
    except: return []

def rule_extract(text):
    clean = re.sub(r'\(.*?\)|（.*?）|\d+\.?\d*|[^\u4e00-\u9fa5\s]', ' ', text or "")
    for word in ['接', '送', '前往', '返程', '车程', '住', '小时', '公里']:
        clean = clean.replace(word, ' ')
    return clean.split()

# ==================== 4. 页面布局：三柱独立模式 ====================
# 左侧报价、中间识别、右侧确认
col_sidebar, col_middle, col_right = st.columns([0.8, 1, 1.2])

# --- 第一柱：报价核算中心 ---
with col_sidebar:
    st.markdown('<div class="main-col-container">', unsafe_allow_html=True)
    st.header("📊 报价核算中心")
    with st.form("price_form"):
        c1, c2 = st.columns(2)
        b39, p39 = c1.number_input("39起步", 800), c2.number_input("39单价", 2.6)
        b56, p56 = c1.number_input("56起步", 1000), c2.number_input("56单价", 3.6)
        f_km = st.number_input("总公里 (KM)", value=st.session_state['km_auto'])
        f_days = st.number_input("天数", 4)
        st.form_submit_button("💰 更新报价")
    
    res39, res56 = int(f_km*p39 + f_days*b39), int(f_km*p56 + f_days*b56)
    st.info(f"39座: {res39}元 | 56座: {res56}元")
    st.text_area("复制文案", f"里程:{f_km}KM\n39座:{res39}元\n56座:{res56}元", height=100)
    st.markdown('</div>', unsafe_allow_html=True)

# --- 第二柱：文字识别与提取 ---
with col_middle:
    st.markdown('<div class="main-col-container">', unsafe_allow_html=True)
    st.header("1️⃣ 文字识别提取")
    up_file = st.file_uploader("上传截图", type=["jpg", "png"])
    if up_file and st.button("🚀 开始 OCR 识别", use_container_width=True):
        st.session_state['ocr_raw'] = ocr_engine(up_file.read())
    
    raw_edit = st.text_area("识别文本校对", value=st.session_state['ocr_raw'], height=200)
    
    # 双模提取按钮
    btn_a, btn_b = st.columns(2)
    if btn_a.button("✨ 智能 AI 提取", use_container_width=True):
        st.session_state['extracted_sites'] = ai_extract(raw_edit)
    if btn_b.button("🤖 自动规则提取", use_container_width=True):
        st.session_state['extracted_sites'] = rule_extract(raw_edit)
    
    # 预览提取结果
    if st.session_state['extracted_sites']:
        st.markdown('<div class="preview-box"><b>提取结果预览：</b><br/>' + " → ".join(st.session_state['extracted_sites']) + '</div>', unsafe_allow_html=True)
        
        # 【新增】填充按钮：不点这个按钮，右侧站点不刷新
        if st.button("🚀 点击填充至站点确认区", type="primary", use_container_width=True):
            st.session_state['final_stations'] = st.session_state['extracted_sites']
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- 第三柱：站点确认与测距 (独立滚动) ---
with col_right:
    st.markdown('<div class="main-col-container">', unsafe_allow_html=True)
    st.header("2️⃣ 站点确认与测距")
    
    current_coords = []
    # 仅当点击了“填充按钮”后，这里才会循环显示站点
    for i, name in enumerate(st.session_state['final_stations']):
        with st.container(border=True):
            kw = st.text_input(f"站{i+1} 搜索词", value=name, key=f"kw_{i}")
            t_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={kw}&key={AMAP_KEY}"
            try:
                tips = requests.get(t_url, timeout=5).json().get('tips', [])
                valid = [t for t in tips if isinstance(t.get('location'), str) and t.get('location')]
                if valid:
                    sel = st.selectbox(f"确认站{i+1}", [f"{t['name']} ({t.get('district','')})" for t in valid], key=f"sel_{i}")
                    loc = next(t['location'] for t in valid if sel.startswith(t['name']))
                    current_coords.append(loc)
            except: pass

    st.divider()
    if len(current_coords) >= 2:
        # 必须点击开始规划才测距
        if st.button("🗺️ 开始规划行程 (计算公里)", use_container_width=True, type="primary"):
            org, des, way = current_coords[0], current_coords[-1], ";".join(current_coords[1:-1])
            d_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&waypoints={way}&key={AMAP_KEY}"
            res = requests.get(d_url).json()
            if res['status'] == '1':
                st.session_state['km_auto'] = int(int(res['route']['paths'][0]['distance']) / 1000)
                st.success(f"计算完成：{st.session_state['km_auto']} KM")
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
