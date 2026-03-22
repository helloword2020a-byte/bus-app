import streamlit as st
import pandas as pd
import requests
import re
import base64
import json

# ==================== 1. 核心密钥配置 (请在此填入您的真实 Key) ====================
# 请对照您的百度千帆后台截图 填入以下两行
AI_API_KEY = "您的API_Key"
AI_SECRET_KEY = "您的Secret_Key"

# OCR 和 高德地图密钥保持不变
BAIDU_OCR_AK = "1vBiCqNtSYFRx6GYsGwpwXdM"
BAIDU_OCR_SK = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆旅游运输报价系统", layout="wide")

# 初始化状态
if 'ocr_raw' not in st.session_state: st.session_state['ocr_raw'] = ""
if 'sites_final' not in st.session_state: st.session_state['sites_final'] = ""
if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

# ==================== 2. 功能函数库 ====================

def get_baidu_token(ak, sk):
    """通用 Token 获取函数"""
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={ak}&client_secret={sk}"
    try:
        res = requests.get(url, timeout=10).json()
        return res.get("access_token")
    except: return None

def do_ocr(image_file):
    """百度高精度 OCR 识别"""
    token = get_baidu_token(BAIDU_OCR_AK, BAIDU_OCR_SK)
    if not token: return "OCR 授权失败"
    
    img_str = base64.b64encode(image_file.read()).decode()
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic?access_token={token}"
    try:
        res = requests.post(url, data={"image": img_str}, timeout=15).json()
        words = [item['words'] for item in res.get('words_result', [])]
        return "\n".join(words)
    except: return "识别请求超时"

def ai_extract_logic(text):
    """AI 智能地名提取"""
    token = get_baidu_token(AI_API_KEY, AI_SECRET_KEY)
    if not token:
        st.error("AI 授权失败，请检查 API Key 和 Secret Key")
        return
    
    url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-128k?access_token={token}"
    prompt = f"从行程中提取地名，只要地名，空格分隔，不要数字、括号和前往/住等动词。原文：{text}"
    payload = json.dumps({"messages": [{"role": "user", "content": prompt}]})
    
    try:
        with st.spinner('AI 正在思考...'):
            res = requests.post(url, data=payload, headers={'Content-Type': 'application/json'}, timeout=15).json()
            if "result" in res:
                clean = re.sub(r'[^\u4e00-\u9fa5\s]', ' ', res["result"])
                st.session_state['sites_final'] = " ".join(clean.split())
            else:
                st.error(f"AI 响应错误: {res.get('error_msg')}")
    except: st.error("AI 连接超时")

def rule_extract_logic(text):
    """自动规则提取 (您反馈较准的方案)"""
    if not text: return
    # 过滤括号、数字、符号
    clean = re.sub(r'\(.*?\)|（.*?）|\d+\.?\d*|[^\u4e00-\u9fa5\s]', ' ', text)
    # 常见冗余词过滤
    for word in ['接', '前往', '住', '下午', '简易行程', '车程', '约', '返程']:
        clean = clean.replace(word, ' ')
    # 强制拆词补丁
    clean = clean.replace("陶阳里滕王阁", "陶阳里 滕王阁")
    st.session_state['sites_final'] = " ".join(clean.split())

# ==================== 3. 界面布局 ====================

with st.sidebar:
    st.header("📊 报价核算中心")
    with st.expander("⚙️ 计费标准设置", expanded=False):
        col_a, col_b = st.columns(2)
        b39 = col_a.number_input("39座起步", 800)
        p39 = col_b.number_input("39座单价", 2.6)
        b56 = col_a.number_input("56座起步", 1000)
        p56 = col_b.number_input("56座单价", 3.6)
    
    st.divider()
    f_km = st.number_input("实测总公里 (KM)", value=st.session_state['km_auto'])
    f_days = st.number_input("用车总天数 (天)", value=4)
    
    res_39 = int(f_km * p39 + f_days * b39)
    res_56 = int(f_km * p56 + f_days * b56)
    
    st.success(f"39座大巴总价：{res_39} 元")
    st.info(f"56座大巴总价：{res_56} 元")
    
    st.download_button("导出报价单", f"里程：{f_km}KM\n天数：{f_days}\n39座：{res_39}元\n56座：{res_56}元", "报价.txt")

# 主界面
st.title("🚌 九江祥隆旅游运输报价系统 (AI 旗舰版)")

m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.subheader("1️⃣ 行程识别与站点提取")
    up_file = st.file_uploader("上传行程截图", type=["jpg", "png"])
    
    if st.button("🚀 开始文字识别 (OCR)", use_container_width=True):
        if up_file:
            with st.spinner('正在识别文字...'):
                st.session_state['ocr_raw'] = do_ocr(up_file)
        else: st.error("请先上传图片")

    raw_txt = st.text_area("识别结果校对：", value=st.session_state['ocr_raw'], height=200)
    
    st.markdown("---")
    c_ai, c_rule = st.columns(2)
    if c_ai.button("✨ 智能 AI 提取", use_container_width=True):
        ai_extract_logic(raw_txt)
    if c_rule.button("🤖 自动规则提取", use_container_width=True):
        rule_extract_logic(raw_txt)

with m_right:
    st.subheader("2️⃣ 站点确认与地图测距")
    site_input = st.text_input("待匹配关键词 (空格隔开)：", value=st.session_state['sites_final'])
    
    confirmed_locs = []
    if site_input:
        names = site_input.split()
        for i, name in enumerate(names):
            # 高德搜索建议
            t_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
            try:
                tips = requests.get(t_url, timeout=5).json().get('tips', [])
                valid = [t for t in tips if isinstance(t.get('location'), str)]
                if valid:
                    sel = st.selectbox(f"确认第 {i+1} 站: {name}", 
                                      [f"{t['name']} ({t.get('district','')})" for t in valid], key=f"loc_{i}")
                    # 获取坐标
                    confirmed_locs.append(next(t['location'] for t in valid if sel.startswith(t['name'])))
            except: pass

    if st.button("🗺️ 计算总公里数", use_container_width=True):
        if len(confirmed_locs) >= 2:
            org, des = confirmed_locs[0], confirmed_locs[-1]
            way = ";".join(confirmed_locs[1:-1])
            d_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&waypoints={way}&key={AMAP_KEY}"
            try:
                res = requests.get(d_url).json()
                if res['status'] == '1':
                    dist = int(res['route']['paths'][0]['distance']) / 1000
                    st.session_state['km_auto'] = int(dist)
                    st.success(f"🚩 规划成功！总里程：{int(dist)} KM")
                    st.rerun()
            except: st.error("地图测距失败")
