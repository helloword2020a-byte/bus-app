import streamlit as st
import requests
import re
import base64
import json

# ==================== 1. 核心密钥配置 (已根据您的截图还原) ====================
BAIDU_OCR_KEY = "1vBiCqNtSYFRx6GYsGwpwXdM"        
BAIDU_OCR_SECRET = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  
AI_API_KEY = "ALTAKRoF5rezfzpBHyvueydG2B"
AI_SECRET_KEY = "10bc499df39a472d882aee64221d1e31" 
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆-单框高德模式", layout="wide")

# ==================== 2. 核心后端引擎 ====================
def get_access_token(api_key, secret_key):
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
    try: return requests.get(url).json().get("access_token")
    except: return None

def ocr_engine(file_bytes):
    token = get_access_token(BAIDU_OCR_KEY, BAIDU_OCR_SECRET)
    img64 = base64.b64encode(file_bytes).decode()
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token={token}"
    res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
    return "".join([i['words'] for i in res.get('words_result', [])])

def ai_extract_locations(text):
    """回归的 AI 提取功能"""
    token = get_access_token(AI_API_KEY, AI_SECRET_KEY)
    url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-x1-turbo-32k?access_token={token}"
    prompt = f"你是一个旅游调度。请从文字中提取纯地名，地名间用空格隔开，不要任何解释。原文：{text}"
    payload = json.dumps({"messages": [{"role": "user", "content": prompt}]})
    try:
        res = requests.post(url, data=payload, headers={'Content-Type': 'application/json'}).json()
        return res.get("result", "").strip()
    except: return ""

# ==================== 3. 状态管理 ====================
if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0
if 'confirmed_data' not in st.session_state: st.session_state['confirmed_data'] = {}

# ==================== 4. 侧边栏报价 (已锁定) ====================
with st.sidebar:
    st.header("📊 报价核算")
    with st.form("price_f"):
        c1, c2 = st.columns(2)
        b39, p39 = c1.number_input("39座起步", value=800), c2.number_input("39座单价", value=2.6)
        f_km = st.number_input("公里数", value=st.session_state['km_auto'])
        f_days = st.number_input("天数", value=4)
        st.form_submit_button("💰 计算报价")
    st.info(f"39座预估：{int(f_km*p39 + f_days*b39)} 元")

# ==================== 5. 主页面交互 ====================
st.title("🚌 九江祥隆报价系统 (单框搜索模式)")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.markdown("### 1️⃣ 行程智能提取")
    up_file = st.file_uploader("上传截图", type=["jpg", "png", "jpeg"])
    if up_file and st.button("🚀 开始识别", use_container_width=True):
        st.session_state['ocr_raw'] = ocr_engine(up_file.read())
    
    raw_txt = st.text_area("识别文本：", value=st.session_state.get('ocr_raw', ""), height=150)
    
    # AI 提取按钮回归
    if st.button("✨ 智能 AI 提取地点", use_container_width=True, type="primary"):
        extracted = ai_extract_locations(raw_txt)
        st.session_state['sites_list'] = extracted.split()

with m_right:
    st.markdown("### 2️⃣ 站点校对 (输入即搜索)")
    
    sites = st.session_state.get('sites_list', [])
    for i, site in enumerate(sites):
        with st.container(border=True):
            # 获取当前搜索词：如果是首次加载显示AI提取的，如果手动选了就显示选中的名
            current_label = st.session_state['confirmed_data'].get(i, {}).get('name', site)
            
            # 【核心逻辑】：用 st.selectbox 模拟搜索框
            # 这里的 index=0 保证了默认显示 AI 识别的结果
            t_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={current_label}&key={AMAP_KEY}"
            try:
                tips = [t for t in requests.get(t_url).json().get('tips', []) if t.get('location')][:10]
                options = [f"{t['name']} ({t.get('district','')})" for t in tips]
                
                # 如果用户想手动改，这里可以通过 index 逻辑切换
                sel = st.selectbox(f"📍 站点 {i+1}", options=options, key=f"sel_{i}")
                
                # 实时锁定数据到后台
                idx = options.index(sel)
                st.session_state['confirmed_data'][i] = {
                    "name": tips[idx]['name'],
                    "coord": tips[idx]['location']
                }
            except:
                st.error(f"站点 {i+1} 联想失败")

    # ==================== 6. 路径计算 (不点不动) ====================
    st.divider()
    if len(st.session_state['confirmed_data']) >= 2:
        if st.button("🗺️ 确认所有地址，生成导航里程", use_container_width=True, type="primary"):
            keys = sorted(st.session_state['confirmed_data'].keys())
            coords = [st.session_state['confirmed_data'][k]['coord'] for k in keys]
            
            org, des, way = coords[0], coords[-1], ";".join(coords[1:-1])
            r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way}"
            
            try:
                res = requests.get(r_url).json()
                km = int(int(res['route']['paths'][0]['distance']) / 1000)
                st.session_state['km_auto'] = km
                st.success(f"✅ 计算成功！里程：{km} KM")
                st.rerun() 
            except:
                st.error("测距接口调用失败")
