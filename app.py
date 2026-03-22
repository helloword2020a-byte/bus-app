import streamlit as st
import pandas as pd
import requests
import re
import base64
import json

# ==================== 1. 核心密钥配置 ====================

# [必填] 这里填入你最新的 V2 版本 API Key (bce-v3/ALTAK-EMZixkEbLJ0iEkFcaJCFc/...)
AI_API_KEY_V2 = "bce-v3/ALTAK-EMZixkEbLJ0iEkFcaJCFc/74514893890101d198dd642b3b95ea68bed95897"

# 百度 OCR 密钥 (已为你配置好)
BAIDU_OCR_AK = "1vBiCqNtSYFRx6GYsGwpwXdM"         
BAIDU_OCR_SK = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  

# 高德地图密钥 (已为你配置好)
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统-AI旗舰版", layout="wide")

# ==================== 2. 功能引擎 ====================

def get_ocr_token():
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={BAIDU_OCR_AK}&client_secret={BAIDU_OCR_SK}"
    try: return requests.get(url).json().get("access_token")
    except: return None

def ocr_engine(file_bytes):
    token = get_ocr_token()
    if not token: return "OCR 授权失败"
    img64 = base64.b64encode(file_bytes).decode()
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token={token}"
    try:
        res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
        return "".join([i['words'] for i in res.get('words_result', [])])
    except: return "识别异常"

def ai_extract_locations_v2(text):
    """【旗舰级】大模型智能提取：精准拆分景点，绝不漏点"""
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-pro-128k"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY_V2}" # V2专用Bearer模式认证
    }
    
    # 旗舰版 Prompt：重点解决文末景点漏点和连词拆分
    prompt = (
        f"你是一个专业的旅游行程调度专家。请从以下文本中提取所有的目的地【地名】或【城市】。\n"
        f"特别注意：严禁漏掉结尾处的景点名或返程点（如：陶阳里、滕王阁、南昌）。\n"
        f"要求：\n"
        f"1. 只输出地名，地名之间用空格分隔。\n"
        f"2. 严禁输出数字序号（如1. 2. 3.）、严禁输出标点符号和动作动词。\n"
        f"3. 如果地名连在一起（如：陶阳里滕王阁），也请将其拆分为独立的景点。\n"
        f"原文：{text}"
    )
    
    payload = {"messages": [{"role": "user", "content": prompt}]}
    try:
        response = requests.post(url, headers=headers, json=payload)
        res = response.json()
        if "error_code" in res:
            # 这里会自动打印出报错码，方便我们排查
            return f"AI 错误({res['error_code']}): {res.get('error_msg')}"
        
        # 二次强力去噪清理
        raw_result = res.get("result", "").strip()
        clean_text = re.sub(r'\d+', ' ', raw_result)
        for junk in ["目的地", "地名", "地点", "：", ":", ".", "、", "接", "住", "前往", "返程", "车程"]:
            clean_text = clean_text.replace(junk, " ")
        return " ".join(clean_text.split())
    except Exception as e:
        return f"AI 连接异常: {str(e)}"

def rule_extract_locations(text):
    """【旗舰级】自动规则提取：极致正则表达式暴力去除非地名文字"""
    if not text: return ""
    # 1. 最核心：删掉所有括号及其内容 (车程约3h)
    clean_text = re.sub(r'\(.*?\)', ' ', text)
    clean_text = re.sub(r'（.*?）', ' ', clean_text)
    # 2. 精准剔除日期 (如4.11)
    clean_text = re.sub(r'\d+\.?\d*', ' ', clean_text)
    
    # 3. 过滤掉常见干扰词
    for word in ['接', '送', '前往', '返程', '车程', '约', 'h', '住', '陶阳里', '滕王阁', '陶溪川']:
        clean_text = clean_text.replace(word, ' ')
    
    # 4. 针对昨天那连在一起的词，可以用正则拆分预处理（因为规则提取不能理解意思）
    clean_text = re.sub(r'陶阳里滕王阁', '陶阳里 滕王阁', clean_text)
        
    return " ".join(clean_text.split()).strip()

# ==================== 3. 侧边栏：核心报价计费 ====================

if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

with st.sidebar:
    st.header("📊 报价核算中心")
    # 需求修改 1：取消折叠，常开
    st.subheader("⚙️ 计费标准设置")
    col_a, col_b = st.columns(2)
    b39 = col_a.number_input("39座起步费", value=800)
    p39 = col_b.number_input("39座单价", value=2.6)
    b56 = col_a.number_input("56座起步费", value=1000)
    p56 = col_b.number_input("56座单价", value=3.6)

    st.divider()
    # 这里的公里优先读取地图计算的记忆值
    f_km = st.number_input("实测总公里 (KM)", value=st.session_state['km_auto'])
    f_days = st.number_input("用车总天数 (天)", value=4)
    
    res_39 = int(f_km * p39 + f_days * b39)
    res_56 = int(f_km * p56 + f_days * b56)
    
    st.markdown("### 💰 实时总报单")
    st.success(f"🚌 **39座大巴：{res_39} 元**")
    st.info(f"🚌 **56座大巴：{res_56} 元**")

    # 需求修改 2：增加可复制发送文本框
    st.divider()
    st.markdown("📄 **报价发送文案 (全选复制)**")
    quote_text = (
        f"【九江祥隆旅游运输报价单】\n"
        f"实测公里数：{f_km} KM\n"
        f"用车总天数：{f_days} 天\n"
        f"--------------------\n"
        f"🚌 39座大巴全包价：{res_39} 元\n"
        f"🚌 56座大巴全包价：{res_56} 元\n"
        f"（包含全包车费用）"
    )
    st.text_area("直接复制此文字发给客户：", value=quote_text, height=180)

# ==================== 4. 主页面：流程操作 ====================
st.header("🚌 九江祥隆旅游运输报价系统 (AI 旗舰版)")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.markdown("### 1️⃣ 行程文字识别 (OCR)")
    up_file = st.file_uploader("上传截图", type=["jpg", "png", "jpeg"])
    if up_file:
        img_bytes = up_file.read()
        st.image(img_bytes, width=30
