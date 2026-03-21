import streamlit as st
import pandas as pd
import requests
import re
import base64

# --- 配置区 ---
BAIDU_API_KEY = "1vBiCqNtSYFRx6GYsGwpwXdM"       
BAIDU_SECRET_KEY = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO" 
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统-专业清洗版", layout="wide")

# --- 样式逻辑 ---
st.markdown("""
    <style>
    .block-container {padding-top: 1rem !important;}
    .q-table { font-size: 0.9rem; border-collapse: collapse; width: 100%; }
    .q-table td, .q-table th { border: 1px solid #dee2e6; padding: 6px; text-align: center; }
    .stNumberInput div div input { color: #d33 !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

# --- 百度 AI 接口 ---
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
    # 合并全文，解决断字问题
    full_text = "".join([i['words'] for i in res.get('words_result', [])])
    return full_text

# --- 侧边栏：核算区 (常驻) ---
with st.sidebar:
    st.title("💰 报价核算中心")
    with st.expander("⚙️ 成本单价设置", expanded=False):
        c1, c2 = st.columns(2)
        b39 = c1.number_input("39座起步", value=800)
        p39 = c2.number_input("39座单价", value=2.6)
        b56 = c1.number_input("56座起步", value=1000)
        p56 = c2.number_input("56座单价", value=3.6)

    st.divider()
    f_km = st.number_input("实测总公里 (KM)", value=st.session_state['km_auto'])
    f_days = st.number_input("用车总天数 (天)", value=4)
    
    res_39 = int(f_km * p39 + f_days * b39)
    res_56 = int(f_km * p56 + f_days * b56)
    
    st.markdown("### 🏷️ 最终计算结果")
    st.markdown(f"""
    <table class="q-table">
        <tr style="background-color:#f8f9fa"><th>车型</th><th>报单金额</th></tr>
        <tr><td>39座大巴</td><td><span style="color:red; font-size:1.2rem;"><b>{res_39} 元</b></span></td></tr>
        <tr><td>56座大巴</td><td><span style="color:red; font-size:1.2rem;"><b>{res_56} 元</b></span></td></tr>
    </table>
    """, unsafe_allow_html=True)
    st.caption("提示：修改公里或天数，报价即刻更新。")

# --- 主页面 ---
st.header("🚌 九江祥隆运输报价系统 (AI 语义清洗版)")
col_l, col_r = st.columns([1, 1.2])

with col_l:
    st.subheader("1️⃣ 行程单 AI 识别")
    up_file = st.file_uploader("粘贴行程截图", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
    if up_file:
        img_bytes = up_file.read()
        st.image(img_bytes, width=320)
        if st.button("🚀 提取全文文字", use_container_width=True):
            st.session_state['ocr_raw'] = ocr_engine(img_bytes)
    
    txt_area = st.text_area("OCR 识别原文 (可微调):", value=st.session_state.get('ocr_raw', ""), height=150)
    
    if st.button("✨ 深度智能清洗地名", use_container_width=True):
        if txt_area:
            # 强化清洗逻辑
            clean_text = txt_area
            # 1. 过滤极其不相关的干扰词
            black_list = [
                r"简易行程", r"行程", r"第\d+天", r"车程约?[\d\.h小时]+", r"住[^\s，。]*", 
                r"含早", r"午餐", r"晚餐", r"早餐", r"返回", r"前往", r"结束", r"接送", 
                r"抵达", r"集合", r"游览", r"接引", r"返程", r"下午", r"上午"
            ]
            for pattern in black_list:
                clean_text = re.sub(pattern, " ", clean_text)
            
            # 2. 提取 2-5 字的中文，排除掉名单
            words = re.findall(r'[\u4e00-\u9fa5]{2,5}', clean_text)
            stop_words = ["地点", "时间", "到达", "可以", "需要", "提示", "进行", "出发", "陶阳里", "景区"]
            
            # 3. 结果去重并合并
            final = []
            for w in words:
                if w not in stop_words and len(w) > 1:
                    if w not in final: final.append(w)
            st.session_state['sites_final'] = " ".join(final)
        else:
            st.error("请先上传并识别图片")

with col_r:
    st.subheader("2️⃣ 站点路线与测距")
    st.info("💡 请确认提取的地名，删掉不相关的词，系统将自动计算里程。")
    site_input = st.text_input("已提取地名 (如有误请在此直接删除修改):", value=st.session_state.get('sites_final', ""))
    
    confirmed_coords = []
    if site_input:
        names = site_input.split()
        grid = st.columns(2)
        for i, name in enumerate(names):
            with grid[i % 2]:
                url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
                try:
                    tips = requests.get(url).json().get('tips', [])
                    valid = [t for t in tips if t.get('location')]
                    if not valid:
                        st.warning(f"找不到: {name}")
                        continue
                    
                    # 默认选第一个最匹配的
                    sel = st.selectbox(f"站点 {i+1}: {name}", [f"{t['name']} ({t.get('district','')})" for t in valid], key=f"sel_{i}")
                    coord = next(t['location'] for t in valid if t['name'] == sel.split(" (")[0])
                    confirmed_coords.append(coord)
                except: pass

    if len(confirmed_coords) >= 2:
        # 高德测距
        org, des, way = confirmed_coords[0], confirmed_coords[-1], ";".join(confirmed_coords[1:-1])
        r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way if len(confirmed_coords)>2 else ''}"
        try:
            res = requests.get(r_url).json()
            km = int(round(int(res['route']['paths'][0]['distance']) / 1000))
            st.session_state['km_auto'] = km
            st.success(f"🚩 测距完成！共 {km} 公里。左侧报价单已自动更新。")
        except:
            st.error("路线规划失败")
