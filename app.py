import streamlit as st
import pandas as pd
import requests
import re
import base64
import json

# ==================== 1. 核心密钥配置 ====================
BAIDU_OCR_KEY = "1vBiCqNtSYFRx6GYsGwpwXdM"        
BAIDU_OCR_SECRET = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  
AI_API_KEY = "ALTAKRoF5rezfzpBHyvueydG2B"
AI_SECRET_KEY = "10bc499df39a472d882aee64221d1e31" 
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统-全功能版", layout="wide")

# ==================== 2. 界面样式定制 ====================
st.markdown("""
    <style>
    .block-container {padding-top: 1rem !important;}
    [data-testid="stSidebar"] {background-color: #f0f2f6; min-width: 280px;}
    .q-table { font-size: 0.95rem; border-collapse: collapse; width: 100%; margin-top: 10px; border-radius: 8px; overflow: hidden;}
    .q-table td, .q-table th { border: 1px solid #ddd; padding: 10px; text-align: center; }
    .stNumberInput div div input { font-size: 1.1rem !important; color: #1e88e5 !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

# ==================== 3. 核心功能引擎 ====================
def get_access_token(api_key, secret_key):
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
    try: return requests.get(url).json().get("access_token")
    except: return None

def ocr_engine(file_bytes):
    token = get_access_token(BAIDU_OCR_KEY, BAIDU_OCR_SECRET)
    if not token: return "OCR 授权失败"
    img64 = base64.b64encode(file_bytes).decode()
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token={token}"
    res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
    return "".join([i['words'] for i in res.get('words_result', [])])

def ai_extract_locations(text):
    token = get_access_token(AI_API_KEY, AI_SECRET_KEY)
    url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-x1-turbo-32k?access_token={token}"
    prompt = f"你是一个旅游调度。请从文字中提取纯地名，地名间用空格隔开。原文：{text}"
    payload = json.dumps({"messages": [{"role": "user", "content": prompt}]})
    try:
        res = requests.post(url, data=payload, headers={'Content-Type': 'application/json'}).json()
        return res.get("result", "").strip()
    except: return ""

# ==================== 4. 侧边栏：核心报价计费 ====================
with st.sidebar:
    st.header("📊 报价核算中心")
    with st.expander("⚙️ 计费标准设置"):
        c1, c2 = st.columns(2)
        b39 = c1.number_input("39座起步费", value=800)
        p39 = c2.number_input("39座单价", value=2.6)
        b56 = c1.number_input("56座起步费", value=1000)
        p56 = c2.number_input("56座单价", value=3.6)

    st.divider()
    f_km = st.number_input("实测总公里 (KM)", value=st.session_state['km_auto'])
    f_days = st.number_input("用车总天数 (天)", value=4)
    res_39, res_56 = int(f_km*p39 + f_days*b39), int(f_km*p56 + f_days*b56)
    
    st.markdown(f"""<table class="q-table">
        <tr style="background-color:#1e88e5; color:white;"><th>车型</th><th>总报价</th></tr>
        <tr><td>39座</td><td><b>{res_39} 元</b></td></tr>
        <tr><td>56座</td><td><b>{res_56} 元</b></td></tr>
    </table>""", unsafe_allow_html=True)

# ==================== 5. 主页面：流程操作 ====================
st.header("🚌 九江祥隆旅游运输报价系统")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.markdown("### 1️⃣ 行程智能识别")
    up_file = st.file_uploader("上传截图", type=["jpg", "png", "jpeg"])
    if up_file and st.button("🚀 开始文字识别", use_container_width=True):
        st.session_state['ocr_raw'] = ocr_engine(up_file.read())
    
    raw_txt = st.text_area("识别文本校对：", value=st.session_state.get('ocr_raw', ""), height=120)
    
    # --- 两个提取功能并排展示 ---
    col_btn1, col_btn2 = st.columns(2)
    if col_btn1.button("✨ 智能 AI 提取", use_container_width=True):
        st.session_state['sites_final'] = ai_extract_locations(raw_txt)
    
    if col_btn2.button("🤖 自动规则提取", use_container_width=True):
        # 规则提取：提取中文地名
        locs = re.findall(r'[\u4e00-\u9fa5]{2,}', raw_txt)
        st.session_state['sites_final'] = " ".join(locs)

with m_right:
    st.markdown("### 2️⃣ 站点校对 (高德实时联想)")
    site_input = st.text_input("待匹配地名 (空格隔开)：", value=st.session_state.get('sites_final', ""))
    
    confirmed_locs = []
    if site_input:
        names = site_input.split()
        for i, name in enumerate(names):
            # 使用 popover 解决手机输入框弹不出的问题
            with st.popover(f"📍 站 {i+1}：{name}", use_container_width=True):
                # 允许用户修改糊涂文字
                kw = st.text_input("修正搜索词", value=name, key=f"kw_{i}")
                # 高德 10 项联想
                t_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={kw}&key={AMAP_KEY}"
                try:
                    tips = requests.get(t_url).json().get('tips', [])
                    v_tips = [t for t in tips if t.get('location') and isinstance(t['location'], str)][:10]
                    if v_tips:
                        opts = [f"{t['name']} ({t.get('district','')})" for t in v_tips]
                        sel = st.selectbox("请选择精准地址：", opts, key=f"s_{i}")
                        st.session_state[f"coord_{i}"] = next(t['location'] for t in v_tips if t['name'] == sel.split(" (")[0])
                    else: st.warning("未找到地址")
                except: pass
            if f"coord_{i}" in st.session_state: confirmed_locs.append(st.session_state[f"coord_{i}"])

    if len(confirmed_locs) >= 2 and st.button("🗺️ 计算公里数", use_container_width=True):
        org, des, way = confirmed_locs[0], confirmed_locs[-1], ";".join(confirmed_locs[1:-1])
        r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way}"
        try:
            res = requests.get(r_url).json()
            st.session_state['km_auto'] = int(int(res['route']['paths'][0]['distance']) / 1000)
            st.rerun()
        except: st.error("计算失败")
