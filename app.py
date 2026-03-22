import streamlit as st
import pandas as pd
import requests
import re
import base64
import json

# ==================== 1. 核心密钥配置 ====================
# [注意] 请务必在此处填入您在百度千帆后台真实的 API Key 和 Secret Key
AI_API_KEY = "这里填入你的API_Key"
AI_SECRET_KEY = "这里填入你的Secret_Key" 

BAIDU_OCR_AK = "1vBiCqNtSYFRx6GYsGwpwXdM"         
BAIDU_OCR_SK = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统", layout="wide")

# 初始化记忆库
if 'sites_final' not in st.session_state: st.session_state['sites_final'] = ""
if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

# ==================== 2. 核心引擎 (修复点击无反应) ====================

def get_ai_token():
    """独立获取 AI 提取专用的 Access Token"""
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={AI_API_KEY}&client_secret={AI_SECRET_KEY}"
    try:
        res = requests.get(url, timeout=10).json()
        return res.get("access_token")
    except: return None

def ai_extract_v3(text):
    """【旗舰提取】解决无反应问题，增加超时处理"""
    token = get_ai_token()
    if not token:
        st.error("AI 授权失败，请检查 API Key 和 Secret Key 是否填写正确。")
        return
    
    url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-128k?access_token={token}"
    prompt = (
        f"请从行程中提取地名（城市、景点）。要求：1.只输出纯地名，空格分隔。2.严禁输出数字、日期、括号、动作词（如前往、住）。"
        f"3.必须包含文末的景点如陶阳里、滕王阁和返程城市。原文：{text}"
    )
    payload = json.dumps({"messages": [{"role": "user", "content": prompt}]})
    
    try:
        with st.spinner('AI 正在深度解析行程...'):
            res = requests.post(url, data=payload, headers={'Content-Type': 'application/json'}, timeout=15).json()
            if "result" in res:
                result = res["result"].strip()
                # 过滤掉非中文字符
                clean = re.sub(r'[^\u4e00-\u9fa5\s]', ' ', result)
                st.session_state['sites_final'] = " ".join(clean.split())
            else:
                st.error(f"AI 响应异常：{res.get('error_msg', '未知错误')}")
    except Exception as e:
        st.error(f"连接超时或失败：{str(e)}")

def rule_extract_v3(text):
    """【规则暴力清洗】不靠AI，靠硬规则删掉杂质"""
    if not text: return ""
    # 删掉所有括号内容、数字、非中文字符
    clean = re.sub(r'\(.*?\)|（.*?）|\d+\.?\d*|[^\u4e00-\u9fa5\s]', ' ', text)
    # 强制拆分补丁
    specials = {"陶阳里滕王阁": "陶阳里 滕王阁", "南昌返程": "南昌", "送南昌": "南昌"}
    for k, v in specials.items():
        clean = clean.replace(k, v)
    # 过滤废话词
    for word in ['接', '前往', '住', '下午', '简易行程', '约']:
        clean = clean.replace(word, ' ')
    st.session_state['sites_final'] = " ".join(clean.split())

# ==================== 3. 界面布局 ====================
with st.sidebar:
    st.header("📊 报价核算中心")
    st.subheader("⚙️ 计费标准")
    col_a, col_b = st.columns(2)
    b39, p39 = col_a.number_input("39起步", 800), col_b.number_input("39单价", 2.6)
    b56, p56 = col_a.number_input("56起步", 1000), col_b.number_input("56单价", 3.6)
    
    st.divider()
    f_km = st.number_input("实测公里 (KM)", value=st.session_state['km_auto'])
    f_days = st.number_input("用车天数", value=4)
    
    res_39 = int(f_km * p39 + f_days * b39)
    res_56 = int(f_km * p56 + f_days * b56)
    
    st.success(f"39座：{res_39} 元 | 56座：{res_56} 元")
    st.text_area("复制报价：", f"里程：{f_km}KM\n39座：{res_39}元\n56座：{res_56}元")

# 主页面
st.header("🚌 九江祥隆旅游运输报价系统")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.markdown("### 1️⃣ 文字识别与提取")
    up_file = st.file_uploader("上传行程截图", type=["jpg", "png"])
    # 假设 OCR 已经识别出文字存入 ocr_raw
    if 'ocr_raw' not in st.session_state: st.session_state['ocr_raw'] = ""
    
    raw_txt = st.text_area("文本核对：", value=st.session_state['ocr_raw'], height=150)
    
    c1, c2 = st.columns(2)
    if c1.button("✨ 智能 AI 提取", use_container_width=True):
        ai_extract_v3(raw_txt)
    if c2.button("🤖 自动规则提取", use_container_width=True):
        rule_extract_v3(raw_txt)

with m_right:
    st.markdown("### 2️⃣ 站点确认")
    site_input = st.text_input("提取出的地名：", value=st.session_state['sites_final'])
    
    confirmed_locs = []
    if site_input:
        names = site_input.split()
        for i, name in enumerate(names):
            url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
            try:
                tips = requests.get(url, timeout=5).json().get('tips', [])
                valid = [t for t in tips if t.get('location')]
                if valid:
                    sel = st.selectbox(f"确认第{i+1}站: {name}", [f"{t['name']} ({t.get('district','')})" for t in valid], key=f"v4_{i}")
                    confirmed_locs.append(next(t['location'] for t in valid if sel.startswith(t['name'])))
            except: pass

    # 自动测距
    if len(confirmed_locs) >= 2:
        org, des, way = confirmed_locs[0], confirmed_locs[-1], ";".join(confirmed_locs[1:-1])
        r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way}"
        try:
            res = requests.get(r_url, timeout=5).json()
            if res['status'] == '1':
                km = int(round(int(res['route']['paths'][0]['distance']) / 1000))
                if km != st.session_state['km_auto']:
                    st.session_state['km_auto'] = km
                    st.rerun()
        except: pass
