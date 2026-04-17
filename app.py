import streamlit as st
import pandas as pd
import requests
import re
import base64
import json

# ==================== 1. 核心密钥配置 (完整保留) ====================

AI_API_KEY_V2 = "bce-v3/ALTAK-EMZixkEbLJ0iEkFcaJCFc/74514893890101d198dd642b3b95ea68bed95897"
BAIDU_OCR_AK = "1vBiCqNtSYFRx6GYsGwpwXdM"         
BAIDU_OCR_SK = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统-旗舰版", layout="wide")

# 初始化状态管理器，确保数据不丢失
if 'ocr_raw' not in st.session_state: st.session_state['ocr_raw'] = ""
if 'sites_list' not in st.session_state: st.session_state['sites_list'] = []
if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0
if 'confirmed_coords' not in st.session_state: st.session_state['confirmed_coords'] = {}

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
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-128k"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {AI_API_KEY_V2}"}
    prompt = (f"你是一个专业的旅游行程调度专家。请从以下文本中提取所有的目的地地名。要求：只输出地名，地名之间用空格分隔。原文：{text}")
    payload = {"messages": [{"role": "user", "content": prompt}]}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        res = response.json()
        if "result" in res:
            raw_result = res.get("result", "").strip()
            clean_text = re.sub(r'[^\u4e00-\u9fa5\s]', ' ', raw_result)
            return " ".join(clean_text.split())
        else: return ""
    except: return ""

def rule_extract_locations(text):
    if not text: return ""
    clean = re.sub(r'\(.*?\)|（.*?）|\d+\.?\d*|[^\u4e00-\u9fa5\s]', ' ', text)
    for word in ['接', '送', '前往', '返程', '车程', '约', '住', '下午', '简易行程', '小时', '公里']:
        clean = clean.replace(word, ' ')
    clean = clean.replace("陶阳里滕王阁", "陶阳里 滕王阁")
    return " ".join(clean.split()).strip()

# ==================== 3. 侧边栏：报价核算 (加入 Form 锁定) ====================

with st.sidebar:
    st.header("📊 报价核算中心")
    # 使用 form 包裹，只有点按钮才会刷新价格，防止修改公里数页面就重跑
    with st.form("price_calc_form"):
        st.subheader("⚙️ 计费标准设置")
        col_a, col_b = st.columns(2)
        b39 = col_a.number_input("39起步费", value=800)
        p39 = col_b.number_input("39单价", value=2.6)
        b56 = col_a.number_input("56起步费", value=1000)
        p56 = col_b.number_input("56单价", value=3.6)
        
        st.divider()
        f_km = st.number_input("总公里 (KM)", value=st.session_state['km_auto'])
        f_days = st.number_input("用车总天数", value=4)
        
        calc_submit = st.form_submit_button("💰 更新报价文案")

    res_39 = int(f_km * p39 + f_days * b39)
    res_56 = int(f_km * p56 + f_days * b56)
    st.success(f"39座：{res_39} 元 | 56座：{res_56} 元")
    
    st.divider()
    quote_text = f"【九江祥隆报价单】\n里程：{f_km}KM | 天数：{f_days}天\n---\n39座大巴：{res_39}元\n56座大巴：{res_56}元"
    st.text_area("复制文案：", value=quote_text, height=120)

# ==================== 4. 主页面 ====================

st.header("🚌 九江祥隆旅游运输报价系统 (AI 旗舰版)")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.subheader("1️⃣ 文字识别与提取")
    up_file = st.file_uploader("上传行程截图", type=["jpg", "png", "jpeg"])
    if up_file and st.button("🚀 开始文字提取识别", use_container_width=True):
        st.session_state['ocr_raw'] = ocr_engine(up_file.read())
    
    raw_txt = st.text_area("识别结果校对：", value=st.session_state.get('ocr_raw', ""), height=200)
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    # 双模按钮完整保留
    if col1.button("✨ 智能 AI 提取", use_container_width=True):
        st.session_state['sites_list'] = ai_extract_locations_v2(raw_txt).split()
    if col2.button("🤖 自动规则提取", use_container_width=True):
        st.session_state['sites_list'] = rule_extract_locations(raw_txt).split()

with m_right:
    st.subheader("2️⃣ 站点确认 (高德实时联想)")
    
    sites = st.session_state.get('sites_list', [])
    current_coords = []
    
    if sites:
        for i, site_name in enumerate(sites):
            with st.container(border=True):
                # 【改进】：站点框支持人工输入，输入即搜索
                search_kw = st.text_input(f"📍 站点 {i+1}：输入文字修改地址", value=site_name, key=f"kw_{i}")
                
                # 高德搜索建议 (实时根据 search_kw 更新)
                t_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={search_kw}&key={AMAP_KEY}"
                try:
                    tips = requests.get(t_url, timeout=5).json().get('tips', [])
                    valid = [t for t in tips if isinstance(t.get('location'), str) and t.get('location')]
                    
                    if valid:
                        options = [f"{t['name']} ({t.get('district','')})" for t in valid]
                        # 用户在下拉框选择后，自动锁定该位置
                        sel = st.selectbox(f"确认精准地址 (站{i+1})", options, key=f"sel_{i}")
                        # 记录选中的坐标
                        target_loc = next(t['location'] for t in valid if sel.startswith(t['name']))
                        current_coords.append(target_loc)
                    else:
                        st.warning("未找到匹配地址，请修改上方文字")
                except:
                    pass

    # ==================== 5. 核心控制器：开始规划按钮 ====================
    st.divider()
    if len(current_coords) >= 2:
        # 【改进】：不点击此按钮，流程绝对不往下走，防止页面闪烁
        if st.button("🗺️ 开始导航规划 (计算总公里数)", use_container_width=True, type="primary"):
            org, des = current_coords[0], current_coords[-1]
            way = ";".join(current_coords[1:-1])
            d_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&waypoints={way}&key={AMAP_KEY}"
            
            try:
                res = requests.get(d_url, timeout=5).json()
                if res['status'] == '1' and res['route']['paths']:
                    dist = int(res['route']['paths'][0]['distance']) / 1000
                    st.session_state['km_auto'] = int(dist)
                    st.success(f"### 🚩 规划成功！总里程：{int(dist)} KM")
                    st.balloons()
                    st.rerun() # 只有计算成功才刷新页面，同步左侧数据
                else:
                    st.error("地图规划失败，请检查站点是否选择准确")
            except:
                st.error("高德接口测距超时")
    elif sites:
        st.info("请在上方选准至少两个站点，然后点击按钮开始规划。")
