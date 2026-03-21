import streamlit as st
import pandas as pd
import requests
import re

# 页面基础配置
st.set_page_config(page_title="包车报价系统-精准识别版", layout="wide")
st.title("🚌 包车报价系统（智能识别优化版）")

# --- 高德 Key ---
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74" 

# --- 侧边栏：价格参数 ---
st.sidebar.header("单价/起步费调节")
p39 = st.sidebar.number_input("39座单价 (元/公里)", value=2.6)
p56 = st.sidebar.number_input("56座单价 (元/公里)", value=3.6)
b39 = st.sidebar.number_input("39座起步费 (元/天)", value=800.0)
b56 = st.sidebar.number_input("56座起步费 (元/天)", value=1000.0)

# --- 智能行程提取函数 (核心优化) ---
def smart_extract(text):
    if not text: return ""
    # 1. 彻底剔除行程单中的干扰词
    noise = [
        r"第\d+天", r"车程约[\d\.]+h", r"住[^\s]+", r"下午", r"上午", r"中午", r"晚上",
        r"前往", r"返回", r"返程", r"接", r"送", r"简易行程", r"行程", r"约", r"h",
        r"小时", r"车程", r"时间", r"入住"
    ]
    temp_text = text
    for n in noise:
        temp_text = re.sub(n, " ", temp_text)
    
    # 2. 提取2-6字的汉字词（通常是地名）
    raw_words = re.findall(r'[\u4e00-\u9fa5]{2,6}', temp_text)
    
    # 3. 二次清理：剔除“前往”、“接引”这种动词或干扰词
    forbidden = ["前往", "接引", "提示", "地址", "路线", "时间", "价格"]
    clean_words = [w for w in raw_words if w not in forbidden]
    
    # 4. 去重并保持顺序
    result = []
    for w in clean_words:
        if w not in result:
            result.append(w)
    return " ".join(result)

# --- 界面布局 ---
st.subheader("🚀 智能行程识别")
smart_text = st.text_area("请直接粘贴行程文本：", height=150, placeholder="例如：4.11 南昌接 前往大觉山...")

# 执行识别
identified_names = smart_extract(smart_text)

if smart_text:
    st.success(f"🔍 自动提取地名：{identified_names}")

# --- 第一步：确认输入 ---
st.subheader("1️⃣ 确认线路关键词")
final_input = st.text_input("地点间用空格分隔（识别不准可在此手动修改）", value=identified_names)

# --- 第二步：确认精确位置 ---
st.subheader("2️⃣ 确认精确位置")
final_locations = []

if final_input:
    names = final_input.split()
    for i, name in enumerate(names):
        try:
            # 增加“江西”前缀提高搜索精度
            search_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}&location=115.892151,28.676493" # 锁定江西坐标附近搜索
            tips_res = requests.get(search_url).json()
            tips = tips_res.get('tips', [])
            
            # 过滤掉没有坐标的结果
            options = [f"{t['name']} ({t.get('district', '')})" for t in tips if t.get('name') and isinstance(t.get('location'), str)]

            if not options:
                options = [f"{name} (未搜索到，请修改关键词)"]
            
            chosen = st.selectbox(f"📍 第{i+1}站 [{name}]", options, key=f"sel_{i}")
            
            actual_name = chosen.split(" (")[0]
            loc_data = next((t.get('location') for t in tips if t['name'] == actual_name and isinstance(t.get('location'), str)), None)
            
            if loc_data:
                final_locations.append({"name": actual_name, "coord": loc_data})
        except:
            pass

# --- 第三步：路径规划 ---
st.divider()
auto_dist = 0

if len(final_locations) >= 2:
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
        st.error("计算出错，请检查地点是否选择准确")

# --- 第四步：报价 ---
c1, c2 = st.columns(2)
with c1:
    final_km = st.number_input("里程修正", value=int(auto_dist), step=1)
with c2:
    days = st.number_input("用车天数", min_value=1, value=4, step=1) # 默认为4天行程

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
