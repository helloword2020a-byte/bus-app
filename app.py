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

st.set_page_config(page_title="九江祥隆-高德交互版", layout="wide")

# 屏蔽干扰词
BLACK_LIST = ["第一天", "第二天", "第三天", "第四天", "第五天", "第六天", "第七天", "返程", "行程", "住宿", "用餐", "含餐", "早餐", "午餐", "晚餐", "自理", "车程", "小时", "分钟", "接团", "送团", "出发", "返回", "入住", "酒店", "车费", "司机", "左右", "抵达"]

# ==================== 2. 状态管理器 ====================
if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0
if 'final_sites' not in st.session_state: st.session_state['final_sites'] = {} # 存储最终选定的地址详情

# ==================== 3. 核心功能 ====================
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

# ==================== 4. 侧边栏报价 ====================
with st.sidebar:
    st.header("📊 报价核算")
    with st.form("price_form"):
        c1, c2 = st.columns(2)
        b39, p39 = c1.number_input("39座起步", value=800), c2.number_input("39座单价", value=2.6)
        f_km = st.number_input("总公里 (KM)", value=st.session_state['km_auto'])
        f_days = st.number_input("总天数 (天)", value=4)
        st.form_submit_button("💰 更新价格")
    st.info(f"39座预估：{int(f_km*p39 + f_days*b39)} 元")

# ==================== 5. 主页面 ====================
st.title("🚌 九江祥隆报价系统 (高德搜索模式)")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.markdown("### 1️⃣ 行程文字提取")
    up_file = st.file_uploader("上传截图", type=["jpg", "png", "jpeg"])
    if up_file and st.button("🚀 开始文字识别"):
        st.session_state['ocr_raw'] = ocr_engine(up_file.read())
    
    raw_txt = st.text_area("文本预览：", value=st.session_state.get('ocr_raw', ""), height=150)
    if st.button("🤖 自动过滤提取"):
        locs = re.findall(r'[\u4e00-\u9fa5]{2,}', raw_txt)
        st.session_state['sites_raw_list'] = [l for l in locs if l not in BLACK_LIST]

with m_right:
    st.markdown("### 2️⃣ 站点确认 (仿高德交互模式)")
    
    # 获取初步提取的站点列表
    sites = st.session_state.get('sites_raw_list', [])
    
    if sites:
        for i, site in enumerate(sites):
            # 搜索与下拉合二为一
            # 我们先用 text_input 作为搜索框
            search_val = st.text_input(f"站点 {i+1}", value=site, key=f"search_{i}", help="支持实时修改搜索内容")
            
            # 高德实时抓取 10 条建议
            t_url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={search_val}&key={AMAP_KEY}"
            try:
                tips_data = requests.get(t_url).json().get('tips', [])
                valid_tips = [t for t in tips_data if t.get('location')][:10]
                
                if valid_tips:
                    # 将联想结果做成列表
                    options = [f"{t['name']} ({t.get('district','')})" for t in valid_tips]
                    # 下拉选择后直接锁定
                    selected = st.selectbox(f"请选定精确地址 (站{i+1})", options, key=f"sel_{i}")
                    
                    # 实时存入 session_state
                    target = next(t for t in valid_tips if f"{t['name']} ({t.get('district','')})" == selected)
                    st.session_state['final_sites'][i] = {
                        "name": target['name'],
                        "coord": target['location']
                    }
                else:
                    st.warning("⚠️ 高德未找到相关地点，请修改搜索词")
            except: pass

    # ==================== 6. 流程控制器 ====================
    st.divider()
    if len(st.session_state['final_sites']) >= 2:
        # 增加手动计算按钮，不点不动
        if st.button("🗺️ 确认所有地址，开始导航规划", use_container_width=True, type="primary"):
            keys = sorted(st.session_state['final_sites'].keys())
            coords = [st.session_state['final_sites'][k]['coord'] for k in keys]
            
            org, des, way = coords[0], coords[-1], ";".join(coords[1:-1])
            r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way}"
            
            try:
                res = requests.get(r_url).json()
                if res['status'] == '1':
                    km = int(int(res['route']['paths'][0]['distance']) / 1000)
                    st.session_state['km_auto'] = km
                    st.success(f"✨ 规划完成！实测里程: {km} KM")
                    st.rerun() # 刷新侧边栏价格
                else:
                    st.error("❌ 地图规划失败，请检查选定地址是否真实有效")
            except:
                st.error("❌ 接口连接异常")
