import streamlit as st
import pandas as pd
import requests
import base64
import json
import re

# ==================== 1. 核心密钥配置 ====================

# [必填] 填入你刚才在百度后台复制的 V2 版本 API Key
AI_API_KEY_V2 = "bce-v3/ALTAK-EMZixkEbLJ0iEkFcaJCFc/74514893890101d198dd642b3b95ea68bed95897"

# 百度 OCR 密钥 (已配置)
BAIDU_OCR_AK = "1vBiCqNtSYFRx6GYsGwpwXdM"         
BAIDU_OCR_SK = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  

# 高德地图密钥 (已配置)
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统-AI旗舰版", layout="wide")

# ==================== 2. 功能引擎 ====================

def get_ocr_token():
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={BAIDU_OCR_AK}&client_secret={BAIDU_OCR_SK}"
    try:
        res = requests.get(url).json()
        return res.get("access_token")
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
    """使用 ERNIE-Speed-Pro-128K 提取纯净地名"""
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-pro-128k"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY_V2}"
    }
    
    # 强化版 Prompt：严禁数字和废话
    prompt = (
        f"你是一个地理数据清理专家。请从以下行程中提取地名或景点名。\n"
        f"要求：\n"
        f"1. 只输出地名，地名之间用空格分隔。\n"
        f"2. 严禁包含数字（如1、2、3）、严禁包含标点符号、严禁包含‘目的地’等字样。\n"
        f"原文内容：{text}"
    )
    
    payload = {"messages": [{"role": "user", "content": prompt}]}
    try:
        response = requests.post(url, headers=headers, json=payload)
        res = response.json()
        if "error_code" in res:
            return f"AI 错误({res['error_code']}): {res.get('error_msg')}"
        
        raw_result = res.get("result", "").strip()
        
        # --- 二次清洗逻辑：用正则表达式删掉所有数字和特定杂词 ---
        # 删掉所有数字
        clean_text = re.sub(r'\d+', '', raw_result)
        # 删掉常见的 AI 废话开头
        for junk in ["目的地", "地名", "地点", "：", ":", ".", "、"]:
            clean_text = clean_text.replace(junk, "")
            
        return clean_text.strip()
    except: return "AI 连接失败"

# ==================== 3. 侧边栏：实时报价核算 ====================

if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

with st.sidebar:
    st.header("📊 报价核算中心")
    with st.expander("⚙️ 计费标准设置", expanded=False):
        c1, c2 = st.columns(2)
        b39 = c1.number_input("39座起步费", value=800)
        p39 = c2.number_input("39座单价", value=2.6)
        b56 = c1.number_input("56座起步费", value=1000)
        p56 = c2.number_input("56座单价", value=3.6)

    st.divider()
    f_km = st.number_input("实测总公里 (KM)", value=st.session_state['km_auto'])
    f_days = st.number_input("用车总天数 (天)", value=4)
    
    res_39 = int(f_km * p39 + f_days * b39)
    res_56 = int(f_km * p56 + f_days * b56)
    
    st.markdown("### 💰 实时总报单")
    st.success(f"**3
