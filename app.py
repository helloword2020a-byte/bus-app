import streamlit as st
import pandas as pd
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

st.set_page_config(page_title="九江祥隆报价系统-极速优化版", layout="wide")

# ==================== 2. 地址过滤“黑名单”库 ====================
# 无需建立庞大的中国地址库，通过黑名单过滤掉行程单中的常见干扰词
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

# ==================== 4. 侧边栏：核心报价计费 (加入 Form 防止刷新) ====================
if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

with st.sidebar:
    st.header("📊 报价核算中心")
    # 使用 Form 包裹，只有点“更新报价”按钮时才会重新计算，防止输入公里数页面就闪烁
    with st.form("calc_form"):
        st.subheader("⚙️ 计费标准")
        c1, c2 = st.columns(2)
        b39 = c1.number_input("39座起步", value=800)
        p39 = c2.number_input("39座单价", value=2.6)
        b56 = c1.number_input("56座起步", value=1000)
        p56 = c2.number_input("56座单价", value=3.6)
        
        st.divider()
        f_km = st.number_input("总公里 (KM)", value=st.session_state['km_auto'])
        f_days = st.number_input("总天数 (天)", value=4)
        
        submitted = st.form_submit_button("💰 更新总报价")
        
        res_39, res_56 = int(f_km*p39 + f_days*b39), int(f_km*p56 + f_days*b56)
        st.markdown(f"""<table style="width:100%; text-align:center; border:1px solid #ddd;">
            <tr style="background-color:#1e88e5; color:white;"><th>车型</th><th>价格</th></tr>
            <tr><td>39座</td><td><b>{res_39} 元</b></td></tr>
            <tr><td>56座</td><td><b>{res_56} 元</b></td></tr>
        </table>""", unsafe_allow_html=True)

# ==================== 5. 主页面：流程操作 ====================
st.header("🚌 九江祥隆旅游运输报价系统 (AI 旗舰版)")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.markdown("### 1️⃣ 行程智能识别")
    up_file = st.file_uploader("上传截图", type=["jpg", "png", "jpeg"])
    if up_file and st.button("🚀 开始文字识别", use_container_width=True):
        st.session_state['ocr_raw'] = ocr_engine(up_file.read())
    
    raw_txt = st.text_area("识别文本校对：", value=st.session_state.get('ocr_raw', ""), height=150)
    
    col_btn1, col_btn2 = st.columns(2)
    if col_btn1.button("✨ 智能 AI 提取", use_container_width=True):
        st.session_state['sites_final'] = ai_extract_locations(raw_txt)
    
    if col_btn2.button("🤖 自动规则提取", use_container_width=True):
        # 优化后的正则提取：提取中文 + 黑名单过滤
        locs = re.findall(r'[\u4e00-\u9fa5]{2,}', raw_txt)
        cleaned_locs = clean_locations(locs)
        st.session_state['sites_final'] = " ".join(cleaned_locs)

with m_right:
    st.markdown("### 2️⃣ 站点确认 (支持高德 10 项联想)")
    site_input = st.text_input("待匹配地名 (空格隔开)：", value=st.session_state.get('sites_final', ""))
    
    confirmed_locs = []
    if site_input:
        names = site_input.split()
        for i, name in enumerate(names):
            # 使用 popover 解决弹窗问题
            with st.popover(f"📍 站 {i+1}：{name}", use_container_width=True):
                # 输入即搜索逻辑
                search_kw = st.text_input(f"手动修改搜索词", value=name, key=f"kw_{i}")
                
                # 获取高德 10 条联想结果
                t_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={search_kw}&key={AMAP_KEY}"
                try:
                    res_json = requests.get(t_url).json()
                    tips = res_json.get('tips', [])
                    # 确保只选取有具体坐标的地址，且显示 10 个
                    valid_tips = [t for t in tips if t.get('location') and isinstance(t['location'], str)][:10]
                    
                    if valid_tips:
                        opts = [f"{t['name']} ({t.get('district','')})" for t in valid_tips]
                        # 用户在此选择最精准的一个
                        selected = st.selectbox("请在下方 10 个建议中选择精准地址：", opts, key=f"sel_{i}")
                        
                        # 锁定最终经纬度
                        final_name = selected.split(" (")[0]
                        coord = next(t['location'] for t in valid_tips if t['name'] == final_name)
                        st.session_state[f"coord_{i}"] = coord
                    else:
                        st.warning("无搜索结果，请尝试简化关键词")
                except:
                    st.error("高德接口连接超时")

            if f"coord_{i}" in st.session_state:
                confirmed_locs.append(st.session_state[f"coord_{i}"])

    st.divider()
    # 只有点击此按钮才会触发布局更新，计算公里数
    if len(confirmed_locs) >= 2:
        if st.button("🗺️ 计算选定站点总公里数", use_container_width=True):
            org, des, way = confirmed_locs[0], confirmed_locs[-1], ";".join(confirmed_locs[1:-1])
            r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way}"
            try:
                route_res = requests.get(r_url).json()
                km_val = int(int(route_res['route']['paths'][0]['distance']) / 1000)
                st.session_state['km_auto'] = km_val
                st.success(f"计算成功！实测：{km_val} KM")
                st.rerun() # 仅在计算成功后刷新侧边栏数字
            except:
                st.error("路径规划失败，请检查站点是否过于偏僻")
