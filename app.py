import streamlit as st
import pandas as pd
import requests
import re
import base64

# --- 1. 密钥配置区 ---
BAIDU_API_KEY = "1vBiCqNtSYFRx6GYsGwpwXdM"       
BAIDU_SECRET_KEY = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO" 
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥龙-智能报价系统Pro", layout="wide")

# --- 2. 百度OCR逻辑 ---
def get_baidu_token():
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={BAIDU_API_KEY}&client_secret={BAIDU_SECRET_KEY}"
    try:
        res = requests.get(url).json()
        return res.get("access_token")
    except: return None

def ocr_smart_engine(file_bytes):
    token = get_baidu_token()
    if not token: return "密钥配置错误"
    img64 = base64.b64encode(file_bytes).decode()
    endpoints = [("accurate", "高精度含位置版"), ("accurate_basic", "高精度版"), ("general_basic", "标准版")]
    for api_path, api_name in endpoints:
        url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/{api_path}?access_token={token}"
        try:
            res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
            if 'words_result' in res:
                st.toast(f"✨ 引擎：{api_name}")
                return "\n".join([item['words'] for item in res.get('words_result', [])])
        except: continue
    return "识别失败"

# --- 3. 界面布局 ---
st.title("🚌 九江祥隆旅游运输报价系统 (专业版)")

# 第一部分：行程识别
st.subheader("1️⃣ 行程单智能识别")
col_up, col_edit = st.columns([1, 1])

with col_up:
    up_file = st.file_uploader("上传行程单截图", type=["jpg", "png", "jpeg"])
    if up_file:
        img_bytes = up_file.read()
        st.image(img_bytes, width=400)
        if st.button("🚀 开始高精度识别"):
            with st.spinner("解析中..."):
                st.session_state['ocr_raw'] = ocr_smart_engine(img_bytes)

with col_edit:
    text_edit = st.text_area("识别文本校对：", value=st.session_state.get('ocr_raw', ""), height=250)
    if st.button("🎯 自动清洗地名"):
        raw = text_edit
        # 过滤动作、状态等杂词
        noise = [r"第\d+天", r"行程", r"简易", r"车程约?[\d\.h小时]+", r"住[^\s，。]*", 
                 r"前往", r"接引", r"返程", r"结束", r"含早", r"下午", r"上午", r"接$", r"送$"]
        for p in noise: raw = re.sub(p, " ", raw)
        found = re.findall(r'[\u4e00-\u9fa5]{2,6}', raw)
        stop_words = ["可以", "需要", "提示", "进行", "返回", "地点", "时间", "到达", "游览", "返程"]
        seen = set()
        clean_sites = [w for w in found if w not in stop_words and len(w) > 1 and not (w in seen or seen.add(w))]
        st.session_state['sites_final'] = " ".join(clean_sites)
        st.success("✅ 已提取核心地名！")

# 第二部分：站点确认（强制锁定江西）
st.divider()
st.subheader("2️⃣ 确认位置 (系统已优先搜索江西境内)")
site_str = st.text_input("待匹配地名：", value=st.session_state.get('sites_final', ""))

loc_data = []
if site_str:
    names = site_str.split()
    cols = st.columns(min(len(names), 4))
    for i, name in enumerate(names):
        with cols[i % 4]:
            # 核心改进：在高德搜索中加入 city=江西 限制
            search_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}&city=江西"
            tips = requests.get(search_url).json().get('tips', [])
            opts = [f"{t['name']} ({t.get('district','')})" for t in tips if t.get('location')]
            
            sel = st.selectbox(f"站点 {i+1}", opts or [f"{name}(未搜到)"], key=f"s_{i}")
            coord = next((t['location'] for t in tips if t['name'] == sel.split(" (")[0]), None)
            if coord: loc_data.append(coord)

# 第三部分：报价参数与结果
if len(loc_data) >= 2:
    st.divider()
    st.subheader("3️⃣ 运价参数调整与报价生成")
    
    # 报价参数配置区
    with st.expander("🛠️ 修改计费单价与起步费", expanded=True):
        cp1, cp2, cp3 = st.columns(3)
        with cp1:
            base_39 = st.number_input("39座起步费(元/天)", value=800)
            base_56 = st.number_input("56座起步费(元/天)", value=1000)
        with cp2:
            price_39 = st.number_input("39座超公里单价(元/KM)", value=2.6, step=0.1)
            price_56 = st.number_input("56座超公里单价(元/KM)", value=3.6, step=0.1)
        with cp3:
            st.info("💡 报价 = (公里数 × 单价) + (天数 × 起步费)")

    try:
        # 高德路径规划
        org, des = loc_data[0], loc_data[-1]
        way = ";".join(loc_data[1:-1])
        r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way}"
        res = requests.get(r_url).json()
        km = int(round(int(res['route']['paths'][0]['distance']) / 1000))
        
        ck, cd = st.columns(2)
        with ck: f_km = st.number_input("实测总里程 (KM)", value=km)
        with cd: days = st.number_input("用车总天数", value=4, min_value=1)
        
        # 应用新公式计算
        final_39 = int(f_km * price_39 + days * base_39)
        final_56 = int(f_km * price_56 + days * base_56)
        
        st.table(pd.DataFrame({
            "车型方案": ["39座大巴", "56座大巴"], 
            "核算里程": [f"{f_km} KM"]*2, 
            "用车天数": [f"{days} 天"]*2, 
            "最终总报价": [f"{final_39} 元", f"{final_56} 元"]
        }))
    except: st.warning("请检查站点位置选择是否正确。")
