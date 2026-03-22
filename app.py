import streamlit as st
import pandas as pd
import requests
import base64
import json
import re

# ==================== 1. 核心密钥配置 (请在此替换新 Key) ====================
# [注意] 请前往百度千帆控制台 -> 应用接入 -> 应用列表 创建应用获取 API Key 和 Secret Key
AI_API_KEY = "这里填入你的新API_Key"
AI_SECRET_KEY = "这里填入你的新Secret_Key" 

# 百度 OCR 密钥 (已配置)
BAIDU_OCR_KEY = "1vBiCqNtSYFRx6GYsGwpwXdM"         
BAIDU_OCR_SECRET = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  

# 高德地图密钥 (已配置)
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统-AI旗舰版", layout="wide")

# ==================== 2. 界面样式定制 ====================
st.markdown("""
    <style>
    .block-container {padding-top: 1rem !important;}
    [data-testid="stSidebar"] {background-color: #f0f2f6; min-width: 280px;}
    .q-table { font-size: 0.95rem; border-collapse: collapse; width: 100%; margin-top: 10px; border-radius: 8px; overflow: hidden;}
    .q-table td, .q-table th { border: 1px solid #ddd; padding: 10px; text-align: center; }
    .stNumberInput div div input { font-size: 1.1rem !important; color: #1e88e5 !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

# ==================== 3. 核心功能引擎 ====================

def get_access_token(api_key, secret_key):
    """获取百度 API 访问凭证"""
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
    try:
        res = requests.get(url).json()
        return res.get("access_token")
    except: return None

def ocr_engine(file_bytes):
    """高精度 OCR 识别"""
    token = get_access_token(BAIDU_OCR_KEY, BAIDU_OCR_SECRET)
    if not token: return "OCR 授权失败"
    img64 = base64.b64encode(file_bytes).decode()
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token={token}"
    try:
        res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
        return "".join([i['words'] for i in res.get('words_result', [])])
    except: return "OCR识别异常"

def ai_extract_locations_v2(text):
    """【方案A】大模型强力提取地名（针对末尾南昌进行了优化）"""
    token = get_access_token(AI_API_KEY, AI_SECRET_KEY)
    if not token: return "AI 授权失败，请检查密钥"
    
    # 采用性能最佳的 ERNIE-Speed-128K 接口
    url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-128k?access_token={token}"
    
    prompt = (
        f"你是一个旅游调配专家。请从以下行程描述中提取所有的【目的地地名】或【城市名】。\n"
        f"特别注意：严禁漏掉结尾处的返程城市名（如：'南昌返程'，必须提取出'南昌'两个字）。\n"
        f"要求：\n"
        f"1. 只输出地名，地名之间用【空格】分隔。\n"
        f"2. 严禁输出数字、标点符号、或‘目的地：’等提示性文字。\n"
        f"3. 即使地名连在一起（如：陶阳里滕王阁），也请拆开为独立的地点。\n"
        f"原文：{text}"
    )
    
    payload = json.dumps({
        "messages": [{"role": "user", "content": prompt}]
    })
    
    try:
        response = requests.post(url, data=payload, headers={'Content-Type': 'application/json'})
        res = response.json()
        if "error_code" in res:
            return f"AI 错误({res['error_code']}): {res.get('error_msg')}"
        
        raw_result = res.get("result", "").strip()
        
        # 二次清理：强力去除数字和常见干扰动词
        clean_text = re.sub(r'\d+', ' ', raw_result)
        for junk in ["目的地", "地名", "地点", "：", ":", ".", "、", "返程", "前往", "回", "住", "车程"]:
            clean_text = clean_text.replace(junk, " ")
        
        # 确保空格干净
        return " ".join(clean_text.split())
    except: return "AI 通信异常"

def rule_extract_locations(text):
    """【方案B】规则（自动）识别（不限模型额度，基础版）"""
    if not text: return ""
    # 1. 清理：去掉所有数字、括号和时间
    clean_text = re.sub(r'\d+', '', text)
    clean_text = re.sub(r'\(.*?\)', '', clean_text)
    # 2. 移除干扰动词
    for word in ['接', '送', '住', '前往', '返程', '车程', '约', 'h', '住', '陶阳里', '滕王阁']: # 如果陶阳里和滕王阁在OCR中经常连在一起，可以在这里做预处理
        clean_text = clean_text.replace(word, ' ')
    # 3. 如果需要对陶阳里和滕王阁做特殊处理，可以用正则拆分
    clean_text = re.sub(r'陶阳里滕王阁', '陶阳里 滕王阁', clean_text)
    return " ".join(clean_text.split()).strip()

# ==================== 4. 侧边栏：核心报价计费 ====================
with st.sidebar:
    st.header("📊 报价核算中心")
    
    # --- 需求修改 1：计费标准设置不再折叠 ---
    st.subheader("⚙️ 计费标准设置")
    col_a, col_b = st.columns(2)
    b39 = col_a.number_input("39座起步费", value=800)
    p39 = col_b.number_input("39座单价", value=2.6)
    b56 = col_a.number_input("56座起步费", value=1000)
    p56 = col_b.number_input("56座单价", value=3.6)

    st.divider()
    f_km = st.number_input("实测总公里 (KM)", value=st.session_state['km_auto'])
    f_days = st.number_input("用车总天数 (天)", value=4)
    
    res_39 = int(f_km * p39 + f_days * b39)
    res_56 = int(f_km * p56 + f_days * b56)
    
    st.markdown("### 💰 实时总报单")
    st.success(f"🚌 **39座大巴：{res_39} 元**")
    st.info(f"🚌 **56座大巴：{res_56} 元**")

    # --- 需求修改 2：增加可复制发送结果文本框 ---
    st.divider()
    st.markdown("📄 **报价结果 (直接复制发送)**")
    quote_text = (
        f"【九江祥隆旅游运输报价单】\n"
        f"总里程：{f_km} KM\n"
        f"用车天数：{f_days} 天\n"
        f"--------------------\n"
        f"🚌 39座大巴单价：{res_39} 元\n"
        f"🚌 56座大巴单价：{res_56} 元\n"
        f"（包含全包车费用）"
    )
    st.text_area("复制下方文字：", value=quote_text, height=150)

# ==================== 5. 主页面：流程操作 ====================
st.header("🚌 九江祥隆旅游运输报价系统 (AI 旗舰版)")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.markdown("### 1️⃣ 行程识别与站点提取")
    up_file = st.file_uploader("上传行程截图", type=["jpg", "png", "jpeg"])
    if up_file:
        img_bytes = up_file.read()
        st.image(img_bytes, width=300)
        if st.button("🚀 开始文字识别 (OCR)", use_container_width=True):
            st.session_state['ocr_raw'] = ocr_engine(img_bytes)
    
    raw_txt = st.text_area("识别文本校对：", value=st.session_state.get('ocr_raw', ""), height=150)
    
    st.markdown("---")
    # --- 需求修改 3：保留两套提取方案 ---
    st.markdown("#### **站点提取方案选择 (双模)**")
    c1, c2 = st.columns(2)
    
    if c1.button("✨ 强力 AI 提取 (抓捕南昌)", use_container_width=True):
        if raw_txt:
            st.session_state['sites_final'] = ai_extract_locations_v2(raw_txt)
        else:
            st.warning("请上传截图或输入文字")

    if c2.button("🤖 自动(规则)提取 (免费兜底)", use_container_width=True):
        if raw_txt:
            st.session_state['sites_final'] = rule_extract_locations(raw_txt)
        else:
            st.warning("请上传截图或输入文字")

with m_right:
    st.markdown("### 2️⃣ 站点确认与地图测距")
    site_input = st.text_input("待匹配地名 (空格隔开)：", value=st.session_state.get('sites_final', ""))
    
    confirmed_locs = []
    if site_input:
        names = site_input.split()
        for i, name in enumerate(names):
            if not name.strip(): continue
            # 调用高德 API 搜索地点建议
            url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
            try:
                tips = requests.get(url).json().get('tips', [])
                valid_tips = [t for t in tips if t.get('location')]
                if valid_tips:
                    sel = st.selectbox(f"确认第 {i+1} 站: {name}", [f"{t['name']} ({t.get('district','')})" for t in valid_tips], key=f"site_v3_{i}")
                    coord = next(t['location'] for t in valid_tips if sel.startswith(t['name']))
                    confirmed_locs.append(coord)
            except: pass

    # 路径测距逻辑
    if len(confirmed_locs) >= 2:
        st.divider()
        org, des = confirmed_locs[0], confirmed_locs[-1]
        way = ";".join(confirmed_locs[1:-1])
        r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way if way else ''}"
        
        try:
            res = requests.get(r_url).json()
            if res['status'] == '1' and res['route']['paths']:
                km = int(round(int(res['route']['paths'][0]['distance']) / 1000))
                st.session_state['km_auto'] = km
                st.success(f"🚩 规划成功！总公里数：{km} KM")
                if st.button("✅ 更新里程到报价单"): st.rerun()
            else: st.error("高德地图无法计算此路径，请检查站点选择是否模糊")
        except: st.error("地图测距服务异常")
