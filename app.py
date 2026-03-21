import streamlit as st
import pandas as pd
import requests

# 页面基础配置
st.set_page_config(page_title="包车报价系统", layout="wide")
st.title("🚌 包车报价系统（布局+单价优化版）")

# --- 高德 Key ---
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74" 

# --- 侧边栏：价格参数 (已更新默认值) ---
st.sidebar.header("单价/起步费调节")
p39 = st.sidebar.number_input("39座单价 (元/公里)", value=2.6)
p56 = st.sidebar.number_input("56座单价 (元/公里)", value=3.6)
b39 = st.sidebar.number_input("39座起步费 (元/天)", value=800)
b56 = st.sidebar.number_input("56座起步费 (元/天)", value=1000)

# --- 第一步：输入简写地点 ---
st.subheader("1️⃣ 输入路线关键词")
st.info("💡 提示：输入地点简写并用【空格】隔开。例如：'南昌 大觉山 葛仙村'")
raw_input = st.text_input("请输入地点关键词（空格分隔）", value="南昌昌北国际机场 大觉山风景区 葛仙村度假区 婺源篁岭景区 江西省景德镇市 南昌昌北国际机场")

# --- 第二步：精确选点（已改为竖向布局） ---
st.subheader("2️⃣ 确认精确位置")
final_locations = []

if raw_input:
    names = raw_input.split()
    
    # 使用 st.container() 和 st.selectbox 让下拉框竖着排列
    for i, name in enumerate(names):
        try:
            # 1. 搜索提示列表
            search_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
            tips_res = requests.get(search_url).json()
            tips = tips_res.get('tips', [])
            
            # 2. 整理带有完整地名的选项
            options = []
            for t in tips:
                if t.get('name') and t.get('district') and t.get('location'):
                    options.append(f"{t['name']} ({t['district']})")
                elif t.get('name') and t.get('location'): # 即使没有 district 也先列出来
                    options.append(f"{t['name']}")

            # 如果没找到，提示用户
            if not options:
                options = [f"{name} (未搜索到精确点，程序将尝试使用地理编码)"]
            
            # 3. 创建竖向排列的选择框
            st.divider() if i > 0 else None # 加一条分割线清晰显示每一站
            st.markdown(f"**📍 第 {i+1} 站：关键字 [{name}]**")
            chosen = st.selectbox("请在下方列表中点选一个最精确的位置：", options, key=f"sel_{i}")
            
            # 4. 获取坐标
            actual_name = chosen.split(" (")[0]
            loc_data = next((t.get('location') for t in tips if t['name'] == actual_name and t.get('location')), None)
            
            # 补丁：如果输入提示里没坐标，强制查一次地理编码
            if not loc_data:
                geo_url = f"https://restapi.amap.com/v3/geocode/geo?address={chosen}&key={AMAP_KEY}"
                geo_res = requests.get(geo_url).json()
                if geo_res.get('geocodes'):
                    loc_data = geo_res['geocodes'][0]['location']
            
            if loc_data:
                final_locations.append({"name": actual_name, "coord": loc_data})
            
        except Exception as e:
            pass

# --- 第三步：路径测算 ---
st.divider()
auto_dist = 0

if len(final_locations) == len(raw_input.split()) and len(final_locations) >= 2:
    try:
        origin = final_locations[0]['coord']
        destination = final_locations[-1]['coord']
        waypts = ";".join([l['coord'] for l in final_locations[1:-1]])
        
        # strategy=2 距离优先
        route_url = f"https://restapi.amap.com/v3/direction/driving?origin={origin_coord}&destination={destination_coord}&key={AMAP_KEY}&strategy=2"
        if waypts:
            route_url += f"&waypoints={waypoints}"
            
        route_res = requests.get(route_url).json()
        if route_res['status'] == '1':
            meters = int(route_res['route']['paths'][0]['distance'])
            auto_dist = int(round(meters / 1000))
            st.success(f"✅ 测算里程：全程约 {auto_dist} 公里")
        else:
            st.error(f"高德路径规划报错：{route_res.get('info')}")
    except:
        st.error(f"里程计算失败")
else:
    st.info("💡 请确保上方所有地点已选定坐标。")

# --- 第四步：输出与微调 ---
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
    wx_msg = f"【包车报价单】\n路线：{route_display}\n全程：{final_km}公里\n天数：{days}天\n---\n39座报价：{fee_39}元\n56座报价：{fee_56}元\n(报价包含油费、路桥费，不含司机食宿)"
    st.text_area("全选框内文本复制：", wx_msg, height=150)
