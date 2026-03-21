import streamlit as st
import pandas as pd
import requests

# 页面基础配置
st.set_page_config(page_title="包车报价系统", layout="wide")
st.title("🚌 包车报价自动计算系统（快捷预设版）")

# --- 高德 Key ---
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74" 

# --- 侧边栏：价格参数 ---
st.sidebar.header("单价/起步费调节")
p39 = st.sidebar.number_input("39座单价 (元/公里)", value=5.0)
p56 = st.sidebar.number_input("56座单价 (元/公里)", value=7.0)
b39 = st.sidebar.number_input("39座起步费 (元/天)", value=700)
b56 = st.sidebar.number_input("56座起步费 (元/天)", value=900)

# --- 新功能：常用路线预设 ---
st.subheader("📍 常用路线一键填入")
# 您可以在这里添加更多常用路线，格式为： "显示名称": "详细地点（空格隔开）"
preset_routes = {
    "自定义输入": "",
    "经典环线 (南昌-大觉山-葛仙村-篁岭-景德镇-南昌)": "江西省南昌市 大觉山风景区 葛仙村度假区 婺源篁岭景区 江西省景德镇市 江西省南昌市",
    "九江周边 (九江-庐山-东林寺-九江)": "九江市 庐山风景名胜区 东林寺 九江市",
    "省际长途 (九江-武汉-九江)": "九江市 武汉市 黄鹤楼 九江市"
}

selected_preset = st.selectbox("选择预设路线（选择后下方会自动填充）：", list(preset_routes.keys()))

# --- 主界面：行程输入 ---
# 如果选择了预设，则自动填充输入框
default_input = preset_routes[selected_preset]
route_input = st.text_input("当前路线详情 (可手动修改或补充)", value=default_input)

days = st.number_input("用车天数", min_value=1, value=1)

# --- 核心逻辑：精准算法 ---
auto_dist = 0

if route_input:
    locations = route_input.split()
    if len(locations) >= 2:
        try:
            def get_loc(addr):
                search_addr = addr if "江西" in addr else f"江西{addr}"
                r = requests.get(f"https://restapi.amap.com/v3/geocode/geo?address={search_addr}&key={AMAP_KEY}").json()
                return r['geocodes'][0]['location']
            
            coords = [get_loc(loc) for loc in locations]
            origin_coord = coords[0]
            destination_coord = coords[-1]
            waypoints = ";".join(coords[1:-1])
            
            # strategy=2 距离优先
            url = f"https://restapi.amap.com/v3/direction/driving?origin={origin_coord}&destination={destination_coord}&key={AMAP_KEY}&strategy=2"
            if waypoints:
                url += f"&waypoints={waypoints}"
            
            route_r = requests.get(url).json()
            meters = int(route_r['route']['paths'][0]['distance'])
            auto_dist = int(round(meters / 1000))
            st.success(f"✅ 路线加载成功，全程共约 {auto_dist} 公里")
        except:
            st.warning("⚠️ 路径解析中，请确保地点正确。")

# 最终里程确认
final_km = st.number_input("确认计算公里数 (可微调)", value=int(auto_dist), step=1)

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
wx_msg = f"【包车报价单】\n路线：{' - '.join(route_input.split())}\n全程：约{final_km}公里\n天数：{days}天\n---\n39座报价：{fee_39}元\n56座报价：{fee_56}元\n(报价含路桥费，不含司机食宿)"
st.text_area("复制报价文本：", wx_msg, height=150)
