import streamlit as st
import pandas as pd
import requests
import re
import base64

# ==================== 1. 核心密钥配置 ====================
AI_API_KEY_V2 = "bce-v3/ALTAK-EMZixkEbLJ0iEkFcaJCFc/74514893890101d198dd642b3b95ea68bed95897"
BAIDU_OCR_AK = "1vBiCqNtSYFRx6GYsGwpwXdM"         
BAIDU_OCR_SK = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统-旗舰版", layout="wide")

# ==================== 2. 界面样式定制 ====================
st.markdown("""
    <style>
    .scroll-container {
        max-height: 750px;
        overflow-y: auto;
        padding: 10px;
        border: 1px solid #f0f2f6;
        border-radius: 8px;
        background-color: #fafafa;
    }
    .km-display {
        font-size: 24px;
        font-weight: bold;
        color: #ff4b4b;
        text-align: center;
        padding: 10px;
        background-color: #ffebee;
        border-radius: 5px;
        margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# 状态初始化
if 'ocr_raw' not in st.session_state: st.session_state['ocr_raw'] = ""
if 'temp_preview_text' not in st.session_state: st.session_state['temp_preview_text'] = "" 
if 'final_station_list' not in st.session_state: st.session_state['final_station_list'] = [] 
if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

# ==================== 3. 核心功能引擎 ====================
def ocr_engine(file_bytes):
    token = requests.get(f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={BAIDU_OCR_AK}&client_secret={BAIDU_OCR_SK}").json().get("access_token")
    img64 = base64.b64encode(file_bytes).decode()
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token={token}"
    res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
    return "".join([i['words'] for i in res.get('words_result', [])])

def ai_extract(text):
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-128k"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {AI_API_KEY_V2}"}
    prompt = f"提取目的地地名，用逗号分隔。原文：{text}"
    res = requests.post(url, headers=headers, json={"messages": [{"role": "user", "content": prompt}]}).json()
    return res.get("result", "").replace(" ", ",")

# ==================== 4. 布局方案 ====================
col_calc, col_extract, col_confirm = st.columns([0.8, 1, 1.2])

# --- 左侧：报价单 ---
with col_calc:
    st.header("📊 报价核算")
    with st.form("price_form"):
        c1, c2 = st.columns(2)
        b39, p39 = c1.number_input("39起步", 800), c2.number_input("39单价", 2.6)
        b56, p56 = c1.number_input("56起步", 1000), c2.number_input("56单价", 3.6)
        f_km = st.number_input("总公里 (KM)", value=st.session_state['km_auto'])
        f_days = st.number_input("天数", 4)
        st.form_submit_button("💰 更新价格")
    
    res39, res56 = int(f_km*p39 + f_days*b39), int(f_km*p56 + f_days*b56)
    st.success(f"39座: {res39} 元 | 56座: {res56} 元")

# --- 中间：行程提取区 ---
with col_extract:
    st.header("1️⃣ 提取行程")
    up_file = st.file_uploader("上传截图", type=["jpg", "png"])
    if up_file and st.button("识别文字", use_container_width=True):
        st.session_state['ocr_raw'] = ocr_engine(up_file.read())
    
    ocr_edit = st.text_area("OCR原文校对", value=st.session_state['ocr_raw'], height=150)
    
    if st.button("✨ 智能提取地名", use_container_width=True):
        st.session_state['temp_preview_text'] = ai_extract(ocr_edit)
    
    st.write("---")
    # 【预览框】：支持手动修改，支持逗号分隔
    modified_text = st.text_area("🖊️ 提取结果预览(用逗号或空格分隔)", 
                                 value=st.session_state['temp_preview_text'], 
                                 height=100)
    
    # 【唯一权限触发】：点击后强制更新右侧站点列表
    if st.button("🚀 确认并填充至站点", type="primary", use_container_width=True):
        # 同时支持中英文逗号和空格分隔
        sites = re.split(r'[，,\s]+', modified_text)
        st.session_state['final_station_list'] = [s.strip() for s in sites if s.strip()]
        st.rerun() # 必须强制刷新以更新右侧表单

# --- 右侧：站点确认区 ---
with col_confirm:
    st.header("2️⃣ 站点确认")
    st.markdown('<div class="scroll-container">', unsafe_allow_html=True)
    
    current_coords = []
    # 动态生成站点，key中加入列表长度确保唯一性以解决不更新问题
    for i, name in enumerate(st.session_state['final_station_list']):
        with st.container(border=True):
            search_kw = st.text_input(f"站{i+1} 关键词", value=name, key=f"kw_{i}_{len(st.session_state['final_station_list'])}")
            t_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={search_kw}&key={AMAP_KEY}"
            try:
                tips = requests.get(t_url, timeout=5).json().get('tips', [])
                valid = [t for t in tips if t.get('location')]
                if valid:
                    sel = st.selectbox(f"请确认站{i+1}地址", 
                                       options=[f"{t['name']} ({t.get('district','')})" for t in valid], 
                                       key=f"sel_{i}_{len(st.session_state['final_station_list'])}")
                    current_coords.append(next(t['location'] for t in valid if sel.startswith(t['name'])))
            except: pass
            
    st.markdown('</div>', unsafe_allow_html=True)

    # 测距逻辑与结果显示
    if len(current_coords) >= 2:
        st.divider()
        if st.button("🗺️ 开始规划测距", use_container_width=True, type="primary"):
            org, des, way = current_coords[0], current_coords[-1], ";".join(current_coords[1:-1])
            d_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&waypoints={way}&key={AMAP_KEY}"
            res = requests.get(d_url).json()
            if res['status'] == '1':
                st.session_state['km_auto'] = int(int(res['route']['paths'][0]['distance']) / 1000)
                st.rerun()
        
        # 【新增】：测完后的公里数显示
        if st.session_state['km_auto'] > 0:
            st.markdown(f'<div class="km-display">📏 规划完成！总公里数：{st.session_state["km_auto"]} KM</div>', unsafe_allow_html=True)
