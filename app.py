import streamlit as st
import pandas as pd
import requests
import re
import base64
import json

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
        max-height: 600px;
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
        padding: 15px;
        background-color: #fff5f5;
        border: 2px solid #ff4b4b;
        border-radius: 10px;
        margin: 10px 0;
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

# ==================== 4. 界面布局 ====================
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
        
        f_km = st.number_input("当前总公里 (KM)", value=st.session_state['km_auto'], key="manual_km")
        f_days = st.number_input("用车天数", 4)
        
        res39 = int(f_km * p39 + f_days * b39)
        res56 = int(f_km * p56 + f_days * b56)
        
        st.divider()
        st.subheader(f"39座: {res39} 元")
        st.subheader(f"56座: {res56} 元")
        
    st.text_area("报价单副本", f"【九江祥龙】\n总里程：{f_km}KM\n总天数：{f_days}天\n---\n39座大巴：{res39}元\n56座大巴：{res56}元", height=120)

# --- 中间：提取行程 (支持实时编辑) ---
with col_extract:
    st.header("1️⃣ 提取行程")
    up_file = st.file_uploader("上传行程截图", type=["jpg", "png"])
    if up_file and st.button("开始识别", use_container_width=True):
        st.session_state['ocr_raw'] = ocr_engine(up_file.read())
    
    ocr_edit = st.text_area("OCR原文", value=st.session_state['ocr_raw'], height=150)
    
    cb1, cb2 = st.columns(2)
    if cb1.button("✨ AI 提取", use_container_width=True):
        st.session_state['temp_preview_text'] = ai_extract(ocr_edit)
    if cb2.button("🤖 规则提取", use_container_width=True):
        st.session_state['temp_preview_text'] = rule_extract(ocr_edit)
    
    st.write("---")
    # 这里是核心：modified_text 的修改会直接存入 temp_preview_text
    modified_text = st.text_area("🖊️ 提取结果预览 (地名请用逗号/空格分隔)", 
                                 value=st.session_state['temp_preview_text'], 
                                 height=150,
                                 help="在这里增加或删减地名，下方的站点框会随之改变")
    st.session_state['temp_preview_text'] = modified_text

    # 填充按钮
    if st.button("🚀 确认并填充至站点", type="primary", use_container_width=True):
        site_list = re.split(r'[，,\s]+', modified_text)
        st.session_state['final_station_list'] = [s.strip() for s in site_list if s.strip()]
        st.rerun()

# --- 右侧：站点确认区 (高德实时联想) ---
with col_confirm:
    st.header("2️⃣ 站点确认")
    
    current_coords = []
    station_names = st.session_state['final_station_list']
    
    if not station_names:
        st.info("请先在左侧提取或手动输入地名并点击确认填充。")
    else:
        st.markdown('<div class="scroll-container">', unsafe_allow_html=True)
        for i, name in enumerate(station_names):
            with st.container(border=True):
                # 即使在这里修改站点的搜索词，也会实时联想
                search_kw = st.text_input(f"站{i+1} 搜索", value=name, key=f"kw_{i}")
                t_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={search_kw}&key={AMAP_KEY}"
                try:
                    res_json = requests.get(t_url, timeout=5).json()
                    tips = [t for t in res_json.get('tips', []) if t.get('location')]
                    if tips:
                        options = [f"{t['name']} ({t.get('district','')})" for t in tips]
                        sel = st.selectbox(f"确认具体位置", options=options, key=f"sel_{i}")
                        # 提取坐标
                        matched_loc = next(t['location'] for t in tips if sel.startswith(t['name']))
                        current_coords.append(matched_loc)
                    else:
                        st.warning("未找到匹配地点")
                except: pass
        st.markdown('</div>', unsafe_allow_html=True)

        # 测距按钮
        st.write("")
        if len(current_coords) >= 2:
            if st.button("🗺️ 开始导航计算里程", use_container_width=True, type="primary"):
                org = current_coords[0]
                des = current_coords[-1]
                way = ";".join(current_coords[1:-1])
                d_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&waypoints={way}&key={AMAP_KEY}"
                
                try:
                    route_res = requests.get(d_url).json()
                    if route_res['status'] == '1':
                        dist = int(int(route_res['route']['paths'][0]['distance']) / 1000)
                        st.session_state['km_auto'] = dist
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("路径规划失败，请检查站点是否跨海或跨越无法驾车的区域")
                except:
                    st.error("网络异常")

    # 结果显示
    if st.session_state['km_auto'] > 0:
        st.markdown(f'<div class="km-display">✅ 自动测距结果：{st.session_state["km_auto"]} KM</div>', unsafe_allow_html=True)
        if st.button("🔄 清除当前里程"):
            st.session_state['km_auto'] = 0
            st.rerun()
