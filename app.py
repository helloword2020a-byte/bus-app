import streamlit as st
import pandas as pd
import requests
import re
import base64

# --- 1. 配置 ---
BAIDU_API_KEY = "1vBiCqNtSYFRx6GYsGwpwXdM"       
BAIDU_SECRET_KEY = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO" 
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆-报价系统", layout="wide")

# --- 2. CSS 样式：深度紧凑化 + 字体微调 ---
st.markdown("""
    <style>
    .block-container {padding: 1rem 2rem !important;}
    /* 缩小所有输入框的高度 */
    .stNumberInput div div input, .stTextInput div div input {padding: 0.2rem !important; height: 1.8rem !important;}
    /* 压缩行间距 */
    div[data-testid="stVerticalBlock"] > div {margin-bottom: -0.6rem !important;}
    /* 调整侧边栏宽度 */
    [data-testid="stSidebar"] {min-width: 220px; max-width: 220px;}
    /* 右侧报价区字体缩小 */
    .quote-box { font-size: 0.85rem; background-color: #f9f9f9; padding: 10px; border-radius: 5px; border-left: 5px solid #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 功能函数 ---
def get_baidu_token():
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={BAIDU_API_KEY}&client_secret={BAIDU_SECRET_KEY}"
    try: return requests.get(url).json().get("access_token")
    except: return None

def ocr_engine(file_bytes):
    token = get_baidu_token()
    if not token: return "授权失败"
    img64 = base64.b64encode(file_bytes).decode()
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token={token}"
    res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
    return "\n".join([i['words'] for i in res.get('words_result', [])])

# --- 4. 侧边栏：单纯放配置 ---
with st.sidebar:
    st.subheader("⚙️ 计费标准")
    st.markdown("**39座大巴**")
    b39 = st.number_input("起步费", value=800, key="sb39")
    p39 = st.number_input("单价(元/KM)", value=2.6, key="sp39")
    st.divider()
    st.markdown("**56座大巴**")
    b56 = st.number_input("起步费 ", value=1000, key="sb56")
    p56 = st.number_input("单价(元/KM) ", value=3.6, key="sp56")

# --- 5. 主页面布局 ---
st.title("🚌 九江祥隆旅游运输报价系统")
col_ocr, col_site = st.columns([1, 1.2])

with col_ocr:
    st.markdown("### 1️⃣ 行程识别")
    up_file = st.file_uploader("上传截图", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
    if up_file:
        img_bytes = up_file.read()
        st.image(img_bytes, width=250)
        if st.button("🚀 开始文字识别", use_container_width=True):
            st.session_state['ocr_raw'] = ocr_engine(img_bytes)
    
    txt = st.text_area("识别文本校对", value=st.session_state.get('ocr_raw', ""), height=180)
    if st.button("✨ 提取地名关键词", use_container_width=True):
        raw = txt
        noise = [r"第\d+天", r"行程", r"简易", r"车程约?[\d\.h小时]+", r"住[^\s，。]*", r"前往", r"接引", r"返程", r"结束", r"含早", r"下午", r"上午", r"接$", r"送$"]
        for p in noise: raw = re.sub(p, " ", raw)
        found = re.findall(r'[\u4e00-\u9fa5]{2,6}', raw)
        stop = ["可以", "需要", "提示", "进行", "返回", "地点", "时间", "到达", "游览", "早餐", "晚餐"]
        st.session_state['sites_final'] = " ".join(dict.fromkeys([w for w in found if w not in stop and len(w)>1]))

with col_site:
    st.markdown("### 2️⃣ 站点确认与自动报价")
    sites = st.text_input("关键词列表", value=st.session_state.get('sites_final', ""), label_visibility="collapsed")
    
    locs = []
    if sites:
        names = sites.split()
        grid = st.columns(2)
        for i, name in enumerate(names):
            with grid[i % 2]:
                url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
                tips = requests.get(url).json().get('tips', [])
                opts = [f"{t['name']} ({t.get('district','')})" for t in tips if t.get('location')]
                sel = st.selectbox(f"{i+1}:{name}", opts or [f"{name}?"], key=f"s_{i}")
                coord = next((t['location'] for t in tips if t['name'] == sel.split(" (")[0]), None)
                if coord: locs.append(coord)

    if len(locs) >= 2:
        try:
            # 自动测距
            org, des, way = locs[0], locs[-1], ";".join(locs[1:-1])
            res = requests.get(f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way}").json()
            km_val = int(round(int(res['route']['paths'][0]['distance']) / 1000))
            
            # --- 报价展示区（原红框搬迁并紧凑化） ---
            st.markdown("---")
            rc1, rc2 = st.columns(2)
            final_km = rc1.number_input("实测公里 (KM)", value=km_val)
            final_days = rc2.number_input("用车天数 (天)", value=4)
            
            res_39 = int(final_km * p39 + final_days * b39)
            res_56 = int(final_km * p56 + final_days * b56)
            
            # 极简结果表
            st.markdown(f"""
            <div class="quote-box">
                <b>💰 报价单生成：</b><br>
                39座方案：<b>{res_39} 元</b> （{final_km}km × {p39} + {final_days}天 × {b39}）<br>
                56座方案：<b>{res_56} 元</b> （{final_km}km × {p56} + {final_days}天 × {b56}）
            </div>
            """, unsafe_allow_html=True)
            
        except: st.warning("请正确选择站点位置以计算距离")
