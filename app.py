import streamlit as st
import pandas as pd
import requests
import re
import base64
import json
import time

# ==================== 1. 核心密钥与配置 ====================
AI_API_KEY_V2 = "bce-v3/ALTAK-EMZixkEbLJ0iEkFcaJCFc/74514893890101d198dd642b3b95ea68bed95897"
BAIDU_OCR_AK = "1vBiCqNtSYFRx6GYsGwpwXdM"         
BAIDU_OCR_SK = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统-旗舰版", layout="wide", page_icon="🚌")

# 样式美化
st.markdown("""
<style>
    .main-header { background: linear-gradient(135deg, #1a3a5c 0%, #2563a8 100%); color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; }
    .stButton > button { border-radius: 8px !important; }
    .station-box { background: #f8fafc; border-radius: 10px; border: 1px solid #e2e8f0; padding: 15px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# 状态初始化
_defaults = {
    'ocr_raw': "", 
    'sites_preview': "",   
    'confirmed_sites': [], 
    'km_auto': 0
}
for k, v in _defaults.items():
    if k not in st.session_state: st.session_state[k] = v

# ==================== 2. 后端引擎函数 ====================

# 【新增优化：缓存搜索结果】设置 1 小时缓存，避免重复请求高德 API 导致卡顿
@st.cache_data(ttl=3600, show_spinner=False)
def get_amap_tips(keyword):
    if not keyword: return []
    url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={keyword}&key={AMAP_KEY}"
    try:
        res = requests.get(url, timeout=5).json()
        tips = res.get('tips', [])
        # 只保留有具体坐标的结果
        return [t for t in tips if isinstance(t.get('location'), str) and t.get('location')]
    except:
        return []

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

def ai_extract_locations(text):
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-128k"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {AI_API_KEY_V2}"}
    prompt = f"你是一个专业的旅游调度。请从以下文本提取目的地地名，用空格分隔。不要输出无关词汇。原文：{text}"
    payload = {"messages": [{"role": "user", "content": prompt}]}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15).json()
        return res.get("result", "").strip()
    except: return ""

def rule_extract_locations(text):
    if not text: return ""
    clean = re.sub(r'\(.*?\)|（.*?）|\d+\.?\d*|[^\u4e00-\u9fa5\s]', ' ', text)
    for word in ['接', '送', '前往', '返程', '车程', '住', '公里']:
        clean = clean.replace(word, ' ')
    return " ".join(clean.split()).strip()

# ==================== 3. 界面布局 ====================

# --- 左侧：报价核算中心 ---
with st.sidebar:
    st.header("📊 报价核算中心")
    with st.expander("⚙️计费标准设置", expanded=True):
        col_a, col_b = st.columns(2)
        b39 = col_a.number_input("39起步费", 800)
        p39 = col_b.number_input("39单价", 2.6)
        b56 = col_a.number_input("56起步费", 1000)
        p56 = col_b.number_input("56单价", 3.6)
    
    st.divider()
    f_km = st.number_input("实测总公里 (KM)", value=st.session_state['km_auto'])
    f_days = st.number_input("用车总天数", value=4)
    
    res_39 = int(f_km * p39 + f_days * b39)
    res_56 = int(f_km * p56 + f_days * b56)
    
    st.metric("39座预估", f"{res_39} 元")
    st.metric("56座预估", f"{res_56} 元")
    
    st.divider()
    quote_text = f"【九江祥隆报价单】\n里程：{f_km}KM | 天数：{f_days}天\n---\n39座大巴：{res_39}元\n56座大巴：{res_56}元"
    st.text_area("报价文案：", value=quote_text, height=120)

# --- 主界面 ---
st.markdown('<div class="main-header"><h1>🚌 九江祥隆旅游运输报价系统</h1><p>旗舰版 | 高速缓存优化</p></div>', unsafe_allow_html=True)

m_left, m_right = st.columns([1, 1.2])

# --- 1️⃣ 文字识别与提取 (中间) ---
with m_left:
    st.subheader("1️⃣ 行程解析提取")
    up_file = st.file_uploader("上传行程截图", type=["jpg", "png", "jpeg"])
    if up_file and st.button("🚀 识别图片文字", use_container_width=True):
        st.session_state['ocr_raw'] = ocr_engine(up_file.read())
    
    raw_txt = st.text_area("OCR识别结果：", value=st.session_state['ocr_raw'], height=150)
    
    col1, col2 = st.columns(2)
    if col1.button("✨ 智能 AI 提取", use_container_width=True):
        st.session_state['sites_preview'] = ai_extract_locations(raw_txt)
    if col2.button("🤖 自动规则提取", use_container_width=True):
        st.session_state['sites_preview'] = rule_extract_locations(raw_txt)
    
    st.divider()
    edited_sites = st.text_area("🖊️ 提取地名列表 (可在此增删改地名)", 
                                value=st.session_state['sites_preview'], 
                                height=100)
    st.session_state['sites_preview'] = edited_sites 

    if st.button("✅ 确认并同步到站点框", type="primary", use_container_width=True):
        names = re.split(r'[，,\s]+', edited_sites)
        st.session_state['confirmed_sites'] = [n.strip() for n in names if n.strip()]
        st.rerun()

# --- 2️⃣ 站点确认与公里数 (右侧) ---
with m_right:
    st.subheader("2️⃣ 站点位置确认")
    current_coords = []
    
    if not st.session_state['confirmed_sites']:
        st.info("💡 请在左侧解析地名后点击“同步”按钮")
    else:
        # 遍历确认好的地名列表
        for i, name in enumerate(st.session_state['confirmed_sites']):
            with st.container():
                st.markdown(f'<div class="station-box">', unsafe_allow_html=True)
                search_kw = st.text_input(f"站{i+1} 搜索关键词", value=name, key=f"inp_{name}_{i}")
                
                # 【优化点】使用带缓存的搜索函数，避免每次点击按钮都去联网请求高德
                valid_tips = get_amap_tips(search_kw)
                
                if valid_tips:
                    opts = [f"{t['name']} ({t.get('district','')})" for t in valid_tips]
                    sel = st.selectbox(f"确认具体位置 {i+1}", opts, key=f"sel_{name}_{i}")
                    # 匹配经纬度
                    loc = next(t['location'] for t in valid_tips if sel.startswith(t['name']))
                    current_coords.append(loc)
                else:
                    st.warning("未找到匹配位置，请修改搜索关键词")
                st.markdown('</div>', unsafe_allow_html=True)

        if len(current_coords) >= 2:
            if st.button("🗺️ 开始计算导航里程", type="primary", use_container_width=True):
                with st.spinner("正在进行路线规划..."):
                    org, des = current_coords[0], current_coords[-1]
                    way = ";".join(current_coords[1:-1])
                    d_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&waypoints={way}&key={AMAP_KEY}"
                    
                    try:
                        res = requests.get(d_url, timeout=10).json()
                        if res.get('status') == '1' and 'route' in res:
                            dist = int(res['route']['paths'][0]['distance']) / 1000
                            st.session_state['km_auto'] = int(dist)
                            st.success(f"🚩 规划成功！总里程：{int(dist)} KM")
                            st.toast("里程已同步")
                            time.sleep(0.3)
                            st.rerun()
                        else:
                            st.error(f"测距失败: {res.get('info')}")
                    except Exception as e:
                        st.error(f"网络异常: {str(e)}")
