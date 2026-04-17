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
    /* 右侧站点区独立滚动容器 */
    .scroll-container {
        max-height: 700px;
        overflow-y: auto;
        padding: 10px;
        border: 1px solid #f0f2f6;
        border-radius: 8px;
        background-color: #fafafa;
    }
    /* 公里数显示样式 */
    .km-display {
        font-size: 22px;
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
    token = requests.get(f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={BAIDU_OCR_AK}&client_secret={BAIDU_OCR_SK}").json().get("access_token")
    img64 = base64.b64encode(file_bytes).decode()
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token={token}"
    res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
    return "".join([i['words'] for i in res.get('words_result', [])])

def ai_extract(text):
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-128k"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {AI_API_KEY_V2}"}
    prompt = f"提取目的地地名，地名间用中文逗号分隔。原文：{text}"
    try:
        res = requests.post(url, headers=headers, json={"messages": [{"role": "user", "content": prompt}]}).json()
        return res.get("result", "")
    except: return ""

def rule_extract(text):
    clean = re.sub(r'\(.*?\)|（.*?）|\d+\.?\d*|[^\u4e00-\u9fa5\s,，]', ' ', text or "")
    for word in ['接', '送', '前往', '返程', '车程', '住', '小时', '公里']: clean = clean.replace(word, ' ')
    return "，".join(clean.split())

# ==================== 4. 经典三列布局 ====================
col_calc, col_extract, col_confirm = st.columns([0.8, 1, 1.2])

# --- 左侧：报价核算 (数据联动) ---
with col_calc:
    st.header("📊 报价核算")
    with st.form("price_form"):
        c1, c2 = st.columns(2)
        b39, p39 = c1.number_input("39起步", 800), c2.number_input("39单价", 2.6)
        b56, p56 = c1.number_input("56起步", 1000), c2.number_input("56单价", 3.6)
        # 这里的公里数会自动接收右侧计算的结果
        f_km = st.number_input("总公里 (KM)", value=st.session_state['km_auto'])
        f_days = st.number_input("天数", 4)
        st.form_submit_button("💰 更新价格")
    
    res39, res56 = int(f_km*p39 + f_days*b39), int(f_km*p56 + f_days*b56)
    st.success(f"39座: {res39} 元 | 56座: {res56} 元")
    st.text_area("报价单副本", f"里程：{f_km}KM\n39座预估：{res39}元\n56座预估：{res56}元", height=100)

# --- 中间：行程提取区 (可人工干预) ---
with col_extract:
    st.header("1️⃣ 提取行程")
    up_file = st.file_uploader("上传截图", type=["jpg", "png"])
    if up_file and st.button("开始 OCR 识别", use_container_width=True):
        st.session_state['ocr_raw'] = ocr_engine(up_file.read())
    
    ocr_edit = st.text_area("OCR原文校对", value=st.session_state['ocr_raw'], height=150)
    
    c_btn1, c_btn2 = st.columns(2)
    if c_btn1.button("✨ 智能 AI 提取", use_container_width=True):
        st.session_state['temp_preview_text'] = ai_extract(ocr_edit)
    if c_btn2.button("🤖 自动规则提取", use_container_width=True):
        st.session_state['temp_preview_text'] = rule_extract(ocr_edit)
    
    st.write("---")
    # 【预览框】：人工修正核心区，支持逗号或空格分隔
    modified_text = st.text_area("🖊️ 提取结果预览(请确认逗号分隔地名)", 
                                 value=st.session_state['temp_preview_text'], 
                                 height=100)
    # 保持状态实时同步
    st.session_state['temp_preview_text'] = modified_text

    # 【唯一填充触发按钮】
    if st.button("🚀 确认并填充至站点", type="primary", use_container_width=True):
        # 正则匹配：支持中文逗号、英文逗号、空格作为分隔符
        site_list = re.split(r'[，,\s]+', modified_text)
        st.session_state['final_station_list'] = [s.strip() for s in site_list if s.strip()]
        st.rerun() # 强制重启以更新右侧组件

# --- 右侧：站点确认区 (高德实时联想) ---
with col_confirm:
    st.header("2️⃣ 站点确认")
    st.markdown('<div class="scroll-container">', unsafe_allow_html=True)
    
    current_coords = []
    # 使用 final_station_list 的长度作为 Key 的一部分，确保填充时组件强制刷新
    for i, name in enumerate(st.session_state['final_station_list']):
        with st.container(border=True):
            # 修正搜索词输入框
            search_kw = st.text_input(f"站{i+1} 搜索词", value=name, key=f"kw_{i}_{len(st.session_state['final_station_list'])}")
            t_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={search_kw}&key={AMAP_KEY}"
            try:
                tips = requests.get(t_url, timeout=5).json().get('tips', [])
                valid = [t for t in tips if t.get('location')]
                if valid:
                    # 联想下拉选择框
                    sel = st.selectbox(f"确认站{i+1}精准位置", 
                                       options=[f"{t['name']} ({t.get('district','')})" for t in valid], 
                                       key=f"sel_{i}_{len(st.session_state['final_station_list'])}")
                    loc = next(t['location'] for t in valid if sel.startswith(t['name']))
                    current_coords.append(loc)
                    st.caption(f"📍 已选中坐标: {loc}")
            except: pass
            
    st.markdown('</div>', unsafe_allow_html=True)

    # 测距执行与结果反馈
    if len(current_coords) >= 2:
        st.divider()
        if st.button("🗺️ 确认所有站点，开始规划行程", use_container_width=True, type="primary"):
            org, des, way = current_coords[0], current_coords[-1], ";".join(current_coords[1:-1])
            d_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&waypoints={way}&key={AMAP_KEY}"
            try:
                res = requests.get(d_url).json()
                if res['status'] == '1':
                    st.session_state['km_auto'] = int(int(res['route']['paths'][0]['distance']) / 1000)
                    st.rerun()
                else: st.error("地图标注不全，测距失败")
            except: st.error("网络连接异常")
            
        # 【新增】：测完后在下方显示总公里数
        if st.session_state['km_auto'] > 0:
            st.markdown(f'<div class="km-display">✅ 规划完成！总公里数：{st.session_state["km_auto"]} KM</div>', unsafe_allow_html=True)
