import streamlit as st
import pandas as pd
import requests
import base64
import json
import re

# ==================== 1. 核心密钥配置 ====================

# [核对] 请确保此 Key 与你百度后台 [V2版本] 的 API Key 一致
AI_API_KEY_V2 = "bce-v3/ALTAK-EMZixkEbLJ0iEkFcaJCFc/74514893890101d198dd642b3b95ea68bed95897"

# 百度 OCR 密钥
BAIDU_OCR_AK = "1vBiCqNtSYFRx6GYsGwpwXdM"         
BAIDU_OCR_SK = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  

# 高德地图密钥
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
    """强化版：地毯式搜索行程中所有地名，重点捕获文末景点"""
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-pro-128k"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY_V2}"
    }
    
    # 终极版 Prompt：明确要求拆分连字地名，不准漏掉结尾
    prompt = (
        f"你是一个专业的旅游行程分析专家。请从以下文本中提取【所有】涉及的地名、城市或景点名称。\n"
        f"特别注意：不要漏掉文末提到的‘返程点’或‘途径景点’（如：陶阳里、滕王阁、南昌）。\n"
        f"要求：\n"
        f"1. 只输出地名，地名之间用【空格】分隔。\n"
        f"2. 严禁输出数字序号、标点符号或‘目的地：’等废话。\n"
        f"3. 若景点连在一起（如：陶阳里滕王阁），请务必拆分为‘陶阳里 滕王阁’。\n"
        f"原文：{text}"
    )
    
    payload = {"messages": [{"role": "user", "content": prompt}]}
    try:
        response = requests.post(url, headers=headers, json=payload)
        res = response.json()
        if "error_code" in res:
            return f"AI 错误({res['error_code']}): {res.get('error_msg')}"
        
        raw_result = res.get("result", "").strip()
        
        # 二次强力清洗：删掉数字和干扰动词
        clean_text = re.sub(r'\d+', ' ', raw_result)
        for junk in ["目的地", "地名", "地点", "：", ":", ".", "、", "住", "前往", "返程", "车程"]:
            clean_text = clean_text.replace(junk, " ")
            
        return " ".join(clean_text.split()) # 确保空格干净
    except: return "AI 连接失败"

# ==================== 3. 侧边栏：实时报价计费 ====================

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
    # 接收地图测距结果
    f_km = st.number_input("实测总公里 (KM)", value=st.session_state['km_auto'])
    f_days = st.number_input("用车总天数 (天)", value=4)
    
    res_39 = int(f_km * p39 + f_days * b39)
    res_56 = int(f_km * p56 + f_days * b56)
    
    st.markdown("### 💰 实时总报单")
    st.success(f"**39座大巴总价：{res_39} 元**")
    st.info(f"**56座大巴总价：{res_56} 元**")

# ==================== 4. 主页面：流程操作 ====================

st.header("🚌 九江祥隆旅游运输报价系统 (AI 旗舰版)")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.markdown("### 1️⃣ 行程 AI 智能识别")
    up_file = st.file_uploader("上传行程截图", type=["jpg", "png", "jpeg"])
    if up_file:
        img_bytes = up_file.read()
        st.image(img_bytes, width=300)
        if st.button("🚀 开始高精度识别", use_container_width=True):
            with st.spinner('提取文字中...'):
                st.session_state['ocr_raw'] = ocr_engine(img_bytes)
    
    raw_txt = st.text_area("识别文本校对：", value=st.session_state.get('ocr_raw', ""), height=150)
    
    if st.button("✨ 大模型智能解析路径", use_container_width=True):
        if raw_txt:
            with st.spinner('AI 正在捕获所有景点...'):
                st.session_state['sites_final'] = ai_extract_locations_v2(raw_txt)
        else:
            st.warning("请先通过图片识别或手动输入文字")

with m_right:
    st.markdown("### 2️⃣ 站点确认与地图测距")
    site_input = st.text_input("待匹配关键词（空格分隔）：", value=st.session_state.get('sites_final', ""))
    
    confirmed_locs = []
    if site_input:
        names = site_input.split()
        for i, name in enumerate(names):
            if not name.strip(): continue
            # 调用高德 API 搜索地点建议
            url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
            try:
                tips = requests.get(url).json().get('tips', [])
                valid_tips = [t for t in tips if t.get('location')]
                if valid_tips:
                    # 每一站让用户确认具体经纬度点
                    sel = st.selectbox(f"确认第 {i+1} 站: {name}", 
                                      [f"{t['name']} ({t.get('district','')})" for t in valid_tips], 
                                      key=f"st_sel_{i}")
                    s_name = sel.split(" (")[0]
                    coord = next(t['location'] for t in valid_tips if t['name'] == s_name)
                    confirmed_locs.append(coord)
            except: pass

    # 路径测距逻辑
    if len(confirmed_locs) >= 2:
        st.divider()
        org, des = confirmed_locs[0], confirmed_locs[-1]
        way = ";".join(confirmed_locs[1:-1])
        r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way if way else ''}"
        
        try:
            res = requests.get(r_url).json()
            if res['status'] == '1' and res['route']['paths']:
                dist_m = int(res['route']['paths'][0]['distance'])
                km = int(round(dist_m / 1000))
                st.session_state['km_auto'] = km
                st.success(f"🚩 路径规划成功！总公里数：{km} KM")
                if st.button("✅ 更新至报价单"): st.rerun()
            else:
                st.error("测距失败，请检查站点是否选择准确")
        except: st.error("地图接口连接异常")
