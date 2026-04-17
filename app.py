import streamlit as st
import pandas as pd
import requests
import re
import base64
import json

# ==================== 1. 核心密钥配置 (已根据您的代码还原) ====================
BAIDU_OCR_KEY = "1vBiCqNtSYFRx6GYsGwpwXdM"        
BAIDU_OCR_SECRET = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  
AI_API_KEY = "ALTAKRoF5rezfzpBHyvueydG2B"
AI_SECRET_KEY = "10bc499df39a472d882aee64221d1e31" 
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统-完整双模版", layout="wide")

# ==================== 2. 界面样式定制 (还原您的 CSS) ====================
st.markdown("""
    <style>
    .block-container {padding-top: 1rem !important;}
    [data-testid="stSidebar"] {background-color: #f0f2f6; min-width: 280px;}
    .stNumberInput div div input {font-size: 1.1rem !important; color: #1e88e5 !important;}
    </style>
    """, unsafe_allow_html=True)

# 干扰词过滤库
BLACK_LIST = ["第一天", "第二天", "第三天", "第四天", "第五天", "第六天", "第七天", "返程", "行程", "住宿", "用餐", "含餐", "早餐", "午餐", "晚餐", "自理", "车程", "小时", "分钟", "接团", "送团", "出发", "返回", "入住", "酒店", "车费", "司机", "左右", "抵达"]

# ==================== 3. 后端核心功能 ====================
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
    """AI 智能模式"""
    token = get_access_token(AI_API_KEY, AI_SECRET_KEY)
    url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-x1-turbo-32k?access_token={token}"
    prompt = f"你是一个旅游调度。请从文字中提取纯地名，地名间用空格隔开。原文：{text}"
    payload = json.dumps({"messages": [{"role": "user", "content": prompt}]})
    try:
        res = requests.post(url, data=payload, headers={'Content-Type': 'application/json'}).json()
        return res.get("result", "").strip()
    except: return ""

# ==================== 4. 状态管理 ====================
if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0
if 'sites_list' not in st.session_state: st.session_state['sites_list'] = []
if 'confirmed_data' not in st.session_state: st.session_state['confirmed_data'] = {}

# ==================== 5. 侧边栏报价 ====================
with st.sidebar:
    st.header("📊 报价核算")
    with st.form("price_form"):
        c1, c2 = st.columns(2)
        b39, p39 = c1.number_input("39座起步", value=800), c2.number_input("39座单价", value=2.60)
        f_km = st.number_input("总公里 (KM)", value=st.session_state['km_auto'])
        f_days = st.number_input("总天数 (天)", value=4)
        st.form_submit_button("💰 更新价格")
    
    total_39 = int(f_km * p39 + f_days * b39)
    st.markdown(f"""<div style="background:#e3f2fd; padding:15px; border-radius:5px; text-align:center;">
        <h3 style="margin:0; color:#1e88e5;">39座预估: {total_39} 元</h3></div>""", unsafe_allow_html=True)

# ==================== 6. 主页面：双模提取区 ====================
st.header("🚌 九江祥隆旅游运输报价系统")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.markdown("### 1️⃣ 行程智能提取")
    up_file = st.file_uploader("上传行程截图", type=["jpg", "png", "jpeg"])
    if up_file and st.button("🚀 执行 OCR 识别"):
        st.session_state['ocr_raw'] = ocr_engine(up_file.read())
    
    raw_txt = st.text_area("识别文本校对：", value=st.session_state.get('ocr_raw', ""), height=180)
    
    # 双模提取按钮
    btn_col1, btn_col2 = st.columns(2)
    if btn_col1.button("✨ 智能 AI 提取", use_container_width=True):
        res = ai_extract_locations(raw_txt)
        st.session_state['sites_list'] = res.split()
        st.session_state['confirmed_data'] = {} # 重置已选数据
        
    if btn_col2.button("🤖 自动规则提取", use_container_width=True):
        locs = re.findall(r'[\u4e00-\u9fa5]{2,}', raw_txt)
        cleaned = [l for l in locs if l not in BLACK_LIST]
        st.session_state['sites_list'] = cleaned
        st.session_state['confirmed_data'] = {}

with m_right:
    st.markdown("### 2️⃣ 站点确认 (高德单框模式)")
    
    for i, site in enumerate(st.session_state['sites_list']):
        # 获取当前框内应显示的内容（优先显示选定的，其次显示提取的）
        current_name = st.session_state['confirmed_data'].get(i, {}).get('full_name', site)
        
        # 实时请求高德联想
        t_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={current_name}&key={AMAP_KEY}"
        try:
            tips = [t for t in requests.get(t_url).json().get('tips', []) if t.get('location')]
            if tips:
                options = [f"{t['name']} ({t.get('district','')})" for t in tips]
                # 单框模式：选择框直接承载搜索结果
                selected = st.selectbox(f"📍 站点 {i+1}", options=options, key=f"site_box_{i}")
                
                # 实时回填坐标与名称到 Session
                target = next(t for t in tips if f"{t['name']} ({t.get('district','')})" == selected)
                st.session_state['confirmed_data'][i] = {
                    "full_name": selected,
                    "coord": target['location']
                }
            else:
                st.warning(f"站点 {i+1}: '{current_name}' 未找到精准定位")
        except:
            pass

    # ==================== 7. 路径规划控制器 ====================
    st.divider()
    if len(st.session_state['confirmed_data']) >= 2:
        if st.button("🗺️ 确认所有地址，生成导航里程", use_container_width=True, type="primary"):
            keys = sorted(st.session_state['confirmed_data'].keys())
            coords = [st.session_state['confirmed_data'][k]['coord'] for k in keys]
            
            org, des, way = coords[0], coords[-1], ";".join(coords[1:-1])
            r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way}"
            
            try:
                res = requests.get(r_url).json()
                if res['status'] == '1':
                    km = int(int(res['route']['paths'][0]['distance']) / 1000)
                    st.session_state['km_auto'] = km
                    st.success(f"✅ 计算成功！总行程：{km} 公里")
                    st.rerun()
                else:
                    st.error("高德路径规划失败")
            except:
                st.error("网络连接异常")
