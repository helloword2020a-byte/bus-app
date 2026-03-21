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

# 压缩顶部空白
st.markdown("<style> .main .block-container{padding-top: 1rem; padding-bottom: 1rem;} </style>", unsafe_allow_html=True)

# --- 2. 核心功能 ---
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

# --- 3. 侧边栏：运价配置 ---
with st.sidebar:
    st.header("⚙️ 报价标准配置")
    st.subheader("39座大巴")
    base_39 = st.number_input("起步费(元/天)", value=800, key="b39")
    price_39 = st.number_input("超公里单价(元/KM)", value=2.6, step=0.1, key="p39")
    st.divider()
    st.subheader("56座大巴")
    base_56 = st.number_input("起步费(元/天) ", value=1000, key="b56")
    price_56 = st.number_input("超公里单价(元/KM) ", value=3.6, step=0.1, key="p56")
    st.caption("注：总价 = (公里数×单价) + (天数×起步)")

# --- 4. 主界面：左右布局 ---
st.title("🚌 九江祥隆旅游运输报价系统")

m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.subheader("1️⃣ 行程识别")
    up_file = st.file_uploader("粘贴/上传行程单", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
    if up_file:
        img_bytes = up_file.read()
        st.image(img_bytes, use_column_width=True)
        if st.button("🚀 开始文字识别", use_container_width=True):
            st.session_state['ocr_raw'] = ocr_smart_engine(img_bytes)
    
    text_edit = st.text_area("识别结果校对：", value=st.session_state.get('ocr_raw', ""), height=150)
    
    # 修改：不再限制江西，改为全国通用的关键词提取
    if st.button("✨ 智能提取行程地名", use_container_width=True):
        raw = text_edit
        # 清洗掉干扰词
        noise = [r"第\d+天", r"行程", r"简易", r"车程约?[\d\.h小时]+", r"住[^\s，。]*", r"前往", r"接引", r"返程", r"结束", r"含早", r"下午", r"上午", r"接$", r"送$"]
        for p in noise: raw = re.sub(p, " ", raw)
        found = re.findall(r'[\u4e00-\u9fa5]{2,6}', raw)
        stop_words = ["可以", "需要", "提示", "进行", "返回", "地点", "时间", "到达", "游览", "早餐", "晚餐"]
        seen = set()
        clean_sites = [w for w in found if w not in stop_words and len(w) > 1 and not (w in seen or seen.add(w))]
        st.session_state['sites_final'] = " ".join(clean_sites)

with m_right:
    st.subheader("2️⃣ 站点与报价")
    site_str = st.text_input("识别出的关键词（空格分隔）：", value=st.session_state.get('sites_final', ""), label_visibility="collapsed")
    
    loc_data = []
    if site_str:
        names = site_str.split()
        grid = st.columns(2)
        for i, name in enumerate(names):
            with grid[i % 2]:
                # 修改：移除 &city=江西，实现全国搜索
                search_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
                try:
                    tips = requests.get(search_url).json().get('tips', [])
                    opts = [f"{t['name']} ({t.get('district','')})" for t in tips if t.get('location')]
                    
                    sel = st.selectbox(f"站点{i+1}: {name}", opts or [f"{name}(未搜到)"], key=f"site_{i}")
                    coord = next((t['location'] for t in tips if t['name'] == sel.split(" (")[0]), None)
                    if coord: loc_data.append(coord)
                except: st.error(f"{name} 搜索超时")

    if len(loc_data) >= 2:
        try:
            # 计算全国路径
            org, des, way = loc_data[0], loc_data[-1], ";".join(loc_data[1:-1])
            r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way}"
            res = requests.get(r_url).json()
            km = int(round(int(res['route']['paths'][0]['distance']) / 1000))
            
            st.divider()
            c1, c2 = st.columns(2)
            f_km = c1.number_input("实测公里 (KM)", value=km)
            days = c2.number_input("用车天数 (天)", value=4, min_value=1)
            
            p39 = int(f_km * price_39 + days * base_39)
            p56 = int(f_km * price_56 + days * base_56)
            
            # 紧凑结果展示
            st.dataframe(pd.DataFrame({
                "车型": ["39座大巴", "56座大巴"], 
                "报价": [f"{p39} 元", f"{p56} 元"],
                "计算详情": [f"{f_km}KM × {price_39} + {days}天 × {base_39}", 
                           f"{f_km}KM × {price_56} + {days}天 × {base_56}"]
            }), use_container_width=True, hide_index=True)
            
            st.success(f"📍 路径已生成，总计覆盖 {len(loc_data)} 个站点。")
        except: st.warning("请校对以上站点名，确保所有站点都匹配到了具体位置。")
