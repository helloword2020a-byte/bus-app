import streamlit as st
import pandas as pd
import requests
import re
import base64
import json

# ==================== 1. 核心密钥配置 ====================

# [已填入] 您提供的 V2 版本完整凭证，支持 Bearer 认证
AI_API_KEY_V2 = "bce-v3/ALTAK-EMZixkEbLJ0iEkFcaJCFc/74514893890101d198dd642b3b95ea68bed95897"

# 百度 OCR 密钥
BAIDU_OCR_AK = "1vBiCqNtSYFRx6GYsGwpwXdM"         
BAIDU_OCR_SK = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  

# 高德地图密钥
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统-旗舰版", layout="wide")

# 初始化 Session 状态
if 'ocr_raw' not in st.session_state: st.session_state['ocr_raw'] = ""
if 'sites_final' not in st.session_state: st.session_state['sites_final'] = ""
if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

# ==================== 2. 功能引擎 ====================

def get_ocr_token():
    """获取 OCR 专用的 Access Token"""
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={BAIDU_OCR_AK}&client_secret={BAIDU_OCR_SK}"
    try: return requests.get(url, timeout=10).json().get("access_token")
    except: return None

def ocr_engine(file_bytes):
    """高精度 OCR 引擎"""
    token = get_ocr_token()
    if not token: return "OCR 授权失败"
    img64 = base64.b64encode(file_bytes).decode()
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic?access_token={token}"
    try:
        res = requests.post(url, data={"image": img64}, timeout=15).json()
        words = [item['words'] for item in res.get('words_result', [])]
        return "\n".join(words)
    except: return "识别异常或超时"

def ai_extract_logic_v3(text):
    """【修复版】智能 AI 提取：采用 bce-v3 鉴权逻辑"""
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-128k"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY_V2}"
    }
    prompt = (
        f"你是一个专业的旅游行程调度专家。请从以下文本中提取所有的目的地地名或城市。\n"
        f"要求：1.只输出地名，用空格分隔。2.不要数字、标点和动词（如前往、住）。\n"
        f"3.必须包含文末提及的景点和返程城市。原文：{text}"
    )
    payload = {"messages": [{"role": "user", "content": prompt}]}
    try:
        with st.spinner('AI 正在深度解析地名...'):
            res = requests.post(url, headers=headers, json=payload, timeout=15).json()
            if "result" in res:
                # 过滤非中文字符，保持地名纯净
                clean = re.sub(r'[^\u4e00-\u9fa5\s]', ' ', res["result"])
                st.session_state['sites_final'] = " ".join(clean.split())
            else:
                st.error(f"AI 响应错误: {res.get('error_msg', '未知错误')}")
    except: st.error("AI 连接超时，请检查网络")

def rule_extract_logic_v3(text):
    """【强化版】自动规则提取：您反馈最准的正则逻辑"""
    if not text: return
    # 1. 强力剔除括号内容 (如车程3h) 和 数字日期
    clean = re.sub(r'\(.*?\)|（.*?）|\d+\.?\d*|[^\u4e00-\u9fa5\s]', ' ', text)
    # 2. 冗余词过滤
    for word in ['接', '前往', '住', '下午', '简易行程', '车程', '约', '返程', '送']:
        clean = clean.replace(word, ' ')
    # 3. 核心地名强制拆分补丁
    clean = clean.replace("陶阳里滕王阁", "陶阳里 滕王阁")
    st.session_state['sites_final'] = " ".join(clean.split())

# ==================== 3. 界面布局 ====================

with st.sidebar:
    st.header("📊 报价核算中心")
    st.subheader("⚙️ 计费标准设置")
    col_a, col_b = st.columns(2)
    b39 = col_a.number_input("39座起步", 800)
    p39 = col_b.number_input("39座单价", 2.6)
    b56 = col_a.number_input("56座起步", 1000)
    p56 = col_b.number_input("56座单价", 3.6)
    
    st.divider()
    f_km = st.number_input("实测总公里 (KM)", value=st.session_state['km_auto'])
    f_days = st.number_input("用车总天数", value=4)
    
    res_39 = int(f_km * p39 + f_days * b39)
    res_56 = int(f_km * p56 + f_days * b56)
    
    st.success(f"39座总价：{res_39} 元")
    st.info(f"56座总价：{res_56} 元")
    
    st.divider()
    quote_text = (
        f"【九江祥隆报价单】\n"
        f"里程：{f_km} KM | 天数：{f_days} 天\n"
        f"--------------------\n"
        f"🚌 39座大巴全包价：{res_39} 元\n"
        f"🚌 56座大巴全包价：{res_56} 元"
    )
    st.text_area("直接复制发给客户：", value=quote_text, height=150)

st.title("🚌 九江祥隆旅游运输报价系统")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.subheader("1️⃣ 行程识别与站点提取")
    up_file = st.file_uploader("上传行程截图", type=["jpg", "png", "jpeg"])
    
    if st.button("🚀 开始文字识别 (OCR)", use_container_width=True):
        if up_file:
            with st.spinner('正在识别文字...'):
                st.session_state['ocr_raw'] = ocr_engine(up_file.read())
        else: st.error("请先上传图片")

    raw_txt = st.text_area("识别结果核对：", value=st.session_state['ocr_raw'], height=180)
    
    st.markdown("---")
    c_ai, c_rule = st.columns(2)
    if c_ai.button("✨ 智能 AI 提取", use_container_width=True):
        ai_extract_logic_v3(raw_txt)
    if c_rule.button("🤖 自动规则提取", use_container_width=True):
        rule_extract_logic_v3(raw_txt)

with m_right:
    st.subheader("2️⃣ 站点确认与地图测距")
    site_input = st.text_input("待匹配关键词 (空格隔开)：", value=st.session_state['sites_final'])
    
    confirmed_locs = []
    if site_input:
        names = site_input.replace(",", " ").replace("，", " ").split()
        for i, name in enumerate(names):
            if not name.strip(): continue
            t_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
            try:
                tips = requests.get(t_url, timeout=5).json().get('tips', [])
                valid = [t for t in tips if isinstance(t.get('location'), str)]
                if valid:
                    sel = st.selectbox(f"确认第 {i+1} 站: {name}", 
                                      [f"{t['name']} ({t.get('district','')})" for t in valid], key=f"v5_{i}")
                    confirmed_locs.append(next(t['location'] for t in valid if sel.startswith(t['name'])))
            except: pass

    if st.button("🗺️ 计算总公里数", use_container_width=True):
        if len(confirmed_locs) >= 2:
            org, des, way = confirmed_locs[0], confirmed_locs[-1], ";".join(confirmed_locs[1:-1])
            d_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&waypoints={way}&key={AMAP_KEY}"
            try:
                res = requests.get(d_url).json()
                if res['status'] == '1':
                    dist = int(res['route']['paths'][0]['distance']) / 1000
                    st.session_state['km_auto'] = int(dist)
                    st.success(f"🚩 测距成功！总里程：{int(dist)} KM")
                    st.rerun()
            except: st.error("高德地图测距失败，请检查站点是否准确")
