import streamlit as st
import requests
import json

# ==================== 1. 核心密钥配置 ====================
# 已为您锁定子用户凭证与地图KEY
AI_API_KEY = "ALTAKRoF5rezfzpBHyvueydG2B"
AI_SECRET_KEY = "10bc499df39a472d882aee64221d1e31" 
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆-实时地图版", layout="wide")

# ==================== 2. 高德实时搜索引擎 ====================
def get_amap_tips(keywords):
    """模拟高德搜索框，获取前10个建议"""
    if not keywords or len(keywords) < 2: return []
    url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={keywords}&key={AMAP_KEY}"
    try:
        res = requests.get(url).json()
        tips = res.get('tips', [])
        # 过滤掉没有坐标的无效地址，最多取10个
        return [t for t in tips if t.get('location') and isinstance(t['location'], str)][:10]
    except: return []

# ==================== 3. 主界面交互 ====================
st.header("🚌 九江祥隆报价系统 (高德实时联动版)")

if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0
if 'confirmed_points' not in st.session_state: st.session_state['confirmed_points'] = {}

# 第一步：获取 AI 提取的初始地名（假设已通过 OCR 提取）
sites_str = st.text_input("📝 AI 提取的原始路径：", value=st.session_state.get('sites_final', "九江 恩施"))

if sites_str:
    site_list = sites_str.split()
    st.markdown("### 🗺️ 站点精准校对 (支持实时联想)")
    
    for idx, site in enumerate(site_list):
        with st.container():
            col_input, col_select = st.columns([1, 1])
            
            # 1. 糊涂文字输入框：用户可以在此随意修改
            user_query = col_input.text_input(
                f"站点 {idx+1} 输入/修改：", 
                value=site, 
                key=f"query_{idx}",
                help="输入文字后，右侧下拉框会自动更新可选地址"
            )
            
            # 2. 实时获取高德建议
            options_data = get_amap_tips(user_query)
            
            if options_data:
                # 构造显示文本：名称 + 区域
                display_options = [f"{t['name']} ({t['district']})" for t in options_data]
                
                # 3. 动态下拉选择框：实时根据输入变化
                selected_label = col_select.selectbox(
                    f"👇 请选择精准地址 ({idx+1})：",
                    options=display_options,
                    key=f"select_{idx}"
                )
                
                # 锁定选中的坐标
                sel_idx = display_options.index(selected_label)
                st.session_state['confirmed_points'][idx] = options_data[sel_idx]['location']
            else:
                col_select.warning("🔍 正在搜索或未找到地址...")

# ==================== 4. 路径计算与报价 ====================
st.divider()
if len(st.session_state['confirmed_points']) >= 2:
    if st.button("🚀 按照以上精准站点计算公里数", use_container_width=True):
        coords = [st.session_state['confirmed_points'][i] for i in sorted(st.session_state['confirmed_points'].keys())]
        org, des = coords[0], coords[-1]
        way = ";".join(coords[1:-1])
        
        d_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&waypoints={way}&key={AMAP_KEY}"
        try:
            res = requests.get(d_url).json()
            km = int(int(res['route']['paths'][0]['distance']) / 1000)
            st.session_state['km_auto'] = km
            st.success(f"🚩 测距成功！全程：{km} 公里")
        except: st.error("测距接口调用失败")

# 侧边栏显示报价
with st.sidebar:
    st.header("💰 实时报价")
    km_val = st.session_state['km_auto']
    st.metric("实测公里", f"{km_val} KM")
    days = st.number_input("天数", value=4)
    # 39座计算：公里*2.6 + 天数*800
    total_39 = int(km_val * 2.6 + days * 800)
    st.subheader(f"39座总报价：{total_39} 元")
