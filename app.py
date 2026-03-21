import streamlit as st
import pandas as pd
import requests
import re
import base64

# --- 1. 基础配置 ---
BAIDU_API_KEY = "1vBiCqNtSYFRx6GYsGwpwXdM"       
BAIDU_SECRET_KEY = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO" 
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统-智能旗舰版", layout="wide")

# --- 2. 界面样式 ---
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

# --- 3. 百度 AI OCR 引擎 ---
def get_baidu_token():
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={BAIDU_API_KEY}&client_secret={BAIDU_SECRET_KEY}"
    try: return requests.get(url).json().get("access_token")
    except: return None

def ocr_engine(file_bytes):
    token = get_baidu_token()
    if not token: return "授权失败"
    img64 = base64.b64encode(file_bytes).decode()
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token={token}"
    res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
    # 核心：将所有识别块拼成一个完整长文本，解决跨行断字问题
    return "".join([i['words'] for i in res.get('words_result', [])])

# --- 4. 侧边栏：核心报价工作台 ---
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
    
    # 实时计算报价
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
    st.caption(f"详情：{f_km}KM × 单价 + {f_days}天 × 起步费")

# --- 5. 主页面布局 ---
st.header("🚌 九江祥隆旅游运输报价系统 (AI 旗舰版)")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.markdown("### 1️⃣ 行程 AI 智能识别")
    up_file = st.file_uploader("粘贴或上传行程截图", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
    if up_file:
        img_bytes = up_file.read()
        st.image(img_bytes, width=320)
        if st.button("🚀 开始高精度全文识别", use_container_width=True):
            st.session_state['ocr_raw'] = ocr_engine(img_bytes)
    
    raw_txt = st.text_area("识别文本校对：", value=st.session_state.get('ocr_raw', ""), height=150)
    
    if st.button("✨ 智能提取所有地名 (测试成功版)", use_container_width=True):
        if raw_txt:
            # --- 智能清洗逻辑 ---
            text = raw_txt
            # 1. 强力剔除干扰词
            noise = [r"第\d+天", r"行程", r"简易", r"车程约?[\d\.h小时]+", r"住[^\s，。]*", r"含早", r"下午", r"上午", r"抵达", r"集合", r"游览", r"返回", r"前往", r"结束", r"返程"]
            for n in noise: text = re.sub(n, " ", text)
            
            # 2. 提取 2-6 个中文字符，并清洗特定的动作词后缀
            found = re.findall(r'[\u4e00-\u9fa5]{2,6}', text)
            stop_words = ["可以", "需要", "提示", "进行", "地点", "时间", "到达", "出发", "景区"]
            
            clean_sites = []
            for w in found:
                # 剔除关键词里的“接”和“送”，比如“南昌接”变为“南昌”
                w_clean = w.replace("接", "").replace("送", "")
                if w_clean not in stop_words and len(w_clean) > 1:
                    if w_clean not in clean_sites: clean_sites.append(w_clean)
            
            st.session_state['sites_final'] = " ".join(clean_sites)
        else:
            st.error("请先识别行程文字")

with m_right:
    st.markdown("### 2️⃣ 站点确认与地图测距")
    st.caption("提示：可在下方框内直接删减不相关的字，地图会实时重算距离。")
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
                    
                    # 下拉选择具体位置
                    sel = st.selectbox(f"站点{i+1}: {name}", [f"{t['name']} ({t.get('district','')})" for t in valid_tips], key=f"sel_{i}")
                    coord = next(t['location'] for t in valid_tips if t['name'] == sel.split(" (")[0])
                    confirmed_locs.append(coord)
                except: pass

    if len(confirmed_locs) >= 2:
        try:
            org, des, way = confirmed_locs[0], confirmed_locs[-1], ";".join(confirmed_locs[1:-1])
            r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way if len(confirmed_locs)>2 else ''}"
            res = requests.get(r_url).json()
            km_val = int(round(int(res['route']['paths'][0]['distance']) / 1000))
            
            # 同步至左侧侧边栏
            st.session_state['km_auto'] = km_val
            st.success(f"🚩 路线规划成功！实测公里：{km_val} KM。")
            st.info("数据已同步至左侧【实测总公里】，最终报价已刷新。")
        except:
            st.error("地图测距失败，请微调站点名称")
