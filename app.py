import streamlit as st
import pandas as pd
import requests

# 页面基础配置
st.set_page_config(page_title="包车报价系统", layout="wide")
st.title("🚌 包车报价系统（布局+单价优化版）")

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
raw_input = st.text_input("请输入地点关键词（空格分隔）", value="南昌昌北国际机场 大觉山 葛仙村 篁岭 景德镇 南昌昌北国际机场")

# --- 第二步：确认精确位置（竖向布局修复版） ---
st.subheader("2️⃣ 确认精确位置")
final_locations = []

if raw_input:
    names = raw_input.split()
    
    for i, name in enumerate(names):
        # 修复：不再使用 inline if 打印，改为标准判断
        if i > 0:
            st.divider()
            
        try:
            # 获取搜索建议
            search_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
            tips_res = requests.get(search_url).json()
            tips = tips_res.get('tips', [])
            
            # 提取有效选项
            options = []
            for t in tips:
                if t.get('name') and t.get('location'):
                    dist = t.get('district', '')
                    options.append(f"{t['name']} ({dist})")

            if not options:
                options = [f"{name} (未搜索到精确点)"]
            
            st.markdown(f"**📍 第 {i+1} 站：关键词 [{name}]**")
            # 渲染选择框
            chosen = st.selectbox(f"请点选精确位置（对应第{i+1}站）：", options, key=f"sel_{i}")
            
            # 解析坐标
            actual_name = chosen.split(" (")[0]
            loc_data = next((t.get('location') for t in tips if t['name'] == actual_name and t.get('location')), None)
            
            # 补丁：地理编码
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
        
        # strategy=2 距离优先（最短路径）
        route_url = f"https://restapi.amap.com/v3/direction/driving?origin={origin_coord}&destination={destination_coord}&key={AMAP_KEY}&strategy=2"
        if waypoints:
            route_url += f"&waypoints={waypoints}"
            
        route_res = requests.get(route_url).json()
        if route_res['status'] == '1':
            meters = int(route_res['route']['paths'][0]['distance'])
            auto_dist = int(round(meters / 1000))
            
            # 显示规划路线详情，方便纠错
            route_flow = " ➡️ ".join([l['name'] for l in final_locations])
            st.info(f"🗺️ 规划线路：{route_flow}")
            st.success(f"✅ 测算里程：{auto_dist} 公里")
        else:
            st.error(f"高德 API 报错：{route_res.get('info')}")
    except:
        st.error("计算公里数时发生错误")
else:
    st.warning("⏳ 请确保上方所有地点的下拉框都已手动点选确认。")

# --- 第四步：最终报价 ---
col1, col2 = st.columns(2)
with col1:
    final_km = st.number_input("最终里程确认 (KM)", value=int(auto_dist), step=1)
with col2:
    days = st.number_input("用车天数 (天)", min_value=1, value=1, step=1)

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
    msg = f"【包车报价单】\n路线：{route_str}\n里程：约{final_km}公里\n天数：{days}天\n---\n39座：{f39}元\n56座：{f56}元\n(报价含路桥费，不含司机食宿)"
    st.text_area("复制下方文本：", msg, height=150)
