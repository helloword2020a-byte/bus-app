import streamlit as st
import requests
import re
import base64
import json

# ==================== 1. 核心密钥配置 ====================
BAIDU_OCR_KEY = "1vBiCqNtSYFRx6GYsGwpwXdM"        
BAIDU_OCR_SECRET = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  
AI_API_KEY = "ALTAKRoF5rezfzpBHyvueydG2B"
AI_SECRET_KEY = "10bc499df39a472d882aee64221d1e31" 
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统-极速联想版", layout="wide")

# ==================== 2. 地址过滤“黑名单”库 ====================
BLACK_LIST = [
    "第一天", "第二天", "第三天", "第四天", "第五天", "第六天", "第七天", "返程", "行程", 
    "住宿", "用餐", "含餐", "早餐", "午餐", "晚餐", "自理", "车程", "小时", "分钟", 
    "接团", "送团", "出发", "返回", "入住", "酒店", "车费", "司机", "左右", "抵达"
]

def clean_locations(text_list):
    """过滤规则提取中的干扰词"""
    return [loc for loc in text_list if loc not in BLACK_LIST and len(loc) > 1]

# ==================== 3. 核心功能引擎 ====================
def get_access_token(api_key, secret_key):
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
    try: return requests.get(url).json().get("access_token")
    except: return None

def ocr_engine(file_bytes):
    token = get_access_token(BAIDU_OCR_KEY, BAIDU_OCR_SECRET)
    if not token: return "OCR 授权失败"
    img64 = base64.b64encode(file_bytes).decode()
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token={token}"
    res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
    return "".join([i['words'] for i in res.get('words_result', [])])

def ai_extract_locations(text):
    token = get_access_token(AI_API_KEY, AI_SECRET_KEY)
    url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-x1-turbo-32k?access_token={token}"
    prompt = f"你是一个旅游调度。请从文字中提取纯地名，地名间用空格隔开。原文：{text}"
    payload = json.dumps({"messages": [{"role": "user", "content": prompt}]})
    try:
        res = requests.post(url, data=payload, headers={'Content-Type': 'application/json'}).json()
        return res.get("result", "").strip()
    except: return ""

# ==================== 4. 状态与计费初始化 ====================
if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0
if 'confirmed_coords' not in st.session_state: st.session_state['confirmed_coords'] = {} 
if 'confirmed_names' not in st.session_state: st.session_state['confirmed_names'] = {}

# 侧边栏：加入 Form 锁定计费，防止输入时页面刷新
with st.sidebar:
    st.header("📊 报价核算中心")
    with st.form("calc_form"):
        st.subheader("⚙️ 计费标准")
        c1, c2 = st.columns(2)
        b39, p39 = c1.number_input("39座起步", value=800), c2.number_input("39座单价", value=2.6)
        b56, p56 = c1.number_input("56座起步", value=1000), c2.number_input("56座单价", value=3.6)
        st.divider()
        f_km = st.number_input("总公里 (KM)", value=st.session_state['km_auto'])
        f_days = st.number_input("总天数 (天)", value=4)
        if st.form_submit_button("💰 更新总报价"): pass # 仅触发表单刷新
        
    res_39, res_56 = int(f_km*p39 + f_days*b39), int(f_km*p56 + f_days*b56)
    st.markdown(f"""<div style="background:#e3f2fd; padding:10px; border-radius:5px;">
        <h4 style="margin:0">39座：{res_39} 元</h4><h4 style="margin:5px 0 0 0">56座：{res_56} 元</h4></div>""", unsafe_allow_html=True)

# ==================== 5. 主页面：流程操作 ====================
st.header("🚌 九江祥隆旅游运输报价系统")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.markdown("### 1️⃣ 行程识别与提取")
    up_file = st.file_uploader("上传截图", type=["jpg", "png", "jpeg"])
    if up_file and st.button("🚀 开始识别", use_container_width=True):
        st.session_state['ocr_raw'] = ocr_engine(up_file.read())
    
    raw_txt = st.text_area("识别文本校对：", value=st.session_state.get('ocr_raw', ""), height=150)
    
    col_btn1, col_btn2 = st.columns(2)
    if col_btn1.button("✨ 智能 AI 提取", use_container_width=True):
        st.session_state['sites_final'] = ai_extract_locations(raw_txt)
    if col_btn2.button("🤖 自动规则提取", use_container_width=True):
        # 正则提取 + 黑名单过滤
        locs = re.findall(r'[\u4e00-\u9fa5]{2,}', raw_txt)
        st.session_state['sites_final'] = " ".join(clean_locations(locs))

with m_right:
    st.markdown("### 2️⃣ 站点校对 (实时联想 10 项)")
    site_input = st.text_input("待匹配关键词 (空格隔开)：", value=st.session_state.get('sites_final', ""))
    
    if site_input:
        names = site_input.split()
        for i, name in enumerate(names):
            with st.container(border=True):
                # 实时输入即联想逻辑
                kw = st.text_input(f"站 {i+1} 搜索词", value=name, key=f"kw_{i}")
                t_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={kw}&key={AMAP_KEY}"
                try:
                    tips = [t for t in requests.get(t_url).json().get('tips', []) if t.get('location')][:10]
                    if tips:
                        opts = [f"{t['name']} ({t.get('district','')})" for t in tips]
                        # 默认增加一个未选择项，防止自动锁定第一个
                        sel = st.selectbox("🎯 确认为：", ["-- 请选择 --"] + opts, key=f"sel_{i}")
                        if sel != "-- 请选择 --":
                            idx = opts.index(sel)
                            st.session_state['confirmed_coords'][i] = tips[idx]['location']
                            st.session_state['confirmed_names'][i] = sel.split(" (")[0]
                            st.caption(f"✅ 已选中坐标: {st.session_state['confirmed_coords'][i]}")
                    else: st.caption("🔍 未找到候选地址")
                except: pass

    # 【新增】手动控制按钮，点击后才进行测距并跳转页面
    st.divider()
    if len(st.session_state['confirmed_coords']) >= 2:
        if st.button("🗺️ 确认所有站点，开始规划行程", use_container_width=True, type="primary"):
            keys = sorted(st.session_state['confirmed_coords'].keys())
            coords = [st.session_state['confirmed_coords'][k] for k in keys]
            org, des, way = coords[0], coords[-1], ";".join(coords[1:-1])
            
            r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way}"
            try:
                res = requests.get(r_url).json()
                st.session_state['km_auto'] = int(int(res['route']['paths'][0]['distance']) / 1000)
                st.success(f"规划完成！总公里数: {st.session_state['km_auto']} KM")
                st.rerun() 
            except: st.error("地图测距失败")
