import streamlit as st
import pandas as pd
import requests
import re

# 页面基础配置
st.set_page_config(page_title="包车报价系统-智能版", layout="wide")
st.title("🚌 包车报价系统（智能识别+紧凑版）")

# --- 高德 Key ---
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74" 

# --- 侧边栏：价格参数 ---
st.sidebar.header("单价/起步费调节")
p39 = st.sidebar.number_input("39座单价 (元/公里)", value=2.6)
p56 = st.sidebar.number_input("56座单价 (元/公里)", value=3.6)
b39 = st.sidebar.number_input("39座起步费 (元/天)", value=800.0)
b56 = st.sidebar.number_input("56座起步费 (元/天)", value=1000.0)

# --- 新功能：智能行程提取 ---
st.subheader("🚀 智能行程识别")
st.info("💡 就像快递单识别一样，直接粘贴一段文字行程，我会尝试提取地名。")
smart_text = st.text_area("请粘贴您的行程描述（例如：第一天南昌出发，下午到大觉山...）", height=100)

# 自动提取逻辑
suggested_names = ""
if smart_text:
    # 简单的正则提取（进阶版通常需要调用专门的NLP接口，这里先做逻辑过滤）
    # 过滤掉常见干扰字词
    noise_words = ["出发", "到达", "玩", "去", "然后", "到", "回", "几天", "第一天", "第二天", "下午", "上午", "我们要", "住"]
    clean_text = smart_text
    for word in noise_words:
        clean_text = clean_text.replace(word, " ")
    
    # 提取2个字以上的词作为地名候选
    extracted = re.findall(r'[\u4e00-\u9fa5]{2,}', clean_text)
    suggested_names = " ".join(extracted)
    st.success(f"🔍 识别到地名关键词：{suggested_names}")

# --- 第一步：确认输入 ---
st.subheader("1️⃣ 确认线路关键词")
# 如果有智能识别的结果，优先填充
final_input = st.text_input("地点间用空格分隔（识别不准可在此手动修改）", value=suggested_names if suggested_names else "南昌昌北国际机场 大觉山 葛仙村 篁岭 景德镇 南昌昌北国际机场")

# --- 第二步：确认精确位置（紧凑布局） ---
st.subheader("2️⃣ 确认精确位置")
final_locations = []

if final_input:
    names = final_input.split()
    for i, name in enumerate(names):
        try:
            search_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
            tips_res = requests.get(search_url).json()
            tips = tips_res.get('tips', [])
            
            options = [f"{t['name']} ({t.get('district', '')})" for t in tips if t.get('name') and t.get('location')]

            if not options:
                options = [f"{name} (未搜索到，请手动修改输入)"]
            
            # 紧凑排列
            chosen = st.selectbox(f"📍 第{i+1}站 [{name}]", options, key=f"sel_{i}")
            
            actual_name = chosen.split(" (")[0]
            loc_data = next((t.get('location') for t in tips if t['name'] == actual_name and t.get('location')), None)
            
            if loc_data:
                final_locations.append({"name": actual_name, "coord": loc_data})
        except:
            pass

# --- 第三步：路径规划 ---
st.divider()
auto_dist = 0

if len(final_locations) == len(final_input.split()) and len(final_locations) >= 2:
    try:
        origin_coord = final_locations[0]['coord']
        destination_coord = final_locations[-1]['coord']
        waypoints = ";".join([l['coord'] for l in final_locations[1:-1]])
        
        route_url = f"https://restapi.amap.com/v3/direction/driving?origin={origin_coord}&destination={destination_coord}&key={AMAP_KEY}&strategy=2"
        if waypoints:
            route_url += f"&waypoints={waypoints}"
            
        route_res = requests.get(route_url).json()
        if route_res['status'] == '1':
            meters = int(route_res['route']['paths'][0]['distance'])
            auto_dist = int(round(meters / 1000))
            
            route_flow = " ➡️ ".join([l['name'] for l in final_locations])
            st.info(f"🗺️ 线路预览：{route_flow}")
            st.success(f"✅ 自动测算里程：{auto_dist} KM")
    except:
        st.error("里程计算出错")

# --- 第四步：报价 ---
c1, c2 = st.columns(2)
with c1:
    final_km = st.number_input("里程修正", value=int(auto_dist), step=1)
with c2:
    days = st.number_input("用车天数", min_value=1, value=1, step=1)

f39 = int(final_km * p39 + days * b39)
f56 = int(final_km * p56 + days * b56)

st.table(pd.DataFrame({
    "车型": ["39座", "56座"],
    "里程": [f"{final_km} KM"] * 2,
    "天数": [f"{days} 天"] * 2,
    "总报价": [f"{f39} 元", f"{f56} 元"]
}))

# 复制区域
if final_locations:
    route_str = " - ".join([l['name'] for l in final_locations])
    msg = f"【包车报价单】\n路线：{route_str}\n里程：约{final_km}公里\n天数：{days}天\n---\n39座报价：{f39}元\n56座报价：{f56}元\n(报价含路桥费，不含司机食宿)"
    st.text_area("复制报价：", msg, height=130)
