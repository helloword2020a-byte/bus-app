import streamlit as st
import pandas as pd
import requests
import re
import base64

# --- 1. 配置中心 ---
BAIDU_API_KEY = "1vBiCqNtSYFRx6GYsGwpwXdM"       
BAIDU_SECRET_KEY = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO" 
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统-智能版", layout="wide")

# --- 2. CSS 样式 (确保布局紧凑且常驻) ---
st.markdown("""
    <style>
    .block-container {padding-top: 1rem !important;}
    [data-testid="stSidebar"] {background-color: #f8f9fa;}
    .q-table { font-size: 0.9rem; border-collapse: collapse; width: 100%; margin-top: 10px;}
    .q-table td, .q-table th { border: 1px solid #dee2e6; padding: 6px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# 初始化公里数状态
if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

# --- 3. 百度 AI 引擎函数 ---
def get_baidu_token():
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={BAIDU_API_KEY}&client_secret={BAIDU_SECRET_KEY}"
    try: return requests.get(url).json().get("access_token")
    except: return None

def ocr_engine(file_bytes):
    token = get_baidu_token()
    if not token: return "授权失败"
    img64 = base64.b64encode(file_bytes).decode()
    # 使用高精度版本
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token={token}"
    res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
    # 聚合成完整文本块，解决断句问题
    return "".join([i['words'] for i in res.get('words_result', [])])

# --- 4. 侧边栏：常驻核算中心 ---
with st.sidebar:
    st.title("📊 核算与报价")
    
    with st.expander("⚙️ 计费标准", expanded=False):
        c1, c2 = st.columns(2)
        b39 = c1.number_input("39座起步", value=800)
        p39 = c2.number_input("39座单价", value=2.6)
        b56 = c1.number_input("56座起步", value=1000)
        p56 = c2.number_input("56座单价", value=3.6)

    st.divider()
    
    st.subheader("📝 核心参数")
    f_km = st.number_input("实测总公里 (KM)", value=st.session_state['km_auto'], key="km_input")
    f_days = st.number_input("用车总天数 (天)", value=4, key="days_input")
    
    # 计算逻辑
    res_39 = int(f_km * p39 + f_days * b39)
    res_56 = int(f_km * p56 + f_days * b56)
    
    st.markdown("### 💰 实时计算报单")
    st.markdown(f"""
    <table class="q-table">
        <tr style="background-color:#e9ecef"><th>车型</th><th>总报价</th></tr>
        <tr><td>39座大巴</td><td><b>{res_39} 元</b></td></tr>
        <tr><td>56座大巴</td><td><b>{res_56} 元</b></td></tr>
    </table>
    """, unsafe_allow_html=True)
    
    st.caption(f"明细：{f_km}KM × 单价 + {f_days}天 × 起步费")

# --- 5. 主页面布局 ---
st.header("🚌 九江祥隆旅游运输报价系统 (AI智能提取)")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.markdown("### 1️⃣ 行程单 AI 识别")
    up_file = st.file_uploader("点击或拖拽行程截图", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
    if up_file:
        img_bytes = up_file.read()
        st.image(img_bytes, width=300)
        if st.button("🚀 开始高精度识别", use_container_width=True):
            with st.spinner("正在解析文字..."):
                st.session_state['ocr_raw'] = ocr_engine(img_bytes)
    
    raw_text = st.text_area("OCR 识别原文 (可手动补全):", value=st.session_state.get('ocr_raw', ""), height=180)
    
    if st.button("✨ 智能提取所有地名", use_container_width=True):
        if raw_text:
            # 智能提取逻辑：
            # 1. 过滤干扰字符（日期、时间、车程、住等）
            text = raw_text
            noise_list = [r"\d+\.\d+", r"第\d+天", r"车程约?[\d\.h小时]+", r"住[^\s，。]*", r"含早", r"下午", r"上午", r"午餐", r"晚餐"]
            for n in noise_list: text = re.sub(n, " ", text)
            
            # 2. 识别动作关联词并清理
            actions = ["前往", "接引", "返程", "结束", "抵达", "集合", "游览", "送", "接"]
            for a in actions: text = text.replace(a, " ")
            
            # 3. 核心地名提取（利用正则表达式匹配2-6个连续中文，但排除常见废话词）
            candidates = re.findall(r'[\u4e00-\u9fa5]{2,6}', text)
            stop_words = ["可以", "需要", "提示", "进行", "返回", "地点", "时间", "到达", "出发", "行程", "简易", "风景区", "博物馆"]
            
            final_sites = []
            for word in candidates:
                if word not in stop_words and len(word) >= 2:
                    if word not in final_sites: final_sites.append(word)
            
            # 将提取结果放回状态
            st.session_state['sites_final'] = " ".join(final_sites)
        else:
            st.warning("请先识别或输入行程文字")

with m_right:
    st.markdown("### 2️⃣ 站点路线确认")
    site_input = st.text_input("提取的地名关键词：", value=st.session_state.get('sites_final', ""), label_visibility="collapsed")
    
    confirmed_locs = []
    if site_input:
        names = site_input.split()
        st.write(f"已识别出 {len(names)} 个潜在站点：")
        grid = st.columns(2)
        for i, name in enumerate(names):
            with grid[i % 2]:
                # 联想搜索
                search_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
                try:
                    tips = requests.get(search_url).json().get('tips', [])
                    # 过滤掉没有经纬度的结果
                    valid_tips = [t for t in tips if t.get('location')]
                    opts = [f"{t['name']} ({t.get('district','')})" for t in valid_tips]
                    
                    if not opts:
                        st.warning(f"未找到: {name}")
                        continue
                        
                    sel = st.selectbox(f"站点 {i+1}", opts, key=f"sel_{i}")
                    coord = next(t['location'] for t in valid_tips if t['name'] == sel.split(" (")[0])
                    confirmed_locs.append(coord)
                except:
                    pass

    if len(confirmed_locs) >= 2:
        # 高德路线规划
        org, des, way = confirmed_locs[0], confirmed_locs[-1], ";".join(confirmed_locs[1:-1])
        r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way if len(confirmed_locs)>2 else ''}"
        try:
            res = requests.get(r_url).json()
            total_dist = int(res['route']['paths'][0]['distance'])
            km_val = int(round(total_dist / 1000))
            
            # 核心：自动同步回侧边栏
            st.session_state['km_auto'] = km_val
            st.success(f"✅ 地图实测总里程：{km_val} KM。报价已在左侧同步生成！")
            if st.button("📥 保存本次行程并刷新报单"):
                st.rerun()
        except:
            st.error("路线规划失败，请调整站点选择")
