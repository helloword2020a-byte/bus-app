import streamlit as st
import pandas as pd
import requests
import re
import base64
import json

# ==================== 1. 核心密钥配置 ====================

# [已填入] 您提供的 V2 版本完整凭证
AI_API_KEY_V2 = "bce-v3/ALTAK-EMZixkEbLJ0iEkFcaJCFc/74514893890101d198dd642b3b95ea68bed95897"

# 百度 OCR 密钥 (保持不变)
BAIDU_OCR_AK = "1vBiCqNtSYFRx6GYsGwpwXdM"         
BAIDU_OCR_SK = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  

# 高德地图密钥 (保持不变)
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统-旗舰版", layout="wide")

# ==================== 2. 功能引擎 ====================

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
    """【专用优化】适配 bce-v3 长凭证认证逻辑"""
    # 注意：这里使用的是 ernie-speed-128k 的标准接口
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-128k"
    
    # 核心修复：针对 bce-v3 凭证，必须在 Header 中严格按照以下格式
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY_V2}"
    }
    
    prompt = (
        f"你是一个专业的旅游行程调度专家。请从以下文本中提取所有的目的地【地名】或【城市】。\n"
        f"要求：只输出地名，地名之间用空格分隔。不要输出数字、符号、动作词（如接送、住）。\n"
        f"必须包含行程结尾的景点（如陶阳里、滕王阁、南昌）。原文：{text}"
    )
    
    payload = {"messages": [{"role": "user", "content": prompt}]}
    
    try:
        # 增加超时限制，防止点击没反应
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        res = response.json()
        
        if "result" in res:
            raw_result = res.get("result", "").strip()
            # 强力二次去噪
            clean_text = re.sub(r'[^\u4e00-\u9fa5\s]', ' ', raw_result)
            return " ".join(clean_text.split())
        else:
            # 如果报错，返回具体的百度错误信息
            return f"AI 错误: {res.get('error_msg', '未知响应格式')}"
    except Exception as e:
        return f"AI 连接超时或异常: {str(e)}"

def rule_extract_locations(text):
    """保持您满意的自动规则提取逻辑"""
    if not text: return ""
    # 1. 剔除括号内容 (车程3h) 和 数字日期 (4.11)
    clean_text = re.sub(r'\(.*?\)|（.*?）|\d+\.?\d*', ' ', text)
    # 2. 精准过滤非地名词汇
    for word in ['接', '送', '前往', '返程', '车程', '约', 'h', '住', '下午', '简易行程']:
        clean_text = clean_text.replace(word, ' ')
    # 3. 补丁：拆解连写的核心地名
    clean_text = clean_text.replace("陶阳里滕王阁", "陶阳里 滕王阁")
    return " ".join(clean_text.split()).strip()

# ==================== 3. 侧边栏与主界面 (逻辑已精简) ====================

if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

with st.sidebar:
    st.header("📊 报价核算中心")
    st.subheader("⚙️ 计费标准设置")
    col_a, col_b = st.columns(2)
    b39, p39 = col_a.number_input("39起步费", 800), col_b.number_input("39单价", 2.6)
    b56, p56 = col_a.number_input("56起步费", 1000), col_b.number_input("56单价", 3.6)
    
    st.divider()
    f_km = st.number_input("实测总公里 (KM)", value=st.session_state['km_auto'])
    f_days = st.number_input("用车总天数", value=4)
    
    res_39, res_56 = int(f_km * p39 + f_days * b39), int(f_km * p56 + f_days * b56)
    st.success(f"39座：{res_39} 元 | 56座：{res_56} 元")
    
    st.divider()
    quote_text = f"【九江祥隆报价单】\n里程：{f_km}KM | 天数：{f_days}天\n---\n39座大巴：{res_39}元\n56座大巴：{res_56}元"
    st.text_area("复制文案：", value=quote_text, height=150)

st.header("🚌 九江祥隆旅游运输报价系统 (AI 旗舰版)")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.markdown("### 1️⃣ 文字识别与提取")
    up_file = st.file_uploader("上传截图", type=["jpg", "png", "jpeg"])
    if up_file:
        if st.button("🚀 开始文字提取识别", use_container_width=True):
            with st.spinner('提取中...'):
                st.session_state['ocr_raw'] = ocr_engine(up_file.read())
    
    raw_txt = st.text_area("文本核对框：", value=st.session_state.get('ocr_raw', ""), height=150)
    
    col1, col2 = st.columns(2)
    if col1.button("✨ 智能 AI 提取", use_container_width=True):
        st.session_state['sites_final'] = ai_extract_locations_v2(raw_txt)
    if col2.button("🤖 自动规则提取", use_container_width=True):
        st.session_state['sites_final'] = rule_extract_locations(raw_txt)

with m_right:
    st.markdown("### 2️⃣ 站点确认与地图测距")
    site_input = st.text_input("提取站点：", value=st.session_state.get('sites_final', ""))
    
    confirmed_locs = []
    if site_input:
        names = site_input.replace(",", " ").replace("，", " ").split()
        for i, name in enumerate(names):
            if not name.strip(): continue
            url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
            try:
                tips = requests.get(url).json().get('tips', [])
                valid = [t for t in tips if t.get('location')]
                if valid:
                    sel = st.selectbox(f"确认第 {i+1} 站: {name}", [f"{t['name']} ({t.get('district','')})" for t in valid], key=f"site_{i}")
                    confirmed_locs.append(next(t['location'] for t in valid if sel.startswith(t['name'])))
            except: pass

    if len(confirmed_locs) >= 2:
        org, des, way = confirmed_locs[0], confirmed_locs[-1], ";".join(confirmed_locs[1:-1])
        r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way if way else ''}"
        try:
            res = requests.get(r_url).json()
            if res['status'] == '1' and res['route']['paths']:
                km = int(round(int(res['route']['paths'][0]['distance']) / 1000))
                st.session_state['km_auto'] = km
                st.success(f"🚩 规划成功！公里数：{km} KM")
        except: st.error("地图测距异常")
