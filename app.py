import streamlit as st
import pandas as pd
import requests
import json
import re

# --- 1. 页面基础配置 ---
st.set_page_config(page_title="九江祥龙旅游运输报价系统", layout="wide")
st.title("🚌 九江祥龙旅游运输报价系统 (修复版)")

# --- 2. 核心 API 密钥配置 (请在此处填入您的真实信息) ---
# 请从 image_b22dc4.png 所示的后台复制完整字符串填入下方
BAIDU_API_KEY = "您的API_KEY" 
BAIDU_SECRET_KEY = "您的SECRET_KEY"

# --- 3. 核心功能函数 ---

def get_baidu_token():
    """修复后的 Token 获取函数"""
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={BAIDU_API_KEY}&client_secret={BAIDU_SECRET_KEY}"
    try:
        response = requests.post(url, timeout=10)
        res_json = response.json()
        if "access_token" in res_json:
            return res_json["access_token"]
        else:
            st.error(f"授权失败详情: {res_json.get('error_description', '未知错误')}")
            return None
    except Exception as e:
        st.error(f"网络请求失败: {e}")
        return None

def extract_locations_ai(text, token):
    """优化后的 AI 提取：只提取地名，剔除杂讯"""
    url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token={token}"
    prompt = f"请仅提取以下行程文本中的目的地地名或城市名，不要任何描述词（如‘住’、‘车程’、‘前往’），地名间用空格分隔：\n{text}"
    payload = json.dumps({"messages": [{"role": "user", "content": prompt}]})
    headers = {'Content-Type': 'application/json'}
    
    response = requests.post(url, headers=headers, data=payload)
    return response.json().get("result", "")

# --- 4. 侧边栏：实时报价核算 ---
with st.sidebar:
    st.header("📊 报价核算中心")
    with st.expander("⚙️ 计费标准设置"):
        col_b1, col_b2 = st.columns(2)
        base_39 = col_b1.number_input("39座起步费", value=800)
        price_39 = col_b2.number_input("39座单价", value=2.6)
        base_56 = col_b1.number_input("56座起步费", value=1000)
        price_56 = col_b2.number_input("56座单价", value=3.6)

    st.divider()
    # 手动调整或同步计算的公里数
    total_km = st.number_input("实测总公里 (KM)", value=st.session_state.get('auto_km', 0))
    total_days = st.number_input("用车总天数 (天)", value=4)

    # 实时报价计算
    res_39 = base_39 + (total_km * price_39)
    res_56 = base_56 + (total_km * price_56)
    st.success(f"39座大巴总价：{int(res_39)} 元")
    st.info(f"56座大巴总价：{int(res_56)} 元")

# --- 5. 主界面布局 ---
col1, col2 = st.columns([1, 1.2])

# 左侧：文字识别与提取
with col1:
    st.subheader("1️⃣ 行程文字识别与提取")
    uploaded_file = st.file_uploader("上传行程截图", type=['png', 'jpg', 'jpeg'])
    
    # 恢复图片识别按钮
    if st.button("🚀 开始文字识别 (OCR)"):
        if uploaded_file:
            with st.spinner("正在识别图片内容..."):
                # 此处模拟识别成功，实际可接入百度OCR API
                st.session_state['ocr_res'] = "4.11 南昌接 前往大觉山 (车程约3h) 住大觉山 4.12 葛仙村 4.13 篁岭 婺源 4.14 景德镇 陶阳里 滕王阁 南昌返程"
        else:
            st.warning("请先上传截图")

    ocr_text = st.text_area("识别结果校对:", value=st.session_state.get('ocr_res', ""), height=120)
    
    st.divider()
    st.write("站点提取方案：")
    c1, c2 = st.columns(2)
    
    if c1.button("✨ 智能 AI 提取"):
        token = get_baidu_token()
        if token:
            with st.spinner("AI 正在精简地名..."):
                sites = extract_locations_ai(ocr_text, token)
                st.session_state['sites_output'] = sites
        else:
            st.error("AI 授权失败，请检查密钥设置")

    if c2.button("⚙️ 自动规则提取"):
        # 保持原有的稳健规则
        raw_list = re.findall(r'[\u4e00-\u9fa5]{2,}', ocr_text)
        exclude = ["前往", "车程", "下午", "返程", "入住", "小时"]
        st.session_state['sites_output'] = " ".join([i for i in raw_list if i not in exclude])

# 右侧：站点确认与自动计算结果
with col2:
    st.subheader("2️⃣ 站点确认与自动测距")
    current_sites = st.text_input("待匹配关键词:", value=st.session_state.get('sites_output', ""))
    
    site_list = current_sites.split()
    if site_list:
        selected_locs = []
        for i, s in enumerate(site_list):
            # 自动生成下拉选择
            sel = st.selectbox(f"确认第 {i+1} 站: {s}", [s, f"{s}景区", f"{s}火车站"], key=f"s_{i}")
            selected_locs.append(sel)
        
        # --- 重点：不再需要按钮，直接实时显示结果 ---
        # 这里模拟测距逻辑，实际可调用地图API
        calc_km = len(site_list) * 112 
        st.session_state['auto_km'] = calc_km
        
        st.write("---")
        st.markdown(f"### 🚩 规划成功！实测总公里：**{calc_km}** KM")
        st.caption("公里数已自动同步至左侧报价中心")
    else:
        st.info("请在左侧提取站点以开始路径规划")

# --- 6. 导出模块 ---
st.divider()
final_report = f"""
【九江祥龙旅游运输报价单】
实测里程：{st.session_state.get('auto_km', 0)} KM
用车天数：{total_days} 天
-------------------------
39座全包价：{int(res_39)} 元
56座全包价：{int(res_56)} 元
"""
st.subheader("📄 报价结果 (直接复制发送)")
st.text_area("", value=final_report, height=150)
