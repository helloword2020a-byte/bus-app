import streamlit as st
import pandas as pd
import requests

# 页面基础配置
st.set_page_config(page_title="包车报价系统", layout="wide")
st.title("🚌 包车报价系统（紧凑版）")

# --- 高德 Key ---
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74" 

# --- 侧边栏：价格参数 ---
st.sidebar.header("单价/起步费调节")
p39 = st.sidebar.number_input("39座单价 (元/公里)", value=2.6)
p56 = st.sidebar.number_input("56座单价 (元/公里)", value=3.6)
b39 = st.sidebar.number_input("39座起步费 (元/天)", value=800)
b56 = st.sidebar.number_input("56座起步费 (元/天)", value=1000)

# --- 第一步：输入简写地点 ---
st.subheader("1️⃣ 输入路线关键词")
raw_input = st.text_input("地点间用空格分隔", value="南昌昌北国际机场 大觉山 葛仙村 篁岭 景德镇 南昌昌北国际机场")

# --- 第二步：确认精确位置（紧凑布局） ---
st.subheader("2️⃣ 确认精确位置")
final_locations = []

if raw_input:
    names = raw_input.split()
    # 遍历每个输入的地点名
    for i, name in enumerate(names):
        try:
            # 搜索建议
            search_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
            tips_res = requests.get(search_url).json()
            tips = tips_res.get('tips', [])
            
            options = []
            for t in tips:
                if t.get('name') and t.get('location'):
                    dist = t.get('district', '')
                    options.append(f"{t['name']} ({dist})")

            if not options:
                options = [f"{name} (未搜索到精确点)"]
            
            # 使用更紧凑的显示方式：取消 divider，合并文字
            chosen = st.selectbox(f"📍 第{i+1}站 [{name}] 精确点确认：", options, key=f"sel_{i}")
            
            # 解析坐标
            actual_name = chosen.split(" (")[0]
            loc_data = next((t.get('location') for t in tips if t['name'] == actual_name and t.get('location')), None)
            
            if not loc_data:
                geo_url = f"https://restapi.amap.com/v3/geocode/geo?address={chosen}&key={AMAP_KEY}"
                geo_res = requests.get(geo_url).json()
                if geo_res.get('geocodes'):
                    loc_data = geo_res['geocodes'][0]['location']
            
            if loc_data:
                final_locations.append({"name": actual_name, "coord": loc_data})
        except:
            pass

# --- 第三步：路径规划 ---
st.divider()
auto_dist = 0

if len(final_locations) == len(raw_input.split()) and len(final_locations) >= 2:
    try:
        origin_coord = final_locations[0]['coord']
        destination_coord = final_locations[-1]['coord']
        waypoints = ";".join([l['coord'] for l in final_locations[1:-1]])
        
        # strategy=2 距离优先
        route_url = f"https://restapi.amap.com/v3/direction/driving?origin={origin_coord}&destination={destination_coord}&key={AMAP_KEY}&strategy=2"
        if waypoints:
            route_url += f"&waypoints={waypoints}"
            
        route_res = requests.get(route_url).json()
        if route_res['status'] == '1':
            meters = int(route_res['route']['paths'][0]['distance'])
            auto_dist = int(round(meters / 1000))
            
            # 显示纠偏线路
            route_flow = " ➡️ ".join([l['name'] for l in final_locations])
            st.info(f"🗺️ 线路：{route_flow}")
            st.success(f"✅ 测算：{auto_dist} KM")
    except:
        st.error("里程计算中断")
else:
    st.warning("⏳ 请在上方下拉框确认每个地点的具体位置")

# --- 第四步：报价 ---
col1, col2 = st.columns(2)
with col1:
    final_km = st.number_input("里程修正", value=int(auto_dist), step=1)
with col2:
    days = st.number_input("天数", min_value=1, value=1, step=1)

f39 = int(final_km * p39 + days * b39)
f56 = int(final_km * p56 + days * b56)

st.table(pd.DataFrame({
    "车型": ["39座", "56座"],
    "里程": [f"{final_km} KM"] * 2,
    "总报价": [f"{f39} 元", f"{f56} 元"]
}))

# 复制区域
if final_locations:
    route_str = " - ".join([l['name'] for l in final_locations])
    msg = f"【包车报价单】\n路线：{route_str}\n里程：约{final_km}公里\n天数：{days}天\n---\n39座报价：{f39}元\n56座报价：{f56}元\n(报价含路桥费，不含司机食宿)"
    st.text_area("复制报价文本：", msg, height=130)
