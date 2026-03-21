import streamlit as st
import pandas as pd
import requests
import re
import base64

# --- 1. 配置与密钥 ---
BAIDU_API_KEY = "1vBiCqNtSYFRx6GYsGwpwXdM"       
BAIDU_SECRET_KEY = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO" 
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统", layout="wide")

# --- 2. 深度视觉压缩 CSS ---
st.markdown("""
    <style>
    /* 全局间距压缩 */
    .block-container {padding-top: 1rem !important; padding-bottom: 0rem !important;}
    div[data-testid="stVerticalBlock"] > div {margin-bottom: -0.8rem !important;}
    .stNumberInput, .stTextInput, .stSelectbox {margin-bottom: -1rem !important;}
    
    /* 右侧文字与组件缩小 */
    [data-testid="stColumn"]:nth-child(2) {
        font-size: 0.85rem !important;
    }
    [data-testid="stColumn"]:nth-child(2) label {
        font-size: 0.8rem !important;
        color: #555;
    }
    
    /* 标题压缩 */
    h1 {font-size: 1.5rem !important; margin-bottom: -1rem !important;}
    h2 {font-size: 1.2rem !important; margin-bottom: -0.5rem !important;}
    h3 {font-size: 1rem !important; margin-bottom: -0.5rem !important;}
    
    /* 表格紧凑化 */
    .stDataFrame {font-size: 0.8rem !important;}
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心功能函数 ---
def get_baidu_token():
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={BAIDU_API_KEY}&client_secret={BAIDU_SECRET_KEY}"
    try: return requests.get(url).json().get("access_token")
    except: return None

def ocr_smart_engine(file_bytes):
    token = get_baidu_token()
    if not token: return "密钥授权失败"
    img64 = base64.b64encode(file_bytes).decode()
    for api in ["accurate", "accurate_basic", "general_basic"]:
        url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/{api}?access_token={token}"
        try:
            res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
            if 'words_result' in res: return "\n".join([item['words'] for item in res['words_result']])
        except: continue
    return "识别失败"

# 初始化数据
if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

# --- 4. 侧边栏：配置参数 + 结果产出 ---
with st.sidebar:
    st.markdown("### ⚙️ 报价配置与结果")
    
    with st.expander("📝 计费单价设定", expanded=True):
        c1, c2 = st.columns(2)
        base_39 = c1.number_input("39座起步", value=800, key="b39")
        price_39 = c2.number_input("39座单价", value=2.6, step=0.1, key="p39")
        base_56 = c1.number_input("56座起步", value=1000, key="b56")
        price_56 = c2.number_input("56座单价", value=3.6, step=0.1, key="p56")

    st.markdown("---")
    st.markdown("### 📊 最终报价核算")
    f_km = st.number_input("实测总公里 (KM)", value=st.session_state['km_auto'])
    days = st.number_input("用车总天数 (天)", value=4, min_value=1)
    
    p39 = int(f_km * price_39 + days * base_39)
    p56 = int(f_km * price_56 + days * base_56)
    
    st.dataframe(pd.DataFrame({
        "车型": ["39座", "56座"], 
        "报价": [f"{p39}元", f"{p56}元"],
        "明细": [f"{f_km}k/{days}d", f"{f_km}k/{days}d"]
    }), use_container_width=True, hide_index=True)
    
    if st.button("🔄 刷新公里数"): st.rerun()

# --- 5. 主界面：左右分栏 ---
st.title("🚌 九江祥隆报价系统")

m_left, m_right = st.columns([1, 1.3])

with m_left:
    st.markdown("### 1️⃣ 行程识别")
    up_file = st.file_uploader("粘贴图片", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
    if up_file:
        img_bytes = up_file.read()
        st.image(img_bytes, width=280) # 进一步缩小图片预览
        if st.button("🚀 开始识别", use_container_width=True):
            st.session_state['ocr_raw'] = ocr_smart_engine(img_bytes)
    
    text_edit = st.text_area("识别校对：", value=st.session_state.get('ocr_raw', ""), height=100)
    
    if st.button("✨ 提取地名", use_container_width=True):
        raw = text_edit
        noise = [r"第\d+天", r"行程", r"简易", r"车程约?[\d\.h小时]+", r"住[^\s，。]*", r"前往", r"接引", r"返程", r"结束", r"含早", r"下午", r"上午", r"接$", r"送$"]
        for p in noise: raw = re.sub(p, " ", raw)
        found = re.findall(r'[\u4e00-\u9fa5]{2,6}', raw)
        stop_words = ["可以", "需要", "提示", "进行", "返回", "地点", "时间", "到达", "游览", "早餐", "晚餐"]
        clean_sites = [w for w in found if w not in stop_words and len(w) > 1]
        st.session_state['sites_final'] = " ".join(dict.fromkeys(clean_sites)) # 去重

with m_right:
    st.markdown("### 2️⃣ 站点与测距")
    site_str = st.text_input("关键词：", value=st.session_state.get('sites_final', ""), label_visibility="collapsed")
    
    loc_data = []
    if site_str:
        names = site_str.split()
        grid = st.columns(2)
        for i, name in enumerate(names):
            with grid[i % 2]:
                search_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
                try:
                    tips = requests.get(search_url).json().get('tips', [])
                    opts = [f"{t['name']} ({t.get('district','')})" for t in tips if t.get('location')]
                    sel = st.selectbox(f"{i+1}:{name}", opts or [f"{name}?"], key=f"site_{i}")
                    coord = next((t['location'] for t in tips if t['name'] == sel.split(" (")[0]), None)
                    if coord: loc_data.append(coord)
                except: pass

    if len(loc_data) >= 2:
        try:
            org, des, way = loc_data[0], loc_data[-1], ";".join(loc_data[1:-1])
            r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way}"
            res = requests.get(r_url).json()
            km_val = int(round(int(res['route']['paths'][0]['distance']) / 1000))
            st.session_state['km_auto'] = km_val
            st.info(f"📍 实测: {km_val} KM (已同步左侧)")
        except: st.warning("测距失败")
