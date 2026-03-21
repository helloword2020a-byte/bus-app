import streamlit as st
import pandas as pd
import requests
import re
import base64

# --- 1. 基础配置 ---
BAIDU_API_KEY = "1vBiCqNtSYFRx6GYsGwpwXdM"       
BAIDU_SECRET_KEY = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO" 
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统", layout="wide")

# --- 2. 深度紧凑样式 ---
st.markdown("""
    <style>
    .block-container {padding: 1rem !important;}
    div[data-testid="stVerticalBlock"] > div {margin-bottom: -0.7rem !important;}
    .stNumberInput div div input {height: 1.8rem !important;}
    /* 侧边栏报价区样式 */
    .sidebar-quote {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #dcdcdc;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 初始化状态 ---
if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

# --- 4. 核心功能函数 ---
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

# --- 5. 侧边栏：参数设定 + 报价结果 (常驻左侧) ---
with st.sidebar:
    st.title("📊 报价核算中心")
    
    with st.expander("🛠️ 计费标准", expanded=False):
        c1, c2 = st.columns(2)
        b39 = c1.number_input("39座起步", value=800)
        p39 = c2.number_input("39座单价", value=2.6)
        b56 = c1.number_input("56座起步", value=1000)
        p56 = c2.number_input("56座单价", value=3.6)

    st.divider()
    
    # 报价核心输入
    st.subheader("核心参数")
    # 公里数会根据右侧地图计算自动更新，也可以手动改
    f_km = st.number_input("实测总公里 (KM)", value=st.session_state['km_auto'])
    f_days = st.number_input("用车总天数 (天)", value=4)
    
    # 即时计算结果
    res_39 = int(f_km * p39 + f_days * b39)
    res_56 = int(f_km * p56 + f_days * b56)
    
    st.markdown("### 💰 最终报价")
    quote_df = pd.DataFrame({
        "车型": ["39座", "56座"],
        "总价": [f"{res_39}元", f"{res_56}元"],
        "明细": [f"{f_km}km/{f_days}天", f"{f_km}km/{f_days}天"]
    })
    st.table(quote_df) # 使用table更紧凑
    
    if st.button("🔄 刷新数据"): st.rerun()

# --- 6. 主界面布局 ---
st.header("🚌 九江祥隆旅游运输报价系统")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.markdown("### 1️⃣ 行程识别")
    up_file = st.file_uploader("上传行程截图", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
    if up_file:
        img_bytes = up_file.read()
        st.image(img_bytes, width=280)
        if st.button("🚀 开始识别", use_container_width=True):
            st.session_state['ocr_raw'] = ocr_engine(img_bytes)
    
    txt_area = st.text_area("识别校对", value=st.session_state.get('ocr_raw', ""), height=150)
    
    if st.button("✨ 提取纯净地名", use_container_width=True):
        raw = txt_area
        # 更加严厉的过滤规则，剔除动作词和杂词
        noise = [
            r"第\d+天", r"行程", r"简易", r"车程约?[\d\.h小时]+", r"住[^\s，。]*", 
            r"前往", r"接引", r"返程", r"结束", r"含早", r"下午", r"上午", 
            r"接$", r"^接", r"送$", r"^送", r"抵达", r"集合", r"游览"
        ]
        for p in noise: raw = re.sub(p, " ", raw)
        found = re.findall(r'[\u4e00-\u9fa5]{2,6}', raw)
        # 排除名单
        stop_words = ["可以", "需要", "提示", "进行", "返回", "地点", "时间", "到达", "游览", "早餐", "晚餐", "酒店", "出发", "南昌接"]
        clean = []
        for w in found:
            # 进一步清洗：如果地名里还带着“接”字，直接去掉
            w_clean = w.replace("接", "").replace("送", "").replace("住", "")
            if w_clean not in stop_words and len(w_clean) > 1:
                if w_clean not in clean: clean.append(w_clean)
        st.session_state['sites_final'] = " ".join(clean)

with m_right:
    st.markdown("### 2️⃣ 站点确认")
    site_input = st.text_input("提取的关键词", value=st.session_state.get('sites_final', ""), label_visibility="collapsed")
    
    loc_data = []
    if site_input:
        names = site_input.split()
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
            # 关键：自动更新左侧的公里数
            st.session_state['km_auto'] = km_val
            st.success(f"📍 地图实测: {km_val} KM (已同步至左侧)")
        except: st.error("地图测距失败，请检查站点选择")
