import streamlit as st
import pandas as pd
import requests
import base64
import json

# ==================== 1. 核心密钥配置 ====================

# [重要] 填入你刚才激活成功的那串长长的 Key
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
    """使用 ERNIE-Speed-Pro-128K 提取纯地名"""
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-pro-128k"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY_V2}"
    }
    prompt = f"你是一个专业的旅游调度。请从以下文字中提取目的地地名（如城市、景点），地名间用空格隔开。只需输出地名。原文：{text}"
    payload = {"messages": [{"role": "user", "content": prompt}]}
    try:
        response = requests.post(url, headers=headers, json=payload)
        res = response.json()
        if "error_code" in res:
            return f"AI 错误({res['error_code']}): {res.get('error_msg')}"
        return res.get("result", "").strip()
    except: return "AI 连接失败"

# ==================== 3. 侧边栏：实时计费单 ====================

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
    # 这里会自动获取右侧地图计算出的里程
    f_km = st.number_input("实测总公里 (KM)", value=st.session_state['km_auto'])
    f_days = st.number_input("用车总天数 (天)", value=4)
    
    res_39 = int(f_km * p39 + f_days * b39)
    res_56 = int(f_km * p56 + f_days * b56)
    
    st.markdown("### 💰 实时总报单")
    st.success(f"**39座大巴：{res_39} 元**")
    st.info(f"**56座大巴：{res_56} 元**")

# ==================== 4. 主页面：AI 与 地图联动 ====================

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
    
    raw_txt = st.text_area("识别文本校对：", value=st.session_state.get('ocr_raw', ""), height=120)
    
    if st.button("✨ 大模型智能提取路径", use_container_width=True):
        if raw_txt:
            with st.spinner('AI 正在分析地名...'):
                extracted = ai_extract_locations_v2(raw_txt)
                st.session_state['sites_final'] = extracted
        else:
            st.warning("请先上传截图")

with m_right:
    st.markdown("### 2️⃣ 站点确认与地图测距")
    site_input = st.text_input("待匹配关键词（空格隔开）：", value=st.session_state.get('sites_final', ""))
    
    confirmed_locs = []
    if site_input:
        # 去掉 AI 可能生成的标点符号
        clean_input = site_input.replace(",", " ").replace("，", " ")
        names = clean_input.split()
        
        # 每一站展示一个下拉选择框
        for i, name in enumerate(names):
            if not name.strip(): continue
            # 搜索高德地图建议
            url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
            try:
                tips = requests.get(url).json().get('tips', [])
                valid_tips = [t for t in tips if t.get('location')]
                if valid_tips:
                    # 让用户在匹配到的多个地点中选一个最准确的
                    sel = st.selectbox(f"确认第 {i+1} 站: {name}", 
                                      [f"{t['name']} ({t.get('district','')})" for t in valid_tips], 
                                      key=f"site_sel_{i}")
                    # 提取选定地点的经纬度
                    selected_name = sel.split(" (")[0]
                    coord = next(t['location'] for t in valid_tips if t['name'] == selected_name)
                    confirmed_locs.append(coord)
            except: pass

    # 如果至少有两个点（起点和终点），就开始算距离
    if len(confirmed_locs) >= 2:
        st.divider()
        org = confirmed_locs[0]
        des = confirmed_locs[-1]
        # 中间站（如果有的话）
        way = ";".join(confirmed_locs[1:-1])
        
        r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way if way else ''}"
        
        try:
            res = requests.get(r_url).json()
            if res['status'] == '1' and res['route']['paths']:
                # 将米转换成公里
                distance_m = int(res['route']['paths'][0]['distance'])
                km_val = int(round(distance_m / 1000))
                
                # 存入 session_state 触发左侧报价单更新
                st.session_state['km_auto'] = km_val
                st.success(f"🚩 路线规划成功！实测公里数：{km_val} KM")
                
                if st.button("✅ 同步里程并更新报价"):
                    st.rerun()
            else:
                st.error("高德地图无法计算此路径")
        except:
            st.error("地图连接失败")
