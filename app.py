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

# 状态初始化
if 'ocr_raw' not in st.session_state: st.session_state['ocr_raw'] = ""
if 'temp_preview_text' not in st.session_state: st.session_state['temp_preview_text'] = "" 
if 'final_station_list' not in st.session_state: st.session_state['final_station_list'] = [] 
if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

# ==================== 2. 功能引擎 ====================
def ocr_engine(file_bytes):
    try:
        token_res = requests.get(f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={BAIDU_OCR_AK}&client_secret={BAIDU_OCR_SK}").json()
        token = token_res.get("access_token")
        img64 = base64.b64encode(file_bytes).decode()
        url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token={token}"
        res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
        return "".join([i['words'] for i in res.get('words_result', [])])
    except: return "识别失败"

def ai_extract(text):
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-128k"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {AI_API_KEY_V2}"}
    prompt = f"提取行程目的地地名，地名之间用中文逗号分隔。不要输出多余文字。原文：{text}"
    try:
        res = requests.post(url, headers=headers, json={"messages": [{"role": "user", "content": prompt}]}).json()
        return res.get("result", "").replace(" ", "，")
    except: return ""

def rule_extract(text):
    clean = re.sub(r'\(.*?\)|（.*?）|\d+\.?\d*|[^\u4e00-\u9fa5\s,，]', ' ', text or "")
    for word in ['接', '送', '前往', '返程', '车程', '住', '小时', '公里']: 
        clean = clean.replace(word, ' ')
    return "，".join(clean.split())

# 【新增核心逻辑】：监听文本框变化，实时同步站点列表
def sync_stations():
    # 从session_state直接读取当前文本框的值
    text = st.session_state.modified_input
    site_list = re.split(r'[，,\s]+', text)
    # 过滤空字符串并更新列表
    st.session_state['final_station_list'] = [s.strip() for s in site_list if s.strip()]

# ==================== 3. 界面布局 ====================
col_calc, col_extract, col_confirm = st.columns([0.8, 1, 1.2])

# --- 左侧：报价核算 ---
with col_calc:
    st.header("📊 报价核算")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        b39 = c1.number_input("39起步费", 800)
        p39 = c2.number_input("39单价", 2.6)
        b56 = c1.number_input("56起步费", 1000)
        p56 = c2.number_input("56单价", 3.6)
        
        f_km = st.number_input("当前总公里 (KM)", value=st.session_state['km_auto'])
        f_days = st.number_input("用车天数", 4)
        
        res39 = int(f_km * p39 + f_days * b39)
        res56 = int(f_km * p56 + f_days * b56)
        st.divider()
        st.subheader(f"39座: {res39} 元")
        st.subheader(f"56座: {res56} 元")

# --- 中间：提取行程 (实时联动区) ---
with col_extract:
    st.header("1️⃣ 提取行程")
    up_file = st.file_uploader("上传行程截图", type=["jpg", "png"])
    if up_file and st.button("开始识别", use_container_width=True):
        st.session_state['ocr_raw'] = ocr_engine(up_file.read())
    
    ocr_edit = st.text_area("OCR原文", value=st.session_state['ocr_raw'], height=150)
    
    cb1, cb2 = st.columns(2)
    if cb1.button("✨ AI 提取", use_container_width=True):
        st.session_state['temp_preview_text'] = ai_extract(ocr_edit)
        # AI提取后也手动触发一次列表更新
        st.session_state['final_station_list'] = re.split(r'[，,\s]+', st.session_state['temp_preview_text'])
        
    if cb2.button("🤖 规则提取", use_container_width=True):
        st.session_state['temp_preview_text'] = rule_extract(ocr_edit)
        st.session_state['final_station_list'] = re.split(r'[，,\s]+', st.session_state['temp_preview_text'])
    
    st.write("---")
    
    # 【实时关键点】：添加 on_change 参数，一旦你修改景德镇，sync_stations 就会运行
    modified_text = st.text_area(
        "🖊️ 提取结果预览 (地名修改后自动同步右侧)", 
        value=st.session_state['temp_preview_text'], 
        height=150,
        key="modified_input",
        on_change=sync_stations
    )
    
    # 依然保留你的手动填充按钮，作为一种保险操作
    if st.button("🚀 强制填充至站点", type="primary", use_container_width=True):
        sync_stations()
        st.rerun()

# --- 右侧：站点确认区 ---
with col_confirm:
    st.header("2️⃣ 站点确认")
    
    current_coords = []
    # 实时从同步后的列表里生成输入框
    station_names = [s for s in st.session_state['final_station_list'] if s]
    
    if not station_names:
        st.info("等待输入地名...")
    else:
        for i, name in enumerate(station_names):
            with st.container(border=True):
                # 这里使用 key=f"kw_{name}_{i}" 保证地名改变时组件刷新
                search_kw = st.text_input(f"站{i+1} 搜索", value=name, key=f"kw_{i}_{name}")
                t_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={search_kw}&key={AMAP_KEY}"
                try:
                    res_json = requests.get(t_url, timeout=5).json()
                    tips = [t for t in res_json.get('tips', []) if t.get('location')]
                    if tips:
                        options = [f"{t['name']} ({t.get('district','')})" for t in tips]
                        sel = st.selectbox(f"确认具体位置", options=options, key=f"sel_{i}_{name}")
                        matched_loc = next(t['location'] for t in tips if sel.startswith(t['name']))
                        current_coords.append(matched_loc)
                except: pass

        # 测距按钮（保留手动点击开始导航）
        if len(current_coords) >= 2:
            if st.button("🗺️ 开始导航计算里程", use_container_width=True, type="primary"):
                org, des = current_coords[0], current_coords[-1]
                way = ";".join(current_coords[1:-1])
                d_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&waypoints={way}&key={AMAP_KEY}"
                
                try:
                    route_res = requests.get(d_url).json()
                    if route_res['status'] == '1':
                        dist = int(int(route_res['route']['paths'][0]['distance']) / 1000)
                        st.session_state['km_auto'] = dist
                        st.rerun()
                except: st.error("网络异常")

    if st.session_state['km_auto'] > 0:
        st.success(f"### ✅ 自动测距结果：{st.session_state['km_auto']} KM")
