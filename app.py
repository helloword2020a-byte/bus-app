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

# --- 2. 样式美化 ---
st.markdown("""
    <style>
    .block-container {padding-top: 1rem !important;}
    /* 缩小左侧组件间距 */
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div {margin-bottom: -1rem !important;}
    /* 报价表紧凑化 */
    .q-table { font-size: 0.9rem; border-collapse: collapse; width: 100%; }
    .q-table td, .q-table th { border: 1px solid #ddd; padding: 4px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# 初始化状态
if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

# --- 3. 核心功能函数 ---
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
    # 关键：将所有文字连成一个长字符串，解决跨行断字问题
    return "".join([i['words'] for i in res.get('words_result', [])])

# --- 4. 侧边栏：核心操作区 (参数+天数+报价) ---
with st.sidebar:
    st.title("📊 报价核算中心")
    
    with st.expander("🛠️ 计费单价设定", expanded=False):
        c1, c2 = st.columns(2)
        b39 = c1.number_input("39座起步", value=800)
        p39 = c2.number_input("39座单价", value=2.6)
        b56 = c1.number_input("56座起步", value=1000)
        p56 = c2.number_input("56座单价", value=3.6)

    st.divider()
    
    # 核心输入区
    st.subheader("📝 行程参数")
    f_km = st.number_input("实测总公里 (KM)", value=st.session_state['km_auto'])
    f_days = st.number_input("用车总天数 (天)", value=4)
    
    # 计算报价
    res_39 = int(f_km * p39 + f_days * b39)
    res_56 = int(f_km * p56 + f_days * b56)
    
    st.markdown("### 💰 实时报价结果")
    # 构建HTML表格以节省空间
    st.markdown(f"""
    <table class="q-table">
        <tr style="background-color:#f0f2f6"><th>车型</th><th>报价</th><th>详情</th></tr>
        <tr><td>39座</td><td><b>{res_39}元</b></td><td>{f_km}k×{p39}+{f_days}d</td></tr>
        <tr><td>56座</td><td><b>{res_56}元</b></td><td>{f_km}k×{p56}+{f_days}d</td></tr>
    </table>
    """, unsafe_allow_html=True)
    
    st.info("💡 修改公里或天数，上方报价将自动更新")
    if st.button("🔄 同步最新数据"): st.rerun()

# --- 5. 主页面布局 ---
st.header("🚌 九江祥隆旅游运输报价系统")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.markdown("### 1️⃣ 行程识别")
    up_file = st.file_uploader("粘贴/上传行程单", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
    if up_file:
        img_bytes = up_file.read()
        st.image(img_bytes, width=280)
        if st.button("🚀 识别全文文字", use_container_width=True):
            st.session_state['ocr_raw'] = ocr_engine(img_bytes)
    
    txt_area = st.text_area("识别出的文本 (支持手动修改)：", value=st.session_state.get('ocr_raw', ""), height=200)
    
    if st.button("✨ 提取完整地名", use_container_width=True):
        raw = txt_area
        # 清洗逻辑：去掉日期、车程等干扰，保留纯中文名
        noise = [
            r"第\d+天", r"行程", r"车程约?[\d\.h小时]+", r"住[^\s，。]*", 
            r"前往", r"接引", r"返程", r"结束", r"含早", r"下午", r"上午", 
            r"抵达", r"集合", r"游览", r"简易"
        ]
        for p in noise: raw = re.sub(p, " ", raw)
        
        # 寻找连续的2-6个中文字符
        found = re.findall(r'[\u4e00-\u9fa5]{2,6}', raw)
        
        # 排除名单 & 深度清洗词干
        stop_words = ["可以", "需要", "提示", "进行", "返回", "地点", "时间", "到达", "游览", "早餐", "晚餐", "酒店", "出发"]
        clean = []
        for w in found:
            # 自动扣掉地名中的“接”、“送”字样，解决“南昌接”这类问题
            w_fixed = w.replace("接", "").replace("送", "")
            if w_fixed not in stop_words and len(w_fixed) > 1:
                if w_fixed not in clean: clean.append(w_fixed)
        st.session_state['sites_final'] = " ".join(clean)

with m_right:
    st.markdown("### 2️⃣ 站点确认与自动测距")
    site_input = st.text_input("待搜索关键词：", value=st.session_state.get('sites_final', ""), label_visibility="collapsed")
    
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
            st.session_state['km_auto'] = km_val
            st.success(f"📍 测距成功: {km_val} KM (报价已在左侧同步生成)")
        except: st.error("地图路线获取失败")
