import streamlit as st
import pandas as pd
import requests
import base64
import json
import re

# ==================== 1. 核心密钥配置 ====================

AI_API_KEY_V2 = "bce-v3/ALTAK-EMZixkEbLJ0iEkFcaJCFc/74514893890101d198dd642b3b95ea68bed95897"
BAIDU_OCR_AK = "1vBiCqNtSYFRx6GYsGwpwXdM"         
BAIDU_OCR_SK = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆旅游运输报价系统", layout="wide")

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
        res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-form-urlencoded'}).json()
        return "".join([i['words'] for i in res.get('words_result', [])])
    except: return "识别异常"

def ai_extract_locations_v2(text):
    """强化版：强制识别所有地点，包括末尾的返程点"""
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-pro-128k"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {AI_API_KEY_V2}"}
    
    prompt = (
        f"你是一个旅游行程专家。请提取以下文本中提到的所有【地名】或【城市名】。\n"
        f"特别指令：\n"
        f"1. 严禁漏掉结尾处的城市名（如：南昌）。\n"
        f"2. 即使原文是'返程'、'回南昌'，也请提取出'南昌'两个字。\n"
        f"3. 必须拆分连字符或紧凑地名（如：陶阳里滕王阁 -> 陶阳里 滕王阁）。\n"
        f"4. 只输出纯地名，空格分隔，不输出任何其他字。\n"
        f"原文：{text}"
    )
    
    payload = {"messages": [{"role": "user", "content": prompt}]}
    try:
        response = requests.post(url, headers=headers, json=payload)
        res = response.json()
        raw_result = res.get("result", "").strip()
        # 二次清洗
        clean_text = re.sub(r'\d+', ' ', raw_result)
        for junk in ["目的地", "地名", "：", ":", ".", "、", "住", "前往", "回", "返程"]:
            clean_text = clean_text.replace(junk, " ")
        return " ".join(clean_text.split())
    except: return "AI 解析失败"

# ==================== 3. 侧边栏：实时报价核算 ====================

if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

with st.sidebar:
    st.header("📊 报价核算中心")
    
    # --- 需求修改 1：计费标准不再折叠 ---
    st.subheader("⚙️ 计费标准设置")
    col_a, col_b = st.columns(2)
    b39 = col_a.number_input("39座起步费", value=800)
    p39 = col_b.number_input("39座单价", value=2.6)
    b56 = col_a.number_input("56座起步费", value=1000)
    p56 = col_b.number_input("56座单价", value=3.6)

    st.divider()
    f_km = st.number_input("实测总公里 (KM)", value=st.session_state['km_auto'])
    f_days = st.number_input("用车总天数 (天)", value=4)
    
    res_39 = int(f_km * p39 + f_days * b39)
    res_56 = int(f_km * p56 + f_days * b56)
    
    st.markdown("### 💰 实时总报单")
    st.success(f"**39座大巴总价：{res_39} 元**")
    st.info(f"**56座大巴总价：{res_56} 元**")

    # --- 需求修改 2：增加可复制的文本区域 ---
    st.divider()
    st.markdown("📝 **报价结果（直接复制发送）**")
    quote_text = (
        f"【九江祥隆旅游运输报价单】\n"
        f"总里程：{f_km} KM\n"
        f"用车天数：{f_days} 天\n"
        f"--------------------\n"
        f"🚌 39座大巴：{res_39} 元\n"
        f"🚌 56座大巴：{res_56} 元\n"
        f"注：以上价格包含车辆燃油费、路桥费、司机工资。"
    )
    st.text_area("复制下方文字：", value=quote_text, height=180)

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
            with st.spinner('AI 正在捕获所有站点...'):
                st.session_state['sites_final'] = ai_extract_locations_v2(raw_txt)
        else:
            st.warning("请上传截图或输入文字")

with m_right:
    st.markdown("### 2️⃣ 站点确认与地图测距")
    site_input = st.text_input("待匹配关键词（空格分隔）：", value=st.session_state.get('sites_final', ""))
    
    confirmed_locs = []
    if site_input:
        names = site_input.split()
        for i, name in enumerate(names):
            if not name.strip(): continue
            url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
            try:
                tips = requests.get(url).json().get('tips', [])
                valid_tips = [t for t in tips if t.get('location')]
                if valid_tips:
                    sel = st.selectbox(f"确认第 {i+1} 站: {name}", 
                                      [f"{t['name']} ({t.get('district','')})" for t in valid_tips], 
                                      key=f"st_sel_v3_{i}")
                    s_name = sel.split(" (")[0]
                    coord = next(t['location'] for t in valid_tips if t['name'] == s_name)
                    confirmed_locs.append(coord)
            except: pass

    if len(confirmed_locs) >= 2:
        st.divider()
        org, des = confirmed_locs[0], confirmed_locs[-1]
        way = ";".join(confirmed_locs[1:-1])
        r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way if way else ''}"
        
        try:
            res = requests.get(r_url).json()
            if res['status'] == '1' and res['route']['paths']:
                km = int(round(int(res['route']['paths'][0]['distance']) / 1000))
                st.session_state['km_auto'] = km
                st.success(f"🚩 规划成功！总里程：{km} KM")
                if st.button("✅ 同步至报价单"): st.rerun()
            else: st.error("地图测距失败，请检查站点是否选择准确")
        except: st.error("地图服务异常")
