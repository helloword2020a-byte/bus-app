import streamlit as st
import pandas as pd
import requests
import re
import base64
import json

# ==================== 1. 核心密钥配置 (完整保留) ====================
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
        max-height: 750px;
        overflow-y: auto;
        padding: 10px;
        border: 1px solid #f0f2f6;
        border-radius: 8px;
        background-color: #fafafa;
    }
    .stTextArea textarea { font-size: 14px !important; }
    </style>
    """, unsafe_allow_html=True)

# 状态初始化
if 'ocr_raw' not in st.session_state: st.session_state['ocr_raw'] = ""
if 'temp_sites' not in st.session_state: st.session_state['temp_sites'] = "" # 提取出的临时文本
if 'final_stations' not in st.session_state: st.session_state['final_stations'] = [] # 点击填充后的正式列表
if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

# ==================== 3. 核心后端函数 ====================
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

def ai_extract(text):
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-128k"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {AI_API_KEY_V2}"}
    prompt = f"提取目的地地名，地名间用空格分隔。原文：{text}"
    try:
        res = requests.post(url, headers=headers, json={"messages": [{"role": "user", "content": prompt}]}).json()
        clean = re.sub(r'[^\u4e00-\u9fa5\s]', ' ', res.get("result", ""))
        return " ".join(clean.split())
    except: return ""

def rule_extract(text):
    clean = re.sub(r'\(.*?\)|（.*?）|\d+\.?\d*|[^\u4e00-\u9fa5\s]', ' ', text or "")
    for word in ['接', '送', '前往', '返程', '车程', '住', '小时', '公里']:
        clean = clean.replace(word, ' ')
    return " ".join(clean.split())

# ==================== 4. 经典三列布局 ====================
col_side, col_mid, col_right = st.columns([0.8, 1, 1.2])

# --- 第一柱：报价中心 ---
with col_side:
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
    st.text_area("文案副本", f"行程:{f_km}KM\n39座:{res39}元\n56座:{res56}元", height=100)

# --- 第二柱：识别与提取 (增加手动修正) ---
with col_mid:
    st.header("1️⃣ 提取行程")
    up_file = st.file_uploader("上传行程截图", type=["jpg", "png"])
    if up_file and st.button("开始识别文字", use_container_width=True):
        st.session_state['ocr_raw'] = ocr_engine(up_file.read())
    
    ocr_edit = st.text_area("OCR原文校对", value=st.session_state['ocr_raw'], height=150)
    
    # 双模提取按钮
    ca, cb = st.columns(2)
    if ca.button("✨ AI 提取", use_container_width=True):
        st.session_state['temp_sites'] = ai_extract(ocr_edit)
    if cb.button("🤖 规则提取", use_container_width=True):
        st.session_state['temp_sites'] = rule_extract(ocr_edit)
    
    # 【新增改进】：提取结果预览区改为可编辑的文本框
    st.write("---")
    final_preview = st.text_area("🖊️ 提取结果预览(可在此手动修改)：", 
                                value=st.session_state['temp_sites'], 
                                help="如果自动提取不准，请直接在这里增删地名，用空格分隔",
                                height=100)
    # 同步手动修改的内容到临时状态
    st.session_state['temp_sites'] = final_preview

    # 【填充按钮】：只有点这个，右侧才会生成站点
    if st.button("🚀 确认并填充至站点", type="primary", use_container_width=True):
        st.session_state['final_stations'] = st.session_state['temp_sites'].split()
        st.rerun()

# --- 第三柱：站点确认与测距 (独立滚动) ---
with col_right:
    st.header("2️⃣ 站点确认")
    
    st.markdown('<div class="scroll-container">', unsafe_allow_html=True)
    
    current_coords = []
    # 循环生成站点框
    for i, name in enumerate(st.session_state['final_stations']):
        with st.container(border=True):
            # 站点框人工输入：支持修改单个站点搜索词
            kw = st.text_input(f"站{i+1} 搜索词", value=name, key=f"kw_{i}")
            t_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={kw}&key={AMAP_KEY}"
            try:
                tips = requests.get(t_url, timeout=5).json().get('tips', [])
                valid = [t for t in tips if isinstance(t.get('location'), str) and t.get('location')]
                if valid:
                    sel = st.selectbox(f"确认站{i+1}", [f"{t['name']} ({t.get('district','')})" for t in valid], key=f"sel_{i}")
                    current_coords.append(next(t['location'] for t in valid if sel.startswith(t['name'])))
            except: pass
            
    st.markdown('</div>', unsafe_allow_html=True)

    # 计算按钮：不点击不测距
    if len(current_coords) >= 2:
        st.divider()
        if st.button("🗺️ 确认站点，开始规划测距", use_container_width=True, type="primary"):
            org, des, way = current_coords[0], current_coords[-1], ";".join(current_coords[1:-1])
            d_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&waypoints={way}&key={AMAP_KEY}"
            try:
                res = requests.get(d_url).json()
                if res['status'] == '1':
                    st.session_state['km_auto'] = int(int(res['route']['paths'][0]['distance']) / 1000)
                    st.success(f"计算成功：{st.session_state['km_auto']} KM")
                    st.rerun()
            except: st.error("测距失败")
