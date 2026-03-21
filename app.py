import streamlit as st
import pandas as pd
import requests
import re
import base64
import json

# --- 1. 基础配置 ---
# 百度 OCR 密钥 (保持您原有的)
BAIDU_API_KEY = "1vBiCqNtSYFRx6GYsGwpwXdM"        
BAIDU_SECRET_KEY = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  
# 百度千帆 AI 密钥 (用于接入 ERNIE-Speed-Pro-128K)
AI_API_KEY = "bce-v3/ALTAK-9aoqLxWVRWAlk87GMFUI6/4bd21140ab38b1883ea5fa7608063fecf89c5bd2"
AI_SECRET_KEY = "这里请替换为您页面显示的Secret_Key" 

AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统-智能旗舰版", layout="wide")

# --- 2. 界面样式 (保留您的原生样式) ---
st.markdown("""
    <style>
    .block-container {padding-top: 1rem !important;}
    [data-testid="stSidebar"] {background-color: #f0f2f6; min-width: 250px;}
    .q-table { font-size: 0.95rem; border-collapse: collapse; width: 100%; margin-top: 10px; border-radius: 8px; overflow: hidden;}
    .q-table td, .q-table th { border: 1px solid #ddd; padding: 8px; text-align: center; }
    .stNumberInput div div input { font-size: 1.1rem !important; color: #1e88e5 !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

# --- 3. 核心引擎：OCR + AI 逻辑 ---

def get_access_token(api_key, secret_key):
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
    try: return requests.get(url).json().get("access_token")
    except: return None

def ocr_engine(file_bytes):
    token = get_access_token(BAIDU_API_KEY, BAIDU_SECRET_KEY)
    if not token: return "授权失败"
    img64 = base64.b64encode(file_bytes).decode()
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token={token}"
    res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
    return "".join([i['words'] for i in res.get('words_result', [])])

def ai_extract_locations(text):
    """【新增】接入 ERNIE-Speed-Pro-128K 进行智能地名提取"""
    token = get_access_token(AI_API_KEY, AI_SECRET_KEY)
    if not token: return "AI 授权失败"
    
    url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-pro-128k?access_token={token}"
    
    # 精准控制：只让 AI 输出地名，解决“南昌接”变“理发店”的问题
    prompt = f"""你是一个旅游计调。请从这段OCR文字中提取出行程经过的所有真实地名。
    要求：1. 删掉所有动作词（如：接、送、住、车程、简易行程、约3h）。
    2. 比如“南昌接”提取为“南昌”，“住大觉山”提取为“大觉山”。
    3. 只按顺序输出地名，中间用空格隔开，不要任何解释。
    文字内容：{text}"""
    
    payload = json.dumps({"messages": [{"role": "user", "content": prompt}]})
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers, data=payload).json()
    return response.get("result", "").strip()

# --- 4. 侧边栏：核心报价工作台 (保留您的计算逻辑) ---
with st.sidebar:
    st.header("📊 报价核算中心")
    with st.expander("⚙️ 计费标准设置", expanded=False):
        c1, c2 = st.columns(2)
        b39 = c1.number_input("39座起步", value=800)
        p39 = c2.number_input("39座单价", value=2.6)
        b5
