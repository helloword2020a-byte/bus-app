import streamlit as st
import pandas as pd
import requests
import re
import base64
import time

# ==================== 1. 页面配置与样式 ====================
st.set_page_config(page_title="九江祥隆报价系统-旗舰版", page_icon="🚌", layout="wide")

st.markdown("""
<style>
    .main-header { background: linear-gradient(135deg, #1a3a5c 0%, #2563a8 100%); color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; }
    .price-box { background: #f0f7ff; border: 2px solid #3b82f6; border-radius: 10px; padding: 15px; text-align: center; margin: 10px 0; }
    .price-amount { font-size: 1.8rem; font-weight: 700; color: #1d4ed8; }
    .station-container { max-height: 550px; overflow-y: auto; padding: 10px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; }
    .stButton > button { border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

# ==================== 2. 状态初始化 ====================
_defaults = {
    'ocr_raw': "", 
    'temp_preview_text': "",     # 缓冲区地名（可修改）
    'final_station_list': [],    # 同步后的正式站点
    'km_auto': 0
}
for k, v in _defaults.items():
    if k not in st.session_state: st.session_state[k] = v

AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"
AI_KEY = "bce-v3/ALTAK-EMZixkEbLJ0iEkFcaJCFc/74514893890101d198dd642b3b95ea68bed95897"

# ==================== 3. 核心功能函数 ====================

def get_baidu_token():
    try:
        url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id=1vBiCqNtSYFRx6GYsGwpwXdM&client_secret=ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"
        return requests.get(url).json().get("access_token")
    except: return None

def ocr_engine(file_bytes):
    token = get_baidu_token()
    if not token: return "Token获取失败"
    img64 = base64.b64encode(file_bytes).decode()
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token={token}"
    try:
        res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
        return "".join([i['words'] for i in res.get('words_result', [])])
    except: return "识别异常"

def rule_extract(text):
    clean = re.sub(r'\(.*?\)|（.*?）|\d+\.?\d*|[^\u4e00-\u9fa5\s,，]', ' ', text or "")
    for word in ['接', '送', '前往', '返程', '车程', '住', '小时', '公里', '行程']: 
        clean = clean.replace(word, ' ')
    return "，".join(clean.split())

# ==================== 4. 界面布局 ====================

st.markdown('<div class="main-header"><h1>🚌 九江祥隆旅游运输报价系统</h1><p>旗舰版 | 计费自定义 + 缓冲同步模式</p></div>', unsafe_allow_html=True)

col_calc, col_extract, col_confirm = st.columns([0.9, 1.1, 1.3])

# --- 左侧：报价核算中心 ---
with col_calc:
    st.subheader("📊 报价核算中心")
    with st.container(border=True):
        st.write("⚙️ **计费标准设置**")
        ca, cb = st.columns(2)
        b39 = ca.number_input("39座起步费", value=800)
        p39 = cb.number_input("39座单价", value=2.60)
        b56 = ca.number_input("56座起步费", value=1000)
        p56 = cb.number_input("56座单价", value=3.60)
        
        st.divider()
        # 这里接收右侧测出来的公里数
        f_km = st.number_input("实测总公里 (KM)", value=st.session_state['km_auto'], step=1)
        f_days = st.number_input("用车总天数", value=4, step=1)
        
        # 计算逻辑
        res39 = int(f_km * p39 + f_days * b39)
        res56 = int(f_km * p56 + f_days * b56)
        
        st.markdown(f'<div class="price-box"><small>39座预估总价</small><div class="price-amount">{res39} 元</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="price-box"><small>56座预估总价</small><div class="price-amount">{res56} 元</div></div>', unsafe_allow_html=True)
    
    # 报价单副本
    st.write("📋 **报价单草稿**")
    copy_text = f"【九江祥隆报价】\n里程：{f_km}KM | 天数：{f_days}天\n---\n39座大巴：{res39}元\n56座大巴：{res56}元"
    st.text_area("复制结果文案", value=copy_text, height=120)

# --- 中间：地名缓冲区 ---
with col_extract:
    st.subheader("1️⃣ 行程解析提取")
    up_file = st.file_uploader("上传截图", type=["jpg", "png", "jpeg"])
    if up_file and st.button("🚀 开始识别图片文字", use_container_width=True):
        with st.spinner("识别中..."):
            st.session_state['ocr_raw'] = ocr_engine(up_file.read())
    
    ocr_res = st.text_area("OCR原文内容", value=st.session_state['ocr_raw'], height=100)
    
    c1, c2 = st.columns(2)
    if c1.button("✨ AI 智能提取", use_container_width=True):
        # 此处模拟AI提取逻辑
        st.session_state['temp_preview_text'] = "九江，吉安，上饶"
    if c2.button("🤖 规则辅助提取", use_container_width=True):
        st.session_state['temp_preview_text'] = rule_extract(ocr_res)
    
    st.divider()
    # 手动修改区
    edited_sites = st.text_area(
        "🖊️ 地名缓冲区 (提取后可手动增删改)", 
        value=st.session_state['temp_preview_text'], 
        height=150,
        help="修改完成后点击下方按钮同步"
    )
    st.session_state['temp_preview_text'] = edited_sites

    if st.button("🚀 确认并同步到站点", type="primary", use_container_width=True):
        site_list = re.split(r'[，,\s]+', edited_sites)
        st.session_state['final_station_list'] = [s.strip() for s in site_list if s.strip()]
        st.rerun()

# --- 右侧：站点确认与测距 ---
with col_confirm:
    st.subheader("2️⃣ 站点位置确认")
    current_coords = []
    
    if not st.session_state['final_station_list']:
        st.info("💡 请在中间区域提取并同步站点")
    else:
        st.markdown('<div class="station-container">', unsafe_allow_html=True)
        for i, name in enumerate(st.session_state['final_station_list']):
            with st.container(border=True):
                search_kw = st.text_input(f"站{i+1} 搜索", value=name, key=f"site_{i}")
                t_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={search_kw}&key={AMAP_KEY}"
                try:
                    tips = requests.get(t_url, timeout=5).json().get('tips', [])
                    valid = [t for t in tips if t.get('location')]
                    if valid:
                        opts = [f"{t['name']} ({t.get('district','')})" for t in valid]
                        sel = st.selectbox(f"确认具体位置", options=opts, key=f"sel_{i}")
                        loc = next(t['location'] for t in valid if sel.startswith(t['name']))
                        current_coords.append(loc)
                except: pass
        st.markdown('</div>', unsafe_allow_html=True)

        if len(current_coords) >= 2:
            st.write("")
            if st.button("🗺️ 开始导航计算里程", type="primary", use_container_width=True):
                with st.spinner("计算中..."):
                    org, des = current_coords[0], current_coords[-1]
                    way = ";".join(current_coords[1:-1])
                    d_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&waypoints={way}&key={AMAP_KEY}"
                    res = requests.get(d_url).json()
                    if res['status'] == '1':
                        st.session_state['km_auto'] = int(int(res['route']['paths'][0]['distance']) / 1000)
                        st.rerun()

    if st.session_state['km_auto'] > 0:
        st.success(f"🚩 规划完成！总里程：{st.session_state['km_auto']} KM")
