import streamlit as st
import pandas as pd
import requests

# 页面基础配置
st.set_page_config(page_title="包车报价系统", layout="wide")
st.title("🚌 包车报价自动计算系统（多点+整数版）")

# --- 高德 Key ---
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74" 

# --- 侧边栏：价格参数 ---
st.sidebar.header("单价/起步费调节")
p39 = st.sidebar.number_input("39座单价 (元/公里)", value=5.0)
p56 = st.sidebar.number_input("56座单价 (元/公里)", value=7.0)
b39 = st.sidebar.number_input("39座起步费 (元/天)", value=700)
b56 = st.sidebar.number_input("56座起步费 (元/天)", value=900)

# --- 主界面：多行程输入 ---
st.info("💡 提示：输入多个地点请用【空格】隔开。例如：'九江 共青城 南昌'")
route_input = st.text_input("请输入完整路线 (起点 途径点1 终点)", placeholder="例如：九江 共青城 南昌")

days = st.number_input("用车天数", min_value=1, value=1)

# --- 核心逻辑：计算多点总里程 ---
auto_dist = 0

if route_input:
    locations = route_input.split()
    if len(locations) >= 2:
        try:
            # 1. 将所有地名转为坐标
            def get_loc(addr):
                r = requests.get(f"https://restapi.amap.com/v3/geocode/geo?address={addr}&key={AMAP_KEY}").json()
                return r['geocodes'][0]['location']
            
            coords = [get_loc(loc) for loc in locations]
            
            # 2. 规划路径
            origin_coord = coords[0]
            destination_coord = coords[-1]
            waypoints = ";".join(coords[1:-1])
            
            url = f"https://restapi.amap.com/v3/direction/driving?origin={origin_coord}&destination={destination_coord}&key={AMAP_KEY}"
            if waypoints:
                url += f"&waypoints={waypoints}"
            
            route_r = requests.get(url).json()
            meters = int(route_r['route']['paths'][0]['distance'])
            auto_dist = int(round(meters / 1000)) # 转换为整数公里
            st.success(f"✅ 路线识别成功：{' ➡️ '.join(locations)}，全程共 {auto_dist} 公里")
        except:
            st.warning("⚠️ 路径解析失败，请检查地名。")
    else:
        st.warning("ℹ️ 请至少输入两个地点。")

# 确认最终公里数 (确保是整数)
final_km = st.number_input("计算公里数 (可微调)", value=int(auto_dist), step=1)

# --- 计算与展示 (全部转换为整数) ---
fee_39 = int(final_km * p39 + days * b39)
fee_56 = int(final_km * p56 + days * b56)

res_data = {
    "车型": ["39座", "56座"],
    "里程": [f"{final_km} KM", f"{final_km} KM"],
    "计算总价": [f"{fee_39} 元", f"{fee_56} 元"]
}

st.subheader("📋 实时报价明细")
st.table(pd.DataFrame(res_data))

# --- 微信报价文本 ---
st.subheader("🔗 微信报价一键复制")
route_display = " - ".join(route_input.split())
wx_msg = f"【包车报价单】\n路线：{route_display}\n路程：约{final_km}公里\n天数：{days}天\n---\n39座报价：{fee_39}元\n56座报价：{fee_56}元\n(报价包含油费及路桥费)"
st.text_area("直接长按下方框内文字即可复制：", wx_msg, height=160)
