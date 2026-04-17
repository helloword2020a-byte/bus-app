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

st.set_page_config(page_title="九江祥隆报价系统-AI旗舰版", layout="wide")

# ==================== 2. 状态与样式初始化 ====================
if 'ocr_raw' not in st.session_state: st.session_state['ocr_raw'] = ""
if 'sites_list' not in st.session_state: st.session_state['sites_list'] = []
if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

# 注入 CSS：实现右侧区域单位滚动
st.markdown("""
    <style>
    .scroll-container {
        max-height: 650px;
        overflow-y: auto;
        padding-right: 10px;
        border: 1px solid #f0f2f6;
        border-radius: 10px;
    }
    .preview-box {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #ff4b4b;
        margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

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
    try:
        res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
        return "".join([i['words'] for i in res.get('words_result', [])])
    except: return "识别异常"

def ai_extract_locations_v2(text):
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-128k"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {AI_API_KEY_V2}"}
    prompt = (f"提取所有目的地地名，用空格分隔。原文：{text}")
    payload = {"messages": [{"role": "user", "content": prompt}]}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15).json()
        clean_text = re.sub(r'[^\u4e00-\u9fa5\s]', ' ', res.get("result", ""))
        return " ".join(clean_text.split())
    except: return ""

def rule_extract_locations(text):
    if not text: return ""
    clean = re.sub(r'\(.*?\)|（.*?）|\d+\.?\d*|[^\u4e00-\u9fa5\s]', ' ', text)
    for word in ['接', '送', '前往', '返程', '车程', '约', '住', '下午', '简易行程', '小时', '公里']:
        clean = clean.replace(word, ' ')
    return " ".join(clean.split()).strip()

# ==================== 4. 侧边栏：报价中心 ====================
with st.sidebar:
    st.header("📊 报价核算中心")
    with st.form("sidebar_price"):
        col_a, col_b = st.columns(2)
        b39, p39 = col_a.number_input("39起步", 800), col_b.number_input("39单价", 2.6)
        b56, p56 = col_a.number_input("56起步", 1000), col_b.number_input("56单价", 3.6)
        f_km = st.number_input("总公里 (KM)", value=st.session_state['km_auto'])
        f_days = st.number_input("用车天数", value=4)
        st.form_submit_button("💰 更新报价文案")

    res_39, res_56 = int(f_km * p39 + f_days * b39), int(f_km * p56 + f_days * b56)
    st.success(f"39座：{res_39} 元 | 56座：{res_56} 元")
    quote = f"【九江祥隆报价】\n里程：{f_km}KM | 天数：{f_days}天\n39座：{res_39}元\n56座：{res_56}元"
    st.text_area("复制结果：", value=quote, height=100)

# ==================== 5. 主页面布局 ====================
st.header("🚌 九江祥隆旅游运输报价系统 (AI 旗舰版)")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.subheader("1️⃣ 文字识别与提取")
    up_file = st.file_uploader("上传行程截图", type=["jpg", "png", "jpeg"])
    if up_file and st.button("🚀 开始文字提取", use_container_width=True):
        st.session_state['ocr_raw'] = ocr_engine(up_file.read())
    
    raw_txt = st.text_area("识别结果校对：", value=st.session_state.get('ocr_raw', ""), height=180)
    
    # 双模提取按钮
    c1, c2 = st.columns(2)
    if c1.button("✨ 智能 AI 提取", use_container_width=True):
        st.session_state['sites_list'] = ai_extract_locations_v2(raw_txt).split()
    if c2.button("🤖 自动规则提取", use_container_width=True):
        st.session_state['sites_list'] = rule_extract_locations(raw_txt).split()

    # 【新增】提取后结果的行程展示区
    if st.session_state['sites_list']:
        st.markdown(f"""
            <div class="preview-box">
                <b>提取后结果的行程：</b><br/>
                {' → '.join(st.session_state['sites_list'])}
            </div>
            """, unsafe_allow_html=True)

with m_right:
    st.subheader("2️⃣ 站点确认 (仿高德交互模式)")
    
    # 【新增】滚动容器开始
    st.markdown('<div class="scroll-container">', unsafe_allow_html=True)
    
    current_coords = []
    for i, site in enumerate(st.session_state['sites_list']):
        with st.container(border=True):
            # 仿高德：输入即搜索
            search_kw = st.text_input(f"🔎 站点 {i+1}：输入文字修改地址", value=site, key=f"kw_{i}")
            t_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={search_kw}&key={AMAP_KEY}"
            try:
                tips = requests.get(t_url, timeout=5).json().get('tips', [])
                valid = [t for t in tips if isinstance(t.get('location'), str) and t.get('location')]
                if valid:
                    sel = st.selectbox(f"确认精准地址 (站{i+1})", [f"{t['name']} ({t.get('district','')})" for t in valid], key=f"sel_{i}")
                    current_coords.append(next(t['location'] for t in valid if sel.startswith(t['name'])))
            except: pass
            
    st.markdown('</div>', unsafe_allow_html=True) # 滚动容器结束

    # ==================== 6. 核心规划控制器 ====================
    st.divider()
    if len(current_coords) >= 2:
        # 必须点击按钮才计算，不乱改数据
        if st.button("🗺️ 确认所有站点，开始规划行程", use_container_width=True, type="primary"):
            org, des, way = current_coords[0], current_coords[-1], ";".join(current_coords[1:-1])
            d_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&waypoints={way}&key={AMAP_KEY}"
            try:
                res = requests.get(d_url, timeout=5).json()
                if res['status'] == '1':
                    st.session_state['km_auto'] = int(int(res['route']['paths'][0]['distance']) / 1000)
                    st.success(f"### ✅ 规划完成！总公里数：{st.session_state['km_auto']} KM")
                    st.rerun()
                else: st.error("测距失败")
            except: st.error("接口异常")
