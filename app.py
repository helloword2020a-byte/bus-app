import streamlit as st
import pandas as pd
import requests

# 页面基础配置
st.set_page_config(page_title="包车报价系统", layout="wide")
st.title("🚌 包车报价系统（智能选点+精准取整版）")

# --- 高德 Key ---
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74" 

# --- 侧边栏：价格参数 ---
st.sidebar.header("单价/起步费调节")
p39 = st.sidebar.number_input("39座单价 (元/公里)", value=5.0)
p56 = st.sidebar.number_input("56座单价 (元/公里)", value=7.0)
b39 = st.sidebar.number_input("39座起步费 (元/天)", value=700)
b56 = st.sidebar.number_input("56座起步费 (元/天)", value=900)

# --- 第一步：输入简写地点 ---
st.subheader("1️⃣ 输入路线关键词")
st.info("💡 提示：输入地点简写并用【空格】隔开。例如：'南昌 大觉山 葛仙村 婺源 景德镇 南昌'")
raw_input = st.text_input("请输入地点（空格分隔）", value="南昌 大觉山 葛仙村 篁岭 景德镇 南昌")

# --- 第二步：智能搜索与精确选择 ---
st.subheader("2️⃣ 确认精确位置")
final_locations = []

if raw_input:
    names = raw_input.split()
    # 为每个输入的词创建下拉选择框
    cols = st.columns(len(names))
    
    for i, name in enumerate(names):
        with cols[i]:
            try:
                # 调用高德输入提示接口
                search_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
                r = requests.get(search_url).json()
                tips = r.get('tips', [])
                
                # 过滤出有坐标的有效地点
                options = [f"{t['name']} ({t.get('district', '')})" for t in tips if t.get('location')]
                
                if not options:
                    options = [f"{name} (未找到精确位置)"]
                    st.warning(f"找不到 {name}")
                
                # 用户选择精确点
                chosen = st.selectbox(f"确认第{i+1}站", options, key=f"sel_{i}")
                
                # 获取选中点的坐标
                if "(" in chosen:
                    actual_name = chosen.split(" (")[0]
                    selected_tip = next(t for t in tips if t['name'] == actual_name)
                    final_locations.append({"name": actual_name, "coord": selected_tip['location']})
            except Exception as e:
                st.error(f"搜索 {name} 出错")

# --- 第三步：路径规划与计算 ---
st.divider()
auto_dist = 0

if len(final_locations) >= 2:
    try:
        origin = final_locations[0]['coord']
        destination = final_locations[-1]['coord']
        # 途径点用分号隔开
        waypts = ";".join([l['coord'] for l in final_locations[1:-1]])
        
        # 策略 2：距离优先（最短路径）
        route_url = f"https://restapi.amap.com/v3/direction/driving?origin={origin}&destination={destination}&key={AMAP_KEY}&strategy=2"
        if waypts:
            route_url += f"&waypoints={waypts}"
            
        route_res = requests.get(route_url).json()
        meters = int(route_res['route']['paths'][0]['distance'])
        auto_dist = int(round(meters / 1000))
        st.success(f"✅ 已串联 {len(final_locations)} 个点，总里程约：{auto_dist} 公里")
    except:
        st.info("请确认上方所有地点已选定")

# 公里数确认与天数设置
c1, c2 = st.columns(2)
with c1:
    final_km = st.number_input("最终公里数 (可手动微调)", value=int(auto_dist), step=1)
with c2:
    days = st.number_input("用车天数", min_value=1, value=1, step=1)

# --- 报价展示 ---
fee_39 = int(final_km * p39 + days * b39)
fee_56 = int(final_km * p56 + days * b56)

res_df = pd.DataFrame({
    "车型": ["39座", "56座"],
    "计算里程": [f"{final_km} KM", f"{final_km} KM"],
    "总报价": [f"{fee_39} 元", f"{fee_56} 元"]
})
st.table(res_df)

# --- 微信复制文本 ---
st.subheader("🔗 微信报价一键复制")
route_display = " - ".join([l['name'] for l in final_locations])
wx_msg = f"【包车报价单】\n路线：{route_display}\n路程：约{final_km}公里\n天数：{days}天\n---\n39座报价：{fee_39}元\n56座报价：{fee_56}元\n(报价包含油费、路桥费，不含司机食宿)"
st.text_area("长按框内文字复制：", wx_msg, height=150)
