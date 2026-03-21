import streamlit as st
import pandas as pd
import requests

# 页面基础配置
st.set_page_config(page_title="包车报价系统", layout="wide")
st.title("🚌 包车报价自动计算系统（精准取整版）")

# --- 高德 Key (已填入你的 Key) ---
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74" 

# --- 侧边栏：价格参数 ---
st.sidebar.header("单价/起步费调节")
p39 = st.sidebar.number_input("39座单价 (元/公里)", value=5.0)
p56 = st.sidebar.number_input("56座单价 (元/公里)", value=7.0)
b39 = st.sidebar.number_input("39座起步费 (元/天)", value=700)
b56 = st.sidebar.number_input("56座起步费 (元/天)", value=900)

# --- 主界面：行程输入 ---
st.info("💡 提示：输入多个地点请用【空格】隔开。例如：'南昌 大觉山 葛仙村 婺源 南昌'")
route_input = st.text_input("请输入完整路线", placeholder="起点 途径点1 途径点2 终点")

days = st.number_input("用车天数", min_value=1, value=1)

# --- 核心逻辑：高德 API 请求 ---
auto_dist = 0

if route_input:
    locations = route_input.split()
    if len(locations) >= 2:
        try:
            # 1. 地名转坐标函数
            def get_loc(addr):
                r = requests.get(f"https://restapi.amap.com/v3/geocode/geo?address={addr}&key={AMAP_KEY}").json()
                return r['geocodes'][0]['location']
            
            coords = [get_loc(loc) for loc in locations]
            
            # 2. 规划路径 (加入 strategy=2 距离优先策略)
            origin_coord = coords[0]
            destination_coord = coords[-1]
            waypoints = ";".join(coords[1:-1])
            
            # 策略参数说明：strategy=2 为距离优先
            url = f"https://restapi.amap.com/v3/direction/driving?origin={origin_coord}&destination={destination_coord}&key={AMAP_KEY}&strategy=2"
            if waypoints:
                url += f"&waypoints={waypoints}"
            
            route_r = requests.get(url).json()
            # 获取总里程（米），转为公里并取整
            meters = int(route_r['route']['paths'][0]['distance'])
            auto_dist = int(round(meters / 1000)) 
            st.success(f"✅ 路线识别成功：{' ➡️ '.join(locations)}，全程共约 {auto_dist} 公里")
        except:
            st.warning("⚠️ 路径解析失败，请检查地名是否准确或加具体省市（如：江西大觉山）。")
    else:
        st.warning("ℹ️ 请至少输入起点和终点两个位置。")

# 最终里程确认 (用户可根据实际导航微调)
final_km = st.number_input("计算公里数 (可参考手机导航手动微调)", value=int(auto_dist), step=1)

# --- 计算逻辑 (强制整数) ---
fee_39 = int(final_km * p39 + days * b39)
fee_56 = int(final_km * p56 + days * b56)

res_data = {
    "车型": ["39座", "56座"],
    "里程": [f"{final_km} KM", f"{final_km} KM"],
    "计算总价": [f"{fee_39} 元", f"{fee_56} 元"]
}

st.subheader("📋 实时报价明细")
st.table(pd.DataFrame(res_data))

# --- 微信报价文本导出 ---
st.subheader("🔗 微信报价一键复制")
route_display = " - ".join(route_input.split())
wx_msg = f"【包车报价单】\n路线：{route_display}\n路程：约{final_km}公里\n天数：{days}天\n---\n39座报价：{fee_39}元\n56座报价：{fee_56}元\n(备注：此报价包含油费、路桥费，不含司机食宿)"
st.text_area("直接长按下方文字即可复制：", wx_msg, height=160)
