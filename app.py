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
    .price-amount { font-size: 2rem; font-weight: 700; color: #1d4ed8; }
    .station-container { max-height: 600px; overflow-y: auto; padding: 10px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; }
    .stButton > button { border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

# ==================== 2. 状态初始化 ====================
_defaults = {
    'ocr_raw': "", 
    'temp_preview_text': "",     # 中间地名列表（可手写修改）
    'final_station_list': [],    # 确认同步后的正式站点
    'km_auto': 0
}
for k, v in _defaults.items():
    if k not in st.session_state: st.session_state[k] = v

AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"
AI_KEY = "bce-v3/ALTAK-EMZixkEbLJ0iEkFcaJCFc/74514893890101d198dd642b3b95ea68bed95897"

# ==================== 3. 功能函数 ====================

def get_baidu_token():
    try:
        url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id=1vBiCqNtSYFRx6GYsGwpwXdM&client_secret=ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"
        return requests.get(url).json().get("access_token")
    except: return None

def ocr_engine(file_bytes):
    token = get_baidu_token()
    if not token: return "Token失败"
    img64 = base64.b64encode(file_bytes).decode()
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token={token}"
    res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
    return "".join([i['words'] for i in res.get('words_result', [])])

def rule_extract(text):
    """自动规则过滤逻辑"""
    clean = re.sub(r'\(.*?\)|（.*?）|\d+\.?\d*|[^\u4e00-\u9fa5\s,，]', ' ', text or "")
    for word in ['接', '送', '前往', '返程', '车程', '住', '小时', '公里', '行程']: 
        clean = clean.replace(word, ' ')
    return "，".join(clean.split())

# ==================== 4. 界面布局 ====================

st.markdown('<div class="main-header"><h1>🚌 九江祥隆旅游运输报价系统</h1><p>旗舰版 | 缓冲同步模式</p></div>', unsafe_allow_html=True)

col_calc, col_extract, col_confirm = st.columns([0.8, 1.1, 1.3])

# --- 左侧：报价核算 ---
with col_calc:
    st.subheader("📊 报价核算")
    with st.container(border=True):
        f_km = st.number_input("总公里 (KM)", value=st.session_state['km_auto'])
        f_days = st.number_input("用车天数", value=4)
        st.divider()
        res39 = int(f_km * 2.6 + f_days * 800)
        res56 = int(f_km * 3.6 + f_days * 1000)
        st.markdown(f'<div class="price-box"><div class="label">39座报价</div><div class="price-amount">{res39}元</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="price-box"><div class="label">56座报价</div><div class="price-amount">{res56}元</div></div>', unsafe_allow_html=True)

# --- 中间：地名缓冲区 ---
with col_extract:
    st.subheader("1️⃣ 行程解析")
    up_file = st.file_uploader("上传截图", type=["jpg", "png", "jpeg"])
    if up_file and st.button("🚀 识别图片文字", use_container_width=True):
        st.session_state['ocr_raw'] = ocr_engine(up_file.read())
    
    ocr_res = st.text_area("OCR原文", value=st.session_state['ocr_raw'], height=100)
    
    c1, c2 = st.columns(2)
    # 点击这两个按钮，只更新下面的 temp_preview_text 文本框
    if c1.button("✨ AI 智能提取", use_container_width=True):
        # 此处模拟AI提取逻辑
        st.session_state['temp_preview_text'] = "九江，吉安，上饶"
    if c2.button("🤖 规则辅助提取", use_container_width=True):
        st.session_state['temp_preview_text'] = rule_extract(ocr_res)
    
    st.divider()
    # 【核心地名列表】：这里可以手动修改文字
    edited_sites = st.text_area(
        "🖊️ 地名列表 (可在此手动修改地名)", 
        value=st.session_state['temp_preview_text'], 
        height=150,
        help="地名之间请用逗号或空格分隔"
    )
    # 将手动修改的文字实时保存回 session
    st.session_state['temp_preview_text'] = edited_sites

    # 【同步按钮】：只有点这个，右侧才会动
    if st.button("🚀 确认并同步到站点", type="primary", use_container_width=True):
        # 解析文本框中的地名
        site_list = re.split(r'[，,\s]+', edited_sites)
        st.session_state['final_station_list'] = [s.strip() for s in site_list if s.strip()]
        st.rerun()

# --- 右侧：正式站点确认 ---
with col_confirm:
    st.subheader("2️⃣ 站点确认")
    current_coords = []
    
    if not st.session_state['final_station_list']:
        st.info("💡 请在左侧确认地名后点击同步按钮")
    else:
        st.markdown('<div class="station-container">', unsafe_allow_html=True)
        for i, name in enumerate(st.session_state['final_station_list']):
            with st.container(border=True):
                # 这里的输入框是基于已经同步过来的地名
                search_kw = st.text_input(f"站{i+1} 搜索关键词", value=name, key=f"site_{i}")
                t_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={search_kw}&key={AMAP_KEY}"
                try:
                    tips = requests.get(t_url, timeout=5).json().get('tips', [])
                    valid_tips = [t for t in tips if t.get('location')]
                    if valid_tips:
                        opts = [f"{t['name']} ({t.get('district','')})" for t in valid_tips]
                        sel = st.selectbox(f"确认站{i+1}精确位置", options=opts, key=f"sel_{i}")
                        loc = next(t['location'] for t in valid_tips if sel.startswith(t['name']))
                        current_coords.append(loc)
                except: pass
        st.markdown('</div>', unsafe_allow_html=True)

        if len(current_coords) >= 2:
            st.write("")
            if st.button("🗺️ 开始计算导航里程", type="primary", use_container_width=True):
                org, des = current_coords[0], current_coords[-1]
                way = ";".join(current_coords[1:-1])
                d_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&waypoints={way}&key={AMAP_KEY}"
                res = requests.get(d_url).json()
                if res['status'] == '1':
                    st.session_state['km_auto'] = int(int(res['route']['paths'][0]['distance']) / 1000)
                    st.rerun()

    if st.session_state['km_auto'] > 0:
        st.success(f"🚩 规划完成！里程：{st.session_state['km_auto']} KM")
