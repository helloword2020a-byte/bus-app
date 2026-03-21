import streamlit as st
import pandas as pd
import requests

# 页面基础配置
st.set_page_config(page_title="包车报价系统", layout="wide")
st.title("🚌 包车报价自动计算系统（终极精准版）")

# --- 高德 Key ---
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74" 

# --- 侧边栏：价格参数 ---
st.sidebar.header("单价/起步费调节")
p39 = st.sidebar.number_input("39座单价 (元/公里)", value=5.0)
p56 = st.sidebar.number_input("56座单价 (元/公里)", value=7.0)
b39 = st.sidebar.number_input("39座起步费 (元/天)", value=700)
b56 = st.sidebar.number_input("56座起步费 (元/天)", value=900)

# --- 主界面：行程输入 ---
st.info("💡 建议：输入地点时带上省份更精准。例如：'江西大觉山 江西葛仙村'")
route_input = st.text_input("请输入完整路线 (空格隔开)", placeholder="起点 途径点1 终点")

days = st.number_input("用车天数", min_value=1, value=1)

# --- 核心逻辑：精准算法 ---
auto_dist = 0

if route_input:
    locations = route_input.split()
    if len(locations) >= 2:
        try:
            # 1. 坐标获取（加入省份纠偏逻辑）
            def get_loc(addr):
                # 如果输入没带省份，尝试补全“江西”以提高省内定位精度
                search_addr = addr if "江西" in addr else f"江西{addr}"
                r = requests.get(f"https://restapi.amap.com/v3/geocode/geo?address={search_addr}&key={AMAP_KEY}").json()
                return r['geocodes'][0]['location']
            
            coords = [get_loc(loc) for loc in locations]
            
            # 2. 路径规划：strategy=2（距离优先）+ avoidpolygons（避开某些区域，促使走主干道）
            origin_coord = coords[0]
            destination_coord = coords[-1]
            waypoints = ";".join(coords[1:-1])
            
            # 强制使用 strategy=2，这在 API 中代表“距离优先”，最接近导航的“最短里程”
            url = f"https://restapi.amap.com/v3/direction/driving?origin={origin_coord}&destination={destination_coord}&key={AMAP_KEY}&strategy=2&extensions=base"
            if waypoints:
                url += f"&waypoints={waypoints}"
            
            route_r = requests.get(url).json()
            meters = int(route_r['route']['paths'][0]['distance'])
            auto_dist = int(round(meters / 1000))
            st.success(f"✅ 路线识别成功：{' ➡️ '.join(locations)}，全程共约 {auto_dist} 公里")
        except:
            st.warning("⚠️ 路径解析失败，请输入更具体的地点名称。")

# 最终里程确认 (支持根据导航截图手动输入)
final_km = st.number_input("确认计算公里数 (若与导航不符请手动修改)", value=int(auto_dist), step=1)

# --- 计算结果 ---
fee_39 = int(final_km * p39 + days * b39)
fee_56 = int(final_km * p56 + days * b56)

res_data = {
    "车型": ["39座", "56座"],
    "里程": [f"{final_km} KM", f"{final_km} KM"],
    "总报价": [f"{fee_39} 元", f"{fee_56} 元"]
}

st.table(pd.DataFrame(res_data))

# --- 微信文本 ---
wx_msg = f"【包车报价单】\n路线：{' - '.join(route_input.split())}\n全程：约{final_km}公里\n天数：{days}天\n---\n39座：{fee_39}元\n56座：{fee_56}元\n(报价含路桥费，不含食宿)"
st.text_area("复制报价文本：", wx_msg, height=150)
