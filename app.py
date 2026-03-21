import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="包车报价系统", layout="wide")
st.title("🚌 包车报价系统（路径纠偏版）")

AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74" 

# --- 侧边栏：价格参数 ---
st.sidebar.header("单价/起步费调节")
p39 = st.sidebar.number_input("39座单价 (元/公里)", value=5.0)
p56 = st.sidebar.number_input("56座单价 (元/公里)", value=7.0)
b39 = st.sidebar.number_input("39座起步费 (元/天)", value=700)
b56 = st.sidebar.number_input("56座起步费 (元/天)", value=900)

# --- 第一步：输入简写地点 ---
st.subheader("1️⃣ 输入路线关键词")
raw_input = st.text_input("请输入地点（空格分隔）", value="南昌 大觉山 葛仙村 篁岭 景德镇 南昌")

# --- 第二步：智能搜索与精确选择 ---
st.subheader("2️⃣ 确认精确位置")
final_locations = []

if raw_input:
    names = raw_input.split()
    cols = st.columns(len(names))
    
    for i, name in enumerate(names):
        with cols[i]:
            try:
                # 获取候选列表
                search_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
                tips_res = requests.get(search_url).json()
                tips = tips_res.get('tips', [])
                
                # 过滤出有明确名称和坐标的选项
                options = [f"{t['name']} ({t.get('district', '')})" for t in tips if t.get('name') and t.get('location')]
                
                if not options:
                    options = [f"{name} (请检查输入)"]
                
                chosen = st.selectbox(f"第{i+1}站", options, key=f"sel_{i}")
                
                # 获取坐标
                actual_name = chosen.split(" (")[0]
                loc_data = next((t.get('location') for t in tips if t['name'] == actual_name and t.get('location')), None)
                
                # 二次查询坐标补丁
                if not loc_data:
                    geo_url = f"https://restapi.amap.com/v3/geocode/geo?address={chosen}&key={AMAP_KEY}"
                    geo_res = requests.get(geo_url).json()
                    if geo_res.get('geocodes'):
                        loc_data = geo_res['geocodes'][0]['location']
                
                if loc_data:
                    final_locations.append({"name": actual_name, "coord": loc_data})
            except:
                pass

# --- 第三步：路径规划与纠偏 ---
st.divider()
auto_dist = 0

if len(final_locations) == len(raw_input.split()) and len(final_locations) >= 2:
    try:
        # 严格按照顺序提取坐标
        origin = final_locations[0]['coord']
        destination = final_locations[-1]['coord']
        waypts = ";".join([l['coord'] for l in final_locations[1:-1]])
        
        # 改进策略：strategy=2 (距离优先，尽量走直线/最短)
        route_url = f"https://restapi.amap.com/v3/direction/driving?origin={origin}&destination={destination}&key={AMAP_KEY}&strategy=2"
        if waypts:
            route_url += f"&waypoints={waypts}"
            
        route_res = requests.get(route_url).json()
        if route_res['status'] == '1':
            meters = int(route_res['route']['paths'][0]['distance'])
            auto_dist = int(round(meters / 1000))
            
            # 路线逻辑检查：显示完整线路顺序
            route_flow = " ➡️ ".join([l['name'] for l in final_locations])
            st.info(f"📍 规划线路：{route_flow}")
            st.success(f"✅ 测算里程：{auto_dist} 公里")
        else:
            st.error(f"高德接口返回错误：{route_res.get('info')}")
    except Exception as e:
        st.error(f"里程计算中断，请检查地点是否选择正确")
else:
    st.warning("⚠️ 请确保上方每个下拉框都已选定具体的地点，目前正在等待选点...")

# --- 第四步：报价与输出 ---
c1, c2 = st.columns(2)
with c1:
    final_km = st.number_input("最终确认公里数", value=int(auto_dist), step=1)
with c2:
    days = st.number_input("用车天数", min_value=1, value=1, step=1)

fee_39 = int(final_km * p39 + days * b39)
fee_56 = int(final_km * p56 + days * b56)

st.table(pd.DataFrame({
    "车型": ["39座", "56座"],
    "里程": [f"{final_km} KM"] * 2,
    "总报价": [f"{fee_39} 元", f"{fee_56} 元"]
}))

# 复制文本
if final_locations:
    route_display = " - ".join([l['name'] for l in final_locations])
    wx_msg = f"【包车报价单】\n路线：{route_display}\n路程：约{final_km}公里\n天数：{days}天\n---\n39座：{fee_39}元\n56座：{fee_56}元\n(报价含路桥费，不含司机食宿)"
    st.text_area("点击下方框内全选复制：", wx_msg, height=150)
