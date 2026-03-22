import streamlit as st
import pandas as pd
import requests
import base64
import json

# ==================== 1. 核心密钥配置 (仅需填入 V2 Key) ====================
# 请填入你刚才复制的那串 bce-v3/ALTAK...
AI_API_KEY_V2 = "bce-v3/ALTAK-EMZixkEbLJ0iEkFcaJCFc/74514893890101d198dd642b3b95ea68bed95897"

# 百度 OCR 密钥（保持不变）
BAIDU_OCR_AK = "1vBiCqNtSYFRx6GYsGwpwXdM"         
BAIDU_OCR_SK = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  

# 高德地图密钥（保持不变）
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统-AI旗舰版", layout="wide")

# ==================== 2. 功能引擎 ====================

def get_ocr_token():
    """OCR 专用 Token 获取"""
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={BAIDU_OCR_AK}&client_secret={BAIDU_OCR_SK}"
    try: return requests.get(url).json().get("access_token")
    except: return None

def ocr_engine(file_bytes):
    """高精度 OCR 文字识别"""
    token = get_ocr_token()
    if not token: return "OCR 授权失败"
    img64 = base64.b64encode(file_bytes).decode()
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token={token}"
    try:
        res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
        return "".join([i['words'] for i in res.get('words_result', [])])
    except: return "识别失败"

def ai_extract_locations_v2(text):
    """使用 V2 接口进行智能地名提取"""
    # 百度千帆 V2 接口 URL
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-128k"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY_V2}"
    }
    
    prompt = f"你是一个专业的旅游调度。请从以下行程描述中提取目的地地名，地名之间用空格隔开。只需输出地名，不要多余解释。原文：{text}"
    
    payload = {
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        res = response.json()
        # 针对 V2 接口的返回结构处理
        if "error_code" in res:
            return f"AI 授权失败，错误代码: {res['error_code']} (请确认后台已开通服务)"
        return res.get("result", "").strip()
    except Exception as e:
        return f"AI 连接异常: {str(e)}"

# ==================== 3. 侧边栏：计费逻辑 ====================
if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

with st.sidebar:
    st.header("📊 报价核算中心")
    with st.expander("⚙️ 计费标准设置"):
        b39 = st.number_input("39座起步费", value=800)
        p39 = st.number_input("39座单价", value=2.6)
        b56 = st.number_input("56座起步费", value=1000)
        p56 = st.number_input("56座单价", value=3.6)

    st.divider()
    f_km = st.number_input("实测总公里 (KM)", value=st.session_state['km_auto'])
    f_days = st.number_input("用车总天数 (天)", value=4)
    
    st.markdown("### 💰 实时报价结果")
    st.info(f"39座大巴：{int(f_km * p39 + f_days * b39)} 元")
    st.info(f"56座大巴：{int(f_km * p56 + f_days * b56)} 元")

# ==================== 4. 主页面逻辑 ====================
st.header("🚌 九江祥隆旅游运输报价系统 (AI 旗舰版)")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.markdown("### 1️⃣ 行程 AI 智能识别")
    up_file = st.file_uploader("上传行程截图", type=["jpg", "png", "jpeg"])
    if up_file:
        img_bytes = up_file.read()
        st.image(img_bytes, width=300)
        if st.button("🚀 开始识别文字", use_container_width=True):
            st.session_state['ocr_raw'] = ocr_engine(img_bytes)
    
    raw_txt = st.text_area("文本校对：", value=st.session_state.get('ocr_raw', ""), height=150)
    
    if st.button("✨ 大模型智能解析路径", use_container_width=True):
        if raw_txt:
            st.session_state['sites_final'] = ai_extract_locations_v2(raw_txt)
        else:
            st.warning("请先获取识别文字")

with m_right:
    st.markdown("### 2️⃣ 站点确认与地图测距")
    site_input = st.text_input("待匹配关键词：", value=st.session_state.get('sites_final', ""))
    
    confirmed_locs = []
    if site_input:
        names = site_input.split()
        for i, name in enumerate(names):
            # 高德搜索建议
            url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
            tips = requests.get(url).json().get('tips', [])
            valid_tips = [t for t in tips if t.get('location')]
            if valid_tips:
                sel = st.selectbox(f"确认站点 {i+1}: {name}", [f"{t['name']} ({t.get('district','')})" for t in valid_tips], key=f"s_{i}")
                coord = next(t['location'] for t in valid_tips if sel.startswith(t['name']))
                confirmed_locs.append(coord)

    if len(confirmed_locs) >= 2:
        org, des = confirmed_locs[0], confirmed_locs[-1]
        way = ";".join(confirmed_locs[1:-1])
        r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way if way else ''}"
        res = requests.get(r_url).json()
        if res['status'] == '1':
            km = int(int(res['route']['paths'][0]['distance']) / 1000)
            st.session_state['km_auto'] = km
            st.success(f"📍 路径规划成功！共计 {km} KM")
            if st.button("✅ 将里程应用到报价单"): st.rerun()
