import streamlit as st
import pandas as pd
import requests
import re
import base64

# --- 1. 密钥配置区 (已根据您的百度实名账号配置) ---
BAIDU_API_KEY = "1vBiCqNtSYFRx6GYsGwpwXdM"       #
BAIDU_SECRET_KEY = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO" #
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆-包车报价智能系统", layout="wide")

# --- 2. 核心功能函数 ---
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
    # 按照您领取的资源包顺序：高精度含位置版(500次) -> 高精度版(1000次) -> 标准版
    endpoints = [
        ("accurate", "高精度含位置版"),
        ("accurate_basic", "高精度版"),
        ("general_basic", "标准版")
    ]
    
    for api_path, api_name in endpoints:
        url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/{api_path}?access_token={token}"
        try:
            res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
            if 'words_result' in res:
                st.toast(f"✨ 当前引擎：{api_name}")
                return "\n".join([item['words'] for item in res.get('words_result', [])])
        except: continue
    return "识别失败，请检查网络或额度"

# --- 3. 界面布局 ---
st.title("🚌 九江祥隆旅游运输报价系统")

# 第一部分：行程识别与精准清洗
st.subheader("1️⃣ 行程单智能识别")
col1, col2 = st.columns([1, 1])

with col1:
    up_file = st.file_uploader("粘贴行程单截图 (Ctrl+V)", type=["jpg", "png", "jpeg"])
    if up_file:
        img_bytes = up_file.read()
        st.image(img_bytes, width=400)
        if st.button("🚀 开始高精度识别"):
            with st.spinner("正在提取文字..."):
                st.session_state['ocr_raw_text'] = ocr_smart_engine(img_bytes)

with col2:
    text_edit = st.text_area("识别出的原始文本：", value=st.session_state.get('ocr_raw_text', ""), height=250)
    
    if st.button("🎯 自动清洗并提取地名"):
        raw = text_edit
        # --- 增强版清洗逻辑：剔除干扰词 ---
        noise_patterns = [
            r"第\d+天", r"行程", r"简易", r"车程约?[\d\.h小时]+", 
            r"住[^\s，。]*", r"前往", r"接引", r"返程", r"结束", 
            r"上午", r"中午", r"下午", r"晚上", r"含早", r"晚", r"自理", r"早餐", r"晚餐"
        ]
        for p in noise_patterns:
            raw = re.sub(p, " ", raw)
            
        # 提取 2-6 个字的中文
        found = re.findall(r'[\u4e00-\u9fa5]{2,6}', raw)
        # 排除非地名的高频干扰词
        stop_words = ["可以", "需要", "提示", "进行", "返回", "集合", "地点", "时间", "到达", "游览", "南昌", "返程"]
        
        # 过滤并保持顺序去重
        seen = set()
        clean_sites = []
        for w in found:
            # 过滤掉禁词，且长度大于1，且未重复
            if w not in stop_words and len(w) > 1 and w not in seen:
                clean_sites.append(w)
                seen.add(w)
        
        # 特殊处理：如果行程中有南昌，通常作为起点或终点
        st.session_state['sites_final'] = " ".join(clean_sites)
        st.success("✅ 已剔除杂词，站点提取完毕！")

# 第二部分：站点确认与自动报价
st.divider()
st.subheader("2️⃣ 确认位置与生成报价")
site_str = st.text_input("提取的关键词（可手动微调）：", value=st.session_state.get('sites_final', ""))

if site_str:
    names = site_str.split()
    loc_data = []
    # 动态排版显示站点选择
    cols = st.columns(min(len(names), 4))
    for i, name in enumerate(names):
        with cols[i % 4]:
            # 使用高德 API 搜索精确位置
            url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}&location=115.89,28.67"
            tips = requests.get(url).json().get('tips', [])
            opts = [f"{t['name']} ({t.get('district','')})" for t in tips if t.get('location')]
            
            sel = st.selectbox(f"站点 {i+1}", opts or [f"{name}(未搜到)"], key=f"site_sel_{i}")
            coord = next((t['location'] for t in tips if t['name'] == sel.split(" (")[0]), None)
            if coord: loc_data.append(coord)

    # 第三部分：计算结果显示
    if len(loc_data) >= 2:
        try:
            # 调用高德路径规划计算公里数
            org, des = loc_data[0], loc_data[-1]
            way = ";".join(loc_data[1:-1])
            route_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way}"
            route_res = requests.get(route_url).json()
            km = int(round(int(route_res['route']['paths'][0]['distance']) / 1000))
            
            c_km, c_day = st.columns(2)
            with c_km: f_km = st.number_input("实测总里程 (KM)", value=km)
            with c_day: days = st.number_input("用车总天数", value=4)
            
            # 您之前的计费公式
            p39 = int(f_km * 2.6 + days * 800)
            p56 = int(f_km * 3.6 + days * 1000)
            
            st.table(pd.DataFrame({
                "车型": ["39座大巴", "56座大巴"], 
                "预估里程": [f"{f_km} KM"]*2, 
                "用车时长": [f"{days} 天"]*2, 
                "总报价 (建议)": [f"{p39} 元", f"{p56} 元"]
            }))
        except: st.warning("请确保以上所有站点已选择准确的位置。")
