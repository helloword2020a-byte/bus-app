import streamlit as st
import pandas as pd
import requests
import re
import base64

# --- 1. 密钥配置区 (已根据您的截图完成配置) ---
BAIDU_API_KEY = "1vBiCqNtSYFRx6GYsGwpwXdM"       #
BAIDU_SECRET_KEY = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO" #
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="包车报价智能系统", layout="wide")

# --- 2. 核心功能函数 (支持全能降级逻辑) ---
def get_baidu_token():
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={BAIDU_API_KEY}&client_secret={BAIDU_SECRET_KEY}"
    try:
        res = requests.get(url).json()
        return res.get("access_token")
    except: return None

def ocr_smart_engine(file_bytes):
    token = get_baidu_token()
    if not token: return "密钥配置错误，请检查 Key"
    
    img64 = base64.b64encode(file_bytes).decode()
    # 优先级顺序：高精度含位置 -> 高精度 -> 标准含位置 -> 标准
    endpoints = [
        ("accurate", "高精度含位置版"),
        ("accurate_basic", "高精度版"),
        ("general", "标准含位置版"),
        ("general_basic", "标准版")
    ]
    
    for api_path, api_name in endpoints:
        url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/{api_path}?access_token={token}"
        try:
            res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
            if 'words_result' in res:
                st.toast(f"✨ 当前调用接口：{api_name}")
                return "\n".join([item['words'] for item in res.get('words_result', [])])
        except: continue
    return "所有识别接口额度已耗尽或调用失败"

# --- 3. 界面布局 ---
st.title("🚌 包车报价智能系统 (已激活)")

# 第一部分：上传与识别
st.subheader("1️⃣ 行程单识别")
col1, col2 = st.columns([1, 1])

with col1:
    up_file = st.file_uploader("点击上传或 Ctrl+V 粘贴行程截图", type=["jpg", "png", "jpeg"])
    if up_file:
        img_bytes = up_file.read()
        st.image(img_bytes, width=400)
        if st.button("🚀 开始高精度识别"):
            with st.spinner("正在解析行程文字..."):
                st.session_state['ocr_result'] = ocr_smart_engine(img_bytes)

with col2:
    text_edit = st.text_area("识别出的文本（可手动修改）：", value=st.session_state.get('ocr_result', ""), height=300)
    if st.button("🎯 确认文字并填充站点"):
        # 清洗逻辑：提取2-6个字的中文地名
        raw = text_edit
        noise = [r"第\d+天", r"车程", r"入住", r"前往", r"接引", r"小时", r"约", r"含早"]
        for p in noise: raw = re.sub(p, " ", raw)
        found = re.findall(r'[\u4e00-\u9fa5]{2,6}', raw)
        # 排除非地名干扰词
        stop_words = ["可以", "需要", "提示", "行程", "结束", "早餐", "晚餐"]
        clean = [w for w in found if w not in stop_words and len(w) > 1]
        st.session_state['sites_final'] = " ".join(dict.fromkeys(clean))
        st.success("✅ 站点提取成功！")

# 第二部分：站点确认与自动报价
st.divider()
st.subheader("2️⃣ 确认位置与生成报价")
site_str = st.text_input("提取的关键词：", value=st.session_state.get('sites_final', ""))

if site_str:
    names = site_str.split()
    loc_data = []
    cols = st.columns(min(len(names), 4))
    for i, name in enumerate(names):
        with cols[i % 4]:
            url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}&location=115.89,28.67"
            tips = requests.get(url).json().get('tips', [])
            opts = [f"{t['name']} ({t.get('district','')})" for t in tips if t.get('location')]
            sel = st.selectbox(f"站点 {i+1}", opts or [f"{name}(未搜到)"], key=f"site_{i}")
            coord = next((t['location'] for t in tips if t['name'] == sel.split(" (")[0]), None)
            if coord: loc_data.append(coord)

    if len(loc_data) >= 2:
        try:
            # 高德测距
            org, des = loc_data[0], loc_data[-1]
            way = ";".join(loc_data[1:-1])
            route_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way}"
            route_res = requests.get(route_url).json()
            km = int(round(int(route_res['route']['paths'][0]['distance']) / 1000))
            
            c_km, c_day = st.columns(2)
            with c_km: f_km = st.number_input("总里程 (KM)", value=km)
            with c_day: days = st.number_input("天数", value=4)
            
            # 计算价格
            p39 = int(f_km * 2.6 + days * 800)
            p56 = int(f_km * 3.6 + days * 1000)
            
            st.table(pd.DataFrame({
                "车型": ["39座", "56座"], "里程": [f"{f_km}KM"]*2, 
                "天数": [f"{days}天"]*2, "总报价": [f"{p39}元", f"{p56}元"]
            }))
        except: st.warning("请确保所有站点已正确选择。")
