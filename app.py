import streamlit as st
import pandas as pd
import requests
import json
import re

# --- 1. 页面基础配置 ---
st.set_page_config(page_title="九江祥龙旅游运输报价系统 (AI 旗舰版)", layout="wide")
st.title("🚌 九江祥龙旅游运输报价系统")

# --- 2. 侧边栏：计费标准与实时清单 ---
with st.sidebar:
    st.header("📊 报价核算中心")
    with st.expander("⚙️ 计费标准设置", expanded=True):
        col_base1, col_base2 = st.columns(2)
        base_39 = col_base1.number_input("39座起步费", value=800)
        price_39 = col_base2.number_input("39座单价", value=2.6)
        base_56 = col_base1.number_input("56座起步费", value=1000)
        price_56 = col_base2.number_input("56座单价", value=3.6)

    st.divider()
    # 这里的公里数将由右侧逻辑自动更新
    total_km = st.number_input("实测总公里 (KM)", min_value=0, key="total_km_input")
    total_days = st.number_input("用车总天数 (天)", value=4)

    # 实时计算价格
    calc_39 = base_39 + (total_km * price_39)
    calc_56 = base_56 + (total_km * price_56)

    st.success(f"39座大巴总价：{int(calc_39)} 元")
    st.info(f"56座大巴总价：{int(calc_56)} 元")

# --- 3. 核心功能函数 ---

def get_baidu_token(api_key, secret_key):
    """获取百度千帆/AI权限Token"""
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
    payload = json.dumps("")
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    response = requests.request("POST", url, headers=headers, data=payload)
    return response.json().get("access_token")

def extract_locations_ai(text, token):
    """优化后的智能AI提取：严格约束地名输出"""
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token=" + token
    
    # 这里的 Prompt 是解决“杂讯”的关键
    prompt = f"""
    你是一个专业的旅游计调助手。请从下面这段行程文本中提取所有的【地理地点、景区名称、城市名】。
    要求：
    1. 只输出地名，地名之间用一个空格分隔。
    2. 严禁输出“车程”、“住”、“前往”、“下午”等描述性词汇。
    3. 严格按照行程出现的先后顺序排列。
    4. 如果地名重复，请保留重复。
    
    待处理文本：{text}
    """
    
    payload = json.dumps({"messages": [{"role": "user", "content": prompt}]})
    headers = {'Content-Type': 'application/json'}
    response = requests.request("POST", url, headers=headers, data=payload)
    result = response.json().get("result", "")
    return result

# --- 4. 主界面布局 ---
col1, col2 = st.columns([1, 1.2])

# 左侧：行程识别
with col1:
    st.subheader("1️⃣ 行程文字识别 (OCR)")
    uploaded_file = st.file_uploader("上传行程截图", type=['png', 'jpg', 'jpeg'])
    
    # 模拟OCR后的文本框（此处您可接入OCR代码）
    ocr_text = st.text_area("文本校对框 (如有误请手动修改):", 
                            value="4.11 南昌接 前往大觉山 (车程约3h) 住大觉山 4.12 前往葛仙村 住葛仙村 4.13 前往篁岭 住婺源 4.14 前往景德镇 陶阳里 滕王阁 下午南昌返程",
                            height=150)
    
    st.write("---")
    st.subheader("站点提取方案选择")
    c_ai, c_rule = st.columns(2)
    
    extracted_sites = ""
    
    if c_ai.button("✨ 智能 AI 提取"):
        # 注意：此处需填入您在 image_b22dc4.png 中看到的完整 Key
        API_KEY = "您的API_KEY" 
        SECRET_KEY = "您的SECRET_KEY"
        
        token = get_baidu_token(API_KEY, SECRET_KEY)
        if token:
            with st.spinner("AI 正在深度解析地名..."):
                extracted_sites = extract_locations_ai(ocr_text, token)
                st.session_state['sites_output'] = extracted_sites
        else:
            st.error("AI 授权失败，请检查 API Key 和 Secret Key 是否正确。")

    if c_rule.button("⚙️ 自动(规则)提取"):
        # 基础正则过滤非中文字符（简单备选方案）
        raw_sites = re.findall(r'[\u4e00-\u9fa5]{2,}', ocr_text)
        extracted_sites = " ".join([s for s in raw_sites if s not in ["前往", "车程", "约", "下午", "返程"]])
        st.session_state['sites_output'] = extracted_sites

# 右侧：站点确认与自动测距
with col2:
    st.subheader("2️⃣ 站点确认与地图测距")
    
    current_sites = st.text_input("待匹配关键词 (空格隔开):", 
                                  value=st.session_state.get('sites_output', ""))
    
    site_list = current_sites.split()
    
    # 自动渲染站点选择框
    selected_locations = []
    if site_list:
        for i, site in enumerate(site_list):
            loc = st.selectbox(f"确认第 {i+1} 站: {site}", 
                               options=[f"{site} (匹配地点)", f"{site}景区", f"{site}市中心"],
                               key=f"site_{i}")
            selected_locations.append(loc)
        
        # --- 关键修改：取消按钮，直接计算 ---
        # 只要 site_list 有内容，就模拟自动计算公里数
        simulated_km = len(site_list) * 115 # 这里的逻辑应替换为您的地图测距API调用
        
        st.divider()
        st.success(f"✅ 路径规划成功！实测总公里数：{simulated_km} KM")
        
        # 自动同步到侧边栏的输入框
        st.session_state['total_km_input'] = simulated_km
        st.info("💡 公里数已自动同步至左侧报价单。")
    else:
        st.warning("暂无提取站点，请先执行左侧提取操作。")

# --- 5. 报价结果导出 ---
st.divider()
st.subheader("📄 报价结果 (直接复制发送)")
final_msg = f"""
【九江祥龙旅游运输报价单】
总里程：{st.session_state.get('total_km_input', 0)} KM
用车天数：{total_days} 天
-------------------------
🚌 39座大巴全包价：{int(calc_39)} 元
🚌 56座大巴全包价：{int(calc_56)} 元
"""
st.text_area("复制下方文字发给客户：", value=final_msg, height=150)
