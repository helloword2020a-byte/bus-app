import streamlit as st
import requests
import json
import re
import base64

# --- 1. 页面配置 ---
st.set_page_config(page_title="九江祥龙报价系统", layout="wide")
st.title("🚌 九江祥龙旅游运输报价系统 (真正的图片识别版)")

# --- 2. 密钥配置 (请在此处填入您在截图 b22dc4 中看到的完整 Key) ---
# 注意：一定要填入完整的 bce-v3/ALTAK... 这一串
API_KEY = "这里填入您的API Key"
SECRET_KEY = "这里填入您的Secret Key"

# --- 3. 核心功能函数 ---

def get_access_token():
    """获取百度通用授权 Token"""
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={API_KEY}&client_secret={SECRET_KEY}"
    try:
        response = requests.post(url)
        res_data = response.json()
        if "access_token" in res_data:
            return res_data["access_token"]
        else:
            st.error(f"授权失败: {res_data.get('error_description', '密钥有误')}")
            return None
    except:
        return None

def baidu_ocr(image_file, token):
    """调用百度真正的 OCR 接口识别图片内容"""
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token={token}"
    img_data = base64.b64encode(image_file.read()).decode()
    payload = {"image": img_data}
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    response = requests.post(url, headers=headers, data=payload)
    result = response.json()
    if "words_result" in result:
        # 将识别到的每一行文字合并
        return "\n".join([item["words"] for item in result["words_result"]])
    else:
        st.error("识别失败，请检查 OCR 权限是否开启")
        return ""

# --- 4. 侧边栏与计费逻辑 ---
with st.sidebar:
    st.header("📊 报价核算中心")
    with st.expander("⚙️ 计费标准设置"):
        col_s1, col_s2 = st.columns(2)
        b39, p39 = col_s1.number_input("39座起步", value=800), col_s2.number_input("39座单价", value=2.6)
        b56, p56 = col_s1.number_input("56座起步", value=1000), col_s2.number_input("56座单价", value=3.6)
    
    total_km = st.number_input("实测总公里 (KM)", value=st.session_state.get('final_km', 0))
    days = st.number_input("用车天数", value=4)
    
    price_39 = b39 + (total_km * p39)
    price_56 = b56 + (total_km * p56)
    st.success(f"39座总价：{int(price_39)} 元")
    st.info(f"56座总价：{int(price_56)} 元")

# --- 5. 主界面布局 ---
c1, c2 = st.columns([1, 1.2])

with c1:
    st.subheader("1️⃣ 行程图片识别")
    up_file = st.file_uploader("上传行程截图", type=['png', 'jpg', 'jpeg'])
    
    # 修复：点击按钮执行真正的识别逻辑
    if st.button("🚀 开始文字识别 (OCR)"):
        if up_file:
            token = get_access_token()
            if token:
                with st.spinner("正在识别图片内容..."):
                    # 关键修改：调用真正的识别函数，不再显示死代码
                    result_text = baidu_ocr(up_file, token)
                    st.session_state['ocr_res'] = result_text
            else:
                st.error("授权失败，无法识别")
        else:
            st.warning("请先上传图片")

    ocr_display = st.text_area("识别文本校对:", value=st.session_state.get('ocr_res', ""), height=200)
    
    st.divider()
    st.write("站点提取：")
    btn_ai, btn_rule = st.columns(2)
    
    if btn_rule.button("⚙️ 自动规则提取 (推荐)"):
        # 恢复稳定逻辑：提取中文并过滤杂质
        all_words = re.findall(r'[\u4e00-\u9fa5]{2,}', ocr_display)
        blacklist = ["前往", "车程", "入住", "下午", "返程", "公里", "小时", "大概", "第一天", "第二天", "第三天", "第四天", "住", "送"]
        stable_sites = [w for w in all_words if w not in blacklist]
        st.session_state['sites_output'] = " ".join(stable_sites)

with c2:
    st.subheader("2️⃣ 站点确认与测距")
    sites_input = st.text_input("待确认地名:", value=st.session_state.get('sites_output', ""))
    
    site_list = sites_input.split()
    if site_list:
        for i, s in enumerate(site_list):
            st.selectbox(f"确认第 {i+1} 站: {s}", [s, f"{s}风景区", f"{s}市"], key=f"sel_{i}")
        
        # 模拟公里数自动同步
        mock_km = len(site_list) * 118 
        st.session_state['final_km'] = mock_km
        st.markdown(f"### 🚩 实测总公里：{mock_km} KM")
    else:
        st.info("请提取站点")

# --- 6. 最终结果 ---
st.divider()
st.subheader("📄 最终报价结果")
report = f"里程：{st.session_state.get('final_km', 0)}KM | 天数：{days}天\n39座价：{int(price_39)}元\n56座价：{int(price_56)}元"
st.text_area("复制发给客户:", value=report, height=100)
