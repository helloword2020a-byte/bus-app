import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="包车报价系统", layout="wide")
st.title("🚌 包车报价系统（带地点智能建议版）")

AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

# --- 侧边栏：单价设置 ---
st.sidebar.header("单价/起步费调节")
p39 = st.sidebar.number_input("39座单价", value=5.0)
p56 = st.sidebar.number_input("56座单价", value=7.0)
b39 = st.sidebar.number_input("39座起步费", value=700)
b56 = st.sidebar.number_input("56座起步费", value=900)

# --- 第一步：输入简写地点 ---
st.subheader("1️⃣ 快速录入路线")
raw_input = st.text_input("请输入地点简写（空格隔开）", "南昌 大觉山 葛仙村 婺源 景德镇 南昌")

# --- 第二步：智能搜索与精确选择 ---
st.subheader("2️⃣ 精确确认地点")
final_locations = []
if raw_input:
    names = raw_input.split()
    # 为每个输入的词找3个最匹配的地点
    for i, name in enumerate(names):
        try:
            # 调用高德搜索接口获取推荐点 (POI Search)
            search_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}&location="
            tips = requests.get(search_url).json()['tips']
            # 只取有坐标的有效地点
            options = [f"{t['name']} ({t['district']})" for t in tips if t['location']]
            if not options: options = [name]
            
            # 让用户从下拉框里选一个最准的
            chosen = st.selectbox(f"确认地点 {i+1}：关键字 [{name}]", options, key=f"sel_{i}")
            
            # 找到选中地点的坐标
            selected_tip = next(t for t in tips if f"{t['name']} ({t['district']})" == chosen)
            final_locations.append({"name": chosen, "coord": selected_tip['location']})
        except:
            st.error(f"找不到地点：{name}")

# --- 第三步：计算报价 ---
st.divider()
auto_dist = 0
if len(final_locations) >= 2:
    try:
        origin = final_locations[0]['coord']
        destination = final_locations[-1]['coord']
        waypts = ";".join([l['coord'] for l in final_locations[1:-1]])
        
        # 路径规划：strategy=2 距离优先
        route_url = f"https://restapi.amap.com/v3/direction/driving?origin={origin}&destination={destination}&key={AMAP_KEY}&strategy=2&waypoints={waypts}"
        route_res = requests.get(route_url).json()
        meters = int(route_res['route']['paths'][0]['distance'])
        auto_dist = int(round(meters / 1000))
        st.success(f"✅ 已串联 {len(final_locations)} 个精确地点，总里程约：{auto_dist} 公里")
    except:
        st.info("正在等待地点确认...")

final_km = st.number_input("最终公里数微调", value=int(auto_dist))
days = st.number_input("用车天数", min_value=1, value=1)

# 计算报价
fee_39 = int(final_km * p39 + days * b39)
fee_56 = int(final_km * p56 + days * b56)

st.table(pd.DataFrame({
    "车型": ["39座", "56座"],
    "里程": [f"{final_km}KM"] * 2,
    "总价": [f"{fee_39}元", f"{fee_56}元"]
}))

# 微信文本
route_str = " - ".join([l['name'].split('(')[0] for l in final_locations])
wx_msg = f"【包车报价单】\n路线：{route_str}\n全程：{final_km}公里\n天数：{days}天\n---\n39座：{fee_39}元\n56座：{fee_56}元\n(含路桥费，不含司机食宿)"
st.text_area("复制报价：", wx_msg)
