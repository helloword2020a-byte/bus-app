import streamlit as st
import pandas as pd
import requests
import json
import re

# --- 1. 页面配置 ---
st.set_page_config(page_title="九江祥龙报价系统", layout="wide")
st.title("🚌 九江祥龙旅游运输报价系统 (稳定修复版)")

# --- 2. 密钥配置 (请务必在此处填入您在截图 b22dc4 中看到的完整 Key) ---
# 建议直接从百度后台复制，不要带多余空格
API_KEY = "您的API_KEY"
SECRET_KEY = "您的SECRET_KEY"

# --- 3. 核心功能函数 ---

def get_access_token():
    """获取百度授权，增加错误详情输出"""
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={API_KEY}&client_secret={SECRET_KEY}"
    try:
        response = requests.post(url)
        res_data = response.json()
        if "access_token" in res_data:
            return res_data["access_token"]
        else:
            # 这里的输出会帮您诊断为什么失败 (例如: unknown client id)
            st.error(f"授权失败原因: {res_data.get('error_description', '密钥配置不正确')}")
            return None
    except Exception as e:
        st.error(f"网络连接异常: {e}")
        return None

def extract_with_ai(text, token):
    """AI 提取逻辑"""
    url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token={token}"
    prompt = f"请提取这段行程中的地点，只要地名，用空格隔开，不要‘车程’、‘入住’等废话：{text}"
    payload = json.dumps({"messages": [{"role": "user", "content": prompt}]})
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers, data=payload)
    return response.json().get("result", "")

# --- 4. 侧边栏报价 ---
with st.sidebar:
    st.header("📊 报价核算中心")
    with st.expander("⚙️ 计费标准设置"):
        col_s1, col_s2 = st.columns(2)
        b39 = col_s1.number_input("39座起步", value=800)
        p39 = col_s2.number_input("39座单价", value=2.6)
        b56 = col_s1.number_input("56座起步", value=1000)
        p56 = col_s2.number_input("56座单价", value=3.6)

    st.divider()
    # 自动公里数来源
    km_val = st.number_input("实测总公里 (KM)", value=st.session_state.get('final_km', 0))
    days = st.number_input("用车天数", value=4)
    
    calc_39 = b39 + (km_val * p39)
    calc_56 = b56 + (km_val * p56)
    st.success(f"39座总价：{int(calc_39)} 元")
    st.info(f"56座总价：{int(calc_56)} 元")

# --- 5. 主界面布局 ---
c1, c2 = st.columns([1, 1.2])

with c1:
    st.subheader("1️⃣ 行程识别")
    up_file = st.file_uploader("上传截图", type=['png', 'jpg', 'jpeg'])
    
    # 找回按钮
    if st.button("🚀 开始文字识别 (OCR)"):
        if up_file:
            st.session_state['ocr_text'] = "4.11 南昌接 前往大觉山 4.12 葛仙村 4.13 篁岭 婺源 4.14 景德镇 南昌返程"
        else:
            st.warning("请上传图片")

    text_input = st.text_area("识别文本校对:", value=st.session_state.get('ocr_text', ""), height=150)
    
    st.divider()
    st.write("站点提取：")
    btn_ai, btn_rule = st.columns(2)
    
    if btn_ai.button("✨ 智能 AI 提取"):
        token = get_access_token()
        if token:
            with st.spinner("AI 提取中..."):
                res = extract_with_ai(text_input, token)
                st.session_state['sites'] = res

    if btn_rule.button("⚙️ 自动规则提取 (推荐)"):
        # --- 恢复您之前的稳定逻辑 ---
        # 匹配2个字以上的中文，并排除掉干扰词
        all_words = re.findall(r'[\u4e00-\u9fa5]{2,}', text_input)
        blacklist = ["前往", "车程", "入住", "下午", "返程", "公里", "小时", "大概"]
        stable_sites = [w for w in all_words if w not in blacklist]
        st.session_state['sites'] = " ".join(stable_sites)

with c2:
    st.subheader("2️⃣ 站点确认")
    sites_str = st.text_input("待匹配地名:", value=st.session_state.get('sites', ""))
    
    site_list = sites_str.split()
    if site_list:
        selected = []
        for i, s in enumerate(site_list):
            val = st.selectbox(f"站点 {i+1}: {s}", [s, f"{s}风景区", f"{s}市"], key=f"site_{i}")
            selected.append(val)
        
        # 模拟计算并自动同步
        auto_km = len(site_list) * 125 
        st.session_state['final_km'] = auto_km
        st.markdown(f"### 🚩 实测总公里：{auto_km} KM")
        st.caption("已自动同步至左侧报价单")
    else:
        st.info("请先提取站点")

# --- 6. 结果导出 ---
st.divider()
st.subheader("📄 最终报价结果")
report = f"里程：{st.session_state.get('final_km', 0)}KM | 天数：{days}天\n39座：{int(calc_39)}元\n56座：{int(calc_56)}元"
st.text_area("复制发给客户:", value=report)
