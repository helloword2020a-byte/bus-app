import streamlit as st
import pandas as pd
import requests
import re
import base64
import json

# ==================== 1. 核心密钥配置 ====================
# 百度 OCR 密钥 (保持您原有的)
BAIDU_OCR_KEY = "1vBiCqNtSYFRx6GYsGwpwXdM"        
BAIDU_OCR_SECRET = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  

# 百度千帆 AI 密钥 (用于接入 ERNIE-Speed-Pro-128K)
AI_API_KEY = "bce-v3/ALTAK-9aoqLxWVRWAlk87GMFUI6/4bd21140ab38b1883ea5fa7608063fecf89c5bd2"
# 重要：请在此处填入您在千帆后台点击“显示”后看到的 Secret Key
AI_SECRET_KEY = "请填入您的AI_Secret_Key" 

# 高德地图密钥
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
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&secret_key={secret_key}"
    # 注意：百度 OCR 和 千帆 AI 使用的是同一套 Token 获取逻辑，但参数名略有差异
    url_fixed = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
    try: return requests.get(url_fixed).json().get("access_token")
    except: return None

def ocr_engine(file_bytes):
    """高精度 OCR 识别"""
    token = get_access_token(BAIDU_OCR_KEY, BAIDU_OCR_SECRET)
    if not token: return "OCR 授权失败"
    img64 = base64.b64encode(file_bytes).decode()
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token={token}"
    res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
    return "".join([i['words'] for i in res.get('words_result', [])])

def ai_extract_locations(text):
    """ERNIE-Speed-Pro-128K 智能提取地名"""
    token = get_access_token(AI_API_KEY, AI_SECRET_KEY)
    if not token: return "AI 授权失败，请检查 Secret Key"
    
    # 调用的模型接口
    url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-pro-128k?access_token={token}"
    
    prompt = f"""你是一个旅游调度。请从以下文字中只提取出纯地名。
    要求：1. 剔除所有干扰词（如：接、送、住、车程、约3h、简易行程、下午）。
    2. 例如“南昌接”提取为“南昌”，“住葛仙村”提取为“葛仙村”。
    3. 只输出地名，地名之间用一个空格隔开。
    原文内容：{text}"""
    
    payload = json.dumps({"messages": [{"role": "user", "content": prompt}]})
    try:
        res = requests.post(url, data=payload, headers={'Content-Type': 'application/json'}).json()
        return res.get("result", "").strip()
    except:
        return "AI 处理请求失败"

# ==================== 4. 侧边栏：核心报价计费 ====================
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
    # 这里的实测总公里会自动接收右侧地图的计算结果
    f_km = st.number_input("实测总公里 (KM)", value=st.session_state['km_auto'])
    f_days = st.number_input("用车总天数 (天)", value=4)
    
    # 报价计算逻辑
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
    st.caption(f"公式：{f_km}KM × 单价 + {f_days}天 × 起步费")

# ==================== 5. 主页面：流程操作 ====================
st.header("🚌 九江祥隆旅游运输报价系统 (AI 旗舰版)")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.markdown("### 1️⃣ 行程 AI 智能识别")
    up_file = st.file_uploader("上传行程截图", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
    if up_file:
        img_bytes = up_file.read()
        st.image(img_bytes, width=320)
        if st.button("🚀 第一步：高精度文字识别", use_container_width=True):
            st.session_state['ocr_raw'] = ocr_engine(img_bytes)
    
    raw_txt = st.text_area("识别文本校对：", value=st.session_state.get('ocr_raw', ""), height=150)
    
    if st.button("✨ 第二步：AI 提炼纯路径", use_container_width=True):
        if raw_txt:
            with st.spinner('AI 正在清洗路径...'):
                clean_sites = ai_extract_locations(raw_txt)
                st.session_state['sites_final'] = clean_sites
        else:
            st.error("请先识别行程文字")

with m_right:
    st.markdown("### 2️⃣ 站点确认与地图测距")
    st.caption("提示：AI 已为您过滤多余词汇，可手动微调，地图将实时重算。")
    site_input = st.text_input("AI 提取地名关键词：", value=st.session_state.get('sites_final', ""), label_visibility="collapsed")
    
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
                    # 让用户在匹配到的地点中进行微调选择
                    sel = st.selectbox(f"站点{i+1}: {name}", [f"{t['name']} ({t.get('district','')})" for t in valid_tips], key=f"sel_{i}")
                    coord = next(t['location'] for t in valid_tips if t['name'] == sel.split(" (")[0])
                    confirmed_locs.append(coord)
                except: pass

    # 路径规划与里程同步
    if len(confirmed_locs) >= 2:
        try:
            org, des, way = confirmed_locs[0], confirmed_locs[-1], ";".join(confirmed_locs[1:-1])
            r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way if len(confirmed_locs)>2 else ''}"
            res = requests.get(r_url).json()
            km_val = int(round(int(res['route']['paths'][0]['distance']) / 1000))
            
            # 将测距结果同步给左侧侧边栏
            st.session_state['km_auto'] = km_val
            st.success(f"🚩 路线规划成功！实测总计：{km_val} KM。")
            st.info("数据已自动同步至左侧【实测总公里】，总报价已更新。")
        except:
            st.error("地图测距失败，请检查站点名称是否正确")
