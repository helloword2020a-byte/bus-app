import streamlit as st
import pandas as pd
import requests
import re
import base64
import json

# --- 1. 基础配置 ---
# 百度 OCR 密钥 (保持您原有的)
BAIDU_API_KEY = "1vBiCqNtSYFRx6GYsGwpwXdM"        
BAIDU_SECRET_KEY = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  
# 百度千帆 AI 密钥 (用于接入 ERNIE-Speed-Pro-128K)
AI_API_KEY = "bce-v3/ALTAK-9aoqLxWVRWAlk87GMFUI6/4bd21140ab38b1883ea5fa7608063fecf89c5bd2"
AI_SECRET_KEY = "这里请替换为您页面显示的Secret_Key" 

AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统-智能旗舰版", layout="wide")

# --- 2. 界面样式 (保留您的原生样式) ---
st.markdown("""
    <style>
    .block-container {padding-top: 1rem !important;}
    [data-testid="stSidebar"] {background-color: #f0f2f6; min-width: 250px;}
    .q-table { font-size: 0.95rem; border-collapse: collapse; width: 100%; margin-top: 10px; border-radius: 8px; overflow: hidden;}
    .q-table td, .q-table th { border: 1px solid #ddd; padding: 8px; text-align: center; }
    .stNumberInput div div input { font-size: 1.1rem !important; color: #1e88e5 !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

# --- 3. 核心引擎：OCR + AI 逻辑 ---

def get_access_token(api_key, secret_key):
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
    try: return requests.get(url).json().get("access_token")
    except: return None

def ocr_engine(file_bytes):
    token = get_access_token(BAIDU_API_KEY, BAIDU_SECRET_KEY)
    if not token: return "授权失败"
    img64 = base64.b64encode(file_bytes).decode()
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token={token}"
    res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
    return "".join([i['words'] for i in res.get('words_result', [])])

def ai_extract_locations(text):
    """【新增】接入 ERNIE-Speed-Pro-128K 进行智能地名提取"""
    token = get_access_token(AI_API_KEY, AI_SECRET_KEY)
    if not token: return "AI 授权失败"
    
    url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-pro-128k?access_token={token}"
    
    # 精准控制：只让 AI 输出地名，解决“南昌接”变“理发店”的问题
    prompt = f"""你是一个旅游计调。请从这段OCR文字中提取出行程经过的所有真实地名。
    要求：1. 删掉所有动作词（如：接、送、住、车程、简易行程、约3h）。
    2. 比如“南昌接”提取为“南昌”，“住大觉山”提取为“大觉山”。
    3. 只按顺序输出地名，中间用空格隔开，不要任何解释。
    文字内容：{text}"""
    
    payload = json.dumps({"messages": [{"role": "user", "content": prompt}]})
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers, data=payload).json()
    return response.get("result", "").strip()

# --- 4. 侧边栏：核心报价工作台 (保留您的计算逻辑) ---
with st.sidebar:
    st.header("📊 报价核算中心")
    with st.expander("⚙️ 计费标准设置", expanded=False):
        c1, c2 = st.columns(2)
        b39 = c1.number_input("39座起步", value=800)
        p39 = c2.number_input("39座单价", value=2.6)
        b56 = c1.number_input("56座起步", value=1000)
        p56 = c2.number_input("56座单价", value=3.6)

    st.divider()
    st.subheader("📝 核心报单参数")
    f_km = st.number_input("实测总公里 (KM)", value=st.session_state['km_auto'])
    f_days = st.number_input("用车总天数 (天)", value=4)
    
    res_39 = int(f_km * p39 + f_days * b39)
    res_56 = int(f_km * p56 + f_days * b56)
    
    st.markdown("### 💰 实时总报单")
    st.markdown(f"""
    <table class="q-table">
        <tr style="background-color:#1e88e5; color:white;"><th>车型</th><th>总报价</th></tr>
        <tr><td>39座大巴</td><td><b>{res_39} 元</b></td></tr>
        <tr><td>56座大巴</td><td><b>{res_56} 元</b></td></tr>
    </table>
    """, unsafe_allow_html=True)

# --- 5. 主页面布局 (承上启下的核心集成) ---
st.header("🚌 九江祥隆旅游运输报价系统 (AI 旗舰整合版)")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.markdown("### 1️⃣ 行程 AI 智能识别")
    up_file = st.file_uploader("粘贴或上传行程截图", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
    if up_file:
        img_bytes = up_file.read()
        st.image(img_bytes, width=320)
        if st.button("🚀 开始高精度文字识别", use_container_width=True):
            st.session_state['ocr_raw'] = ocr_engine(img_bytes)
    
    raw_txt = st.text_area("识别文本校对：", value=st.session_state.get('ocr_raw', ""), height=150)
    
    # 这一步，我们用大模型取代了您之前的正则清洗逻辑
    if st.button("✨ 大模型智能提取路径 (ERNIE 旗舰驱动)", use_container_width=True):
        if raw_txt:
            with st.spinner('AI 正在深度思考提取地名...'):
                clean_sites = ai_extract_locations(raw_txt)
                st.session_state['sites_final'] = clean_sites
        else:
            st.error("请先识别行程文字")

with m_right:
    st.markdown("### 2️⃣ 站点确认与地图测距")
    st.caption("提示：AI 已为您过滤多余词汇，可手动微调，地图将实时重算。")
    # 这里承接 AI 提取出来的纯地名串
    site_input = st.text_input("待匹配关键词：", value=st.session_state.get('sites_final', ""), label_visibility="collapsed")
    
    confirmed_locs = []
    if site_input:
        names = site_input.split()
        grid = st.columns(2)
        for i, name in enumerate(names):
            with grid[i % 2]:
                url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
                try:
                    tips = requests.get(url).json().get('tips', [])
                    valid_tips = [t for t in tips if t.get('location')]
                    if not valid_tips: continue
                    sel = st.selectbox(f"站点{i+1}: {name}", [f"{t['name']} ({t.get('district','')})" for t in valid_tips], key=f"sel_{i}")
                    coord = next(t['location'] for t in valid_tips if t['name'] == sel.split(" (")[0])
                    confirmed_locs.append(coord)
                except: pass

    # 路径规划与里程同步逻辑 (保持您原有的高效逻辑)
    if len(confirmed_locs) >= 2:
        try:
            org, des, way = confirmed_locs[0], confirmed_locs[-1], ";".join(confirmed_locs[1:-1])
            r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way if len(confirmed_locs)>2 else ''}"
            res = requests.get(r_url).json()
            km_val = int(round(int(res['route']['paths'][0]['distance']) / 1000))
            st.session_state['km_auto'] = km_val
            st.success(f"🚩 路线规划成功！实测公里：{km_val} KM。")
            st.info("数据已同步至左侧【实测总公里】，最终报价已刷新。")
        except:
            st.error("地图测距失败，请微调站点名称")
