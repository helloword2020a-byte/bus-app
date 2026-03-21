import streamlit as st
import pandas as pd
import requests

# 页面基础配置
st.set_page_config(page_title="包车报价系统", layout="wide")
st.title("🚌 包车报价自动计算系统")

# --- 【关键：已为你填入截图中的高德 Key】 ---
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74" 

# --- 侧边栏：价格微调 ---
st.sidebar.header("单价/起步费调节")
p39 = st.sidebar.number_input("39座单价 (元/公里)", value=5.0)
p56 = st.sidebar.number_input("56座单价 (元/公里)", value=7.0)
b39 = st.sidebar.number_input("39座起步费 (元/天)", value=700)
b56 = st.sidebar.number_input("56座起步费 (元/天)", value=900)

# --- 主界面：行程输入 ---
col1, col2 = st.columns(2)
with col1:
    origin = st.text_input("出发地点", placeholder="例如：广州南站")
with col2:
    destination = st.text_input("到达地点", placeholder="例如：衡阳火车站")

days = st.number_input("用车天数", min_value=1, value=1)

# --- 核心逻辑：高德自动算路程 ---
auto_dist = 0.0

if origin and destination:
    try:
        # 1. 获取坐标
        def get_loc(addr):
            r = requests.get(f"https://restapi.amap.com/v3/geocode/geo?address={addr}&key={AMAP_KEY}").json()
            return r['geocodes'][0]['location']
        
        # 2. 计算驾车路程
        s_loc = get_loc(origin)
        e_loc = get_loc(destination)
        route = requests.get(f"https://restapi.amap.com/v3/direction/driving?origin={s_loc}&destination={e_loc}&key={AMAP_KEY}").json()
        
        # 米转公里并取整
        meters = int(route['route']['paths'][0]['distance'])
        auto_dist = round(meters / 1000)
        st.success(f"✅ 识别路程：{auto_dist} 公里")
    except:
        st.warning("⚠️ 自动识别失败，请检查地点名称是否准确。")

# 确认最终公里数 (支持手动修改)
final_km = st.number_input("计算公里数 (可手动微调)", value=float(auto_dist))

# --- 报价展示 ---
res_data = {
    "车型": ["39座", "56座"],
    "里程": [f"{final_km} KM", f"{final_km} KM"],
    "计算总价": [
        round(final_km * p39 + days * b39, 2),
        round(final_km * p56 + days * b56, 2)
    ]
}

st.subheader("📋 实时报价明细")
st.table(pd.DataFrame(res_data))

# --- 微信报价文本 ---
st.subheader("🔗 微信报价一键复制")
wx_msg = f"【包车报价单】\n路线：{origin} - {destination}\n路程：约{final_km}公里\n天数：{days}天\n---\n39座：{res_data['计算总价'][0]}元\n56座：{res_data['计算总价'][1]}元\n(报价包含油费及路桥费)"
st.text_area("直接长按下方框内文字即可复制：", wx_msg, height=160)
