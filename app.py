import streamlit as st
import pandas as pd
import requests
import re
import base64
import time
 
# ==================== 1. 页面配置 ====================
st.set_page_config(
    page_title="九江祥隆报价系统",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="collapsed"
)
 
# ==================== 2. 自定义样式 ====================
st.markdown("""
<style>
    /* 全局字体与背景 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans SC', sans-serif; }
 
    /* 隐藏默认菜单 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
 
    /* 顶部标题栏 */
    .main-header {
        background: linear-gradient(135deg, #1a3a5c 0%, #2563a8 100%);
        color: white;
        padding: 16px 24px;
        border-radius: 12px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 12px;
        box-shadow: 0 4px 15px rgba(37,99,168,0.3);
    }
    .main-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; }
    .main-header p  { margin: 0; font-size: 0.85rem; opacity: 0.85; }
 
    /* 卡片容器 */
    .card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
 
    /* 报价结果大字 */
    .price-box {
        background: linear-gradient(135deg, #f0f7ff, #dbeafe);
        border: 1px solid #93c5fd;
        border-radius: 10px;
        padding: 14px 18px;
        margin: 8px 0;
        text-align: center;
    }
    .price-box .label { font-size: 0.8rem; color: #64748b; margin-bottom: 4px; }
    .price-box .amount { font-size: 2rem; font-weight: 700; color: #1d4ed8; line-height: 1; }
    .price-box .unit   { font-size: 0.9rem; color: #64748b; }
 
    /* 里程徽章 */
    .km-badge {
        background: #dcfce7;
        border: 1px solid #86efac;
        border-radius: 8px;
        padding: 10px 14px;
        text-align: center;
        margin-top: 8px;
    }
    .km-badge .km-num { font-size: 1.6rem; font-weight: 700; color: #16a34a; }
 
    /* 站点卡片 */
    .station-card {
        background: #f8fafc;
        border-left: 3px solid #3b82f6;
        border-radius: 0 8px 8px 0;
        padding: 10px 12px;
        margin-bottom: 8px;
    }
 
    /* 错误提示 */
    .error-box {
        background: #fef2f2;
        border: 1px solid #fca5a5;
        border-radius: 8px;
        padding: 10px 14px;
        color: #b91c1c;
        font-size: 0.85rem;
        margin: 6px 0;
    }
 
    /* 分隔线 */
    hr { border-color: #e2e8f0 !important; margin: 12px 0 !important; }
 
    /* 按钮美化 */
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 500 !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important; }
 
    /* 数字输入框 */
    .stNumberInput > div > div > input { border-radius: 8px !important; }
 
    /* 区域标题 */
    .section-title {
        font-size: 1rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
</style>
""", unsafe_allow_html=True)
 
# ==================== 3. 密钥配置（使用 st.secrets，兼容本地明文） ====================
# 生产环境：在 .streamlit/secrets.toml 中配置以下键值
# [keys]
# BAIDU_OCR_AK = "xxx"
# BAIDU_OCR_SK = "xxx"
# AI_API_KEY   = "xxx"
# AMAP_KEY     = "xxx"
 
def get_secret(key, fallback=""):
    try:
        return st.secrets["keys"][key]
    except Exception:
        # 本地开发时的降级方案（勿提交到版本控制）
        _local = {
            "BAIDU_OCR_AK": "1vBiCqNtSYFRx6GYsGwpwXdM",
            "BAIDU_OCR_SK": "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO",
            "AI_API_KEY":   "bce-v3/ALTAK-EMZixkEbLJ0iEkFcaJCFc/74514893890101d198dd642b3b95ea68bed95897",
            "AMAP_KEY":     "5f1fff45fdb87c675a67685b8e0e6a74",
        }
        return _local.get(key, fallback)
 
# ==================== 4. Session State 初始化 ====================
_defaults = {
    'ocr_raw':          "",
    'temp_preview_text':"",
    'final_station_list':[],
    'km_auto':          0,
    'ocr_token':        None,   # 缓存 Baidu token
    'ocr_token_ts':     0,      # token 获取时间戳
    'coord_cache':      {},     # 地名→坐标缓存
    'tips_cache':       {},     # 地名→候选列表缓存
    'extract_error':    "",
    'route_error':      "",
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v
 
# ==================== 5. 工具函数 ====================
 
# ---------- 5.1 获取百度 Token（带30天缓存）----------
def get_baidu_token():
    now = time.time()
    # token 有效期 30 天，提前 1 天刷新
    if st.session_state['ocr_token'] and (now - st.session_state['ocr_token_ts']) < 86400 * 29:
        return st.session_state['ocr_token']
    try:
        ak = get_secret("BAIDU_OCR_AK")
        sk = get_secret("BAIDU_OCR_SK")
        url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={ak}&client_secret={sk}"
        res = requests.get(url, timeout=8).json()
        token = res.get("access_token")
        if not token:
            raise ValueError(f"百度返回异常: {res}")
        st.session_state['ocr_token'] = token
        st.session_state['ocr_token_ts'] = now
        return token
    except Exception as e:
        st.session_state['extract_error'] = f"获取百度Token失败：{e}"
        return None
 
# ---------- 5.2 OCR 引擎 ----------
def ocr_engine(file_bytes: bytes) -> str:
    token = get_baidu_token()
    if not token:
        return ""
    try:
        img64 = base64.b64encode(file_bytes).decode()
        url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate?access_token={token}"
        res = requests.post(
            url,
            data={"image": img64},
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=15
        ).json()
        if 'error_code' in res:
            raise ValueError(f"OCR错误码 {res['error_code']}: {res.get('error_msg')}")
        return "".join([i['words'] for i in res.get('words_result', [])])
    except Exception as e:
        st.session_state['extract_error'] = f"OCR识别失败：{e}"
        return ""
 
# ---------- 5.3 AI 提取（优化 Prompt + 清洗返回值）----------
def ai_extract(text: str) -> str:
    if not text.strip():
        st.session_state['extract_error'] = "请先输入或识别行程文本"
        return ""
    st.session_state['extract_error'] = ""
    try:
        api_key = get_secret("AI_API_KEY")
        url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-128k"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        prompt = (
            "你是专业行程地名提取助手。请从以下行程文本中，按出现顺序提取所有地点名称。\n"
            "要求：\n"
            "1. 只输出地名，用中文逗号分隔，不要序号、不要解释、不要多余文字\n"
            "2. 地名保留到城市、景区、车站、码头、酒店级别\n"
            "3. 去掉重复地名，但保持顺序\n"
            "4. 不要把'行程'、'备注'、'司机'等非地名词汇输出\n\n"
            "示例输入：第一天从南昌出发，乘车前往景德镇古窑民俗博览区，晚住景德镇喜来登酒店\n"
            "示例输出：南昌，景德镇古窑民俗博览区，景德镇\n\n"
            f"正式文本：{text}"
        )
        res = requests.post(
            url, headers=headers,
            json={"messages": [{"role": "user", "content": prompt}]},
            timeout=20
        ).json()
        if 'error_code' in res:
            raise ValueError(f"AI接口错误 {res['error_code']}: {res.get('error_msg')}")
        raw = res.get("result", "")
        # 清洗：去掉"好的，以下是……"之类的前缀
        raw = re.sub(r'^[^，,\u4e00-\u9fa5]*', '', raw).strip()
        return raw
    except Exception as e:
        st.session_state['extract_error'] = f"AI提取失败：{e}"
        return ""
 
# ---------- 5.4 规则提取（改进版：基于词典过滤）----------
# 常见非地名汉字词，过滤掉
_NON_PLACE_WORDS = {
    '行程', '备注', '司机', '接', '送', '前往', '返程', '出发', '抵达', '到达',
    '住宿', '酒店', '宾馆', '车站', '机场', '码头', '停车', '上车', '下车',
    '小时', '公里', '分钟', '早上', '下午', '晚上', '上午', '中午', '全天',
    '第一天', '第二天', '第三天', '第四天', '第五天', '第六天', '第七天',
    '用车', '包车', '租车', '旅游', '游览', '参观', '拍照', '就餐', '午餐',
    '晚餐', '早餐', '购物', '返回', '乘车', '驾车', '导游', '景区', '景点',
}
 
def rule_extract(text: str) -> str:
    if not text.strip():
        return ""
    # 1. 去掉括号内容和数字
    clean = re.sub(r'\(.*?\)|（.*?）', ' ', text)
    clean = re.sub(r'\d+\.?\d*', ' ', clean)
    # 2. 只保留汉字和分隔符
    clean = re.sub(r'[^\u4e00-\u9fa5，,\s]', ' ', clean)
    # 3. 按标点/空白分词
    tokens = re.split(r'[，,\s、。；：！？\n]+', clean)
    # 4. 过滤：去掉非地名词和单字
    places = []
    seen = set()
    for t in tokens:
        t = t.strip()
        if len(t) < 2:
            continue
        # 过滤掉包含非地名词根的词
        if any(nw in t for nw in _NON_PLACE_WORDS):
            continue
        if t not in seen:
            seen.add(t)
            places.append(t)
    return "，".join(places)
 
# ---------- 5.5 同步站点列表 ----------
def sync_stations():
    text = st.session_state.get('modified_input', '')
    sites = re.split(r'[，,\s]+', text)
    st.session_state['final_station_list'] = [s.strip() for s in sites if s.strip()]
 
# ---------- 5.6 高德搜索候选（带缓存）----------
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_tips(keyword: str) -> list:
    """带1小时缓存的高德地名候选搜索"""
    if not keyword.strip():
        return []
    try:
        amap_key = get_secret("AMAP_KEY")
        url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={keyword}&key={amap_key}"
        res = requests.get(url, timeout=6).json()
        if res.get('status') != '1':
            return []
        return [t for t in res.get('tips', []) if t.get('location')]
    except Exception:
        return []
 
# ---------- 5.7 高德地理编码（精确坐标，带缓存）----------
@st.cache_data(ttl=86400, show_spinner=False)
def geocode(address: str) -> str | None:
    """用地理编码接口获取精确坐标，比 inputtips 更准"""
    try:
        amap_key = get_secret("AMAP_KEY")
        url = f"https://restapi.amap.com/v3/geocode/geo?address={address}&key={amap_key}"
        res = requests.get(url, timeout=6).json()
        if res.get('status') == '1' and res['geocodes']:
            return res['geocodes'][0]['location']
        return None
    except Exception:
        return None
 
# ---------- 5.8 里程计算 ----------
def calc_distance(coords: list) -> int | None:
    """驾车路线里程（公里），途经点最多16个做截断保护"""
    if len(coords) < 2:
        return None
    try:
        amap_key = get_secret("AMAP_KEY")
        org = coords[0]
        des = coords[-1]
        # 高德途经点最多16个
        waypoints = coords[1:-1][:16]
        way_str = ";".join(waypoints)
        url = (
            f"https://restapi.amap.com/v3/direction/driving"
            f"?origin={org}&destination={des}&waypoints={way_str}&key={amap_key}"
        )
        res = requests.get(url, timeout=10).json()
        if res.get('status') != '1':
            raise ValueError(f"路线接口返回: {res.get('info')}")
        dist_m = int(res['route']['paths'][0]['distance'])
        return max(1, dist_m // 1000)
    except Exception as e:
        st.session_state['route_error'] = f"里程计算失败：{e}"
        return None
 
# ==================== 6. 界面 ====================
 
# 顶部标题
st.markdown("""
<div class="main-header">
    <div>
        <h1>🚌 九江祥隆报价系统</h1>
        <p>旗舰版 · OCR识别 · AI智能提取 · 高德测距 · 自动报价</p>
    </div>
</div>
""", unsafe_allow_html=True)
 
col_calc, col_extract, col_confirm = st.columns([0.85, 1.05, 1.1])
 
# ============================================================
# 左栏：报价核算
# ============================================================
with col_calc:
    st.markdown('<div class="section-title">📊 报价核算</div>', unsafe_allow_html=True)
 
    with st.expander("⚙️ 价格参数设置", expanded=True):
        c1, c2 = st.columns(2)
        b39 = c1.number_input("39座 基础费/天", value=800, step=50)
        p39 = c2.number_input("39座 单价/KM",   value=2.6, step=0.1, format="%.1f")
        b56 = c1.number_input("56座 基础费/天", value=1000, step=50)
        p56 = c2.number_input("56座 单价/KM",   value=3.6, step=0.1, format="%.1f")
 
    st.markdown("---")
 
    # 公里数：优先用自动测距结果
    km_val = st.session_state['km_auto'] if st.session_state['km_auto'] > 0 else 0
    f_km = st.number_input(
        "总里程 (KM)",
        value=float(km_val),
        min_value=0.0,
        step=10.0,
        help="可手动填写，或通过右侧自动测距获取"
    )
    f_days = st.number_input("用车天数", value=4, min_value=1, step=1)
 
    if f_km <= 0:
        st.warning("⚠️ 里程为0，请先测距或手动输入")
    else:
        # 报价公式：天数×基础费 + 里程×单价
        res39 = int(f_days * b39 + f_km * p39)
        res56 = int(f_days * b56 + f_km * p56)
 
        st.markdown(f"""
        <div class="price-box">
            <div class="label">🚌 39座中型客车</div>
            <div class="amount">¥{res39:,}</div>
            <div class="unit">元</div>
        </div>
        <div class="price-box">
            <div class="label">🚌 56座大型客车</div>
            <div class="amount">¥{res56:,}</div>
            <div class="unit">元</div>
        </div>
        """, unsafe_allow_html=True)
 
        st.caption(f"计算依据：{f_days}天×基础费 + {int(f_km)}KM×单价")
 
    if st.session_state['km_auto'] > 0:
        st.markdown(f"""
        <div class="km-badge">
            🗺️ 自动测距<br>
            <span class="km-num">{st.session_state['km_auto']}</span> KM
        </div>
        """, unsafe_allow_html=True)
 
# ============================================================
# 中栏：提取行程
# ============================================================
with col_extract:
    st.markdown('<div class="section-title">1️⃣ 提取行程</div>', unsafe_allow_html=True)
 
    # --- OCR 上传 ---
    up_file = st.file_uploader("📎 上传行程截图", type=["jpg", "jpeg", "png"])
    if up_file:
        if st.button("🔍 开始OCR识别", use_container_width=True):
            with st.spinner("正在识别图片文字，请稍候..."):
                result = ocr_engine(up_file.read())
            if result:
                st.session_state['ocr_raw'] = result
                st.session_state['extract_error'] = ""
                st.success("识别完成！")
            elif st.session_state['extract_error']:
                st.error(st.session_state['extract_error'])
 
    ocr_edit = st.text_area(
        "📄 OCR原文（可手动粘贴行程文本）",
        value=st.session_state['ocr_raw'],
        height=130,
        placeholder="在此粘贴行程文本，或通过上方上传图片自动识别..."
    )
 
    # --- 提取按钮 ---
    cb1, cb2 = st.columns(2)
    if cb1.button("✨ AI智能提取", use_container_width=True, type="primary"):
        with st.spinner("AI正在分析行程..."):
            result = ai_extract(ocr_edit)
        if result:
            st.session_state['temp_preview_text'] = result
            st.session_state['final_station_list'] = [
                s.strip() for s in re.split(r'[，,\s]+', result) if s.strip()
            ]
            st.session_state['extract_error'] = ""
        if st.session_state['extract_error']:
            st.error(st.session_state['extract_error'])
 
    if cb2.button("🤖 规则提取", use_container_width=True):
        result = rule_extract(ocr_edit)
        if result:
            st.session_state['temp_preview_text'] = result
            st.session_state['final_station_list'] = [
                s.strip() for s in re.split(r'[，,\s]+', result) if s.strip()
            ]
        else:
            st.warning("规则提取未找到有效地名，建议尝试AI提取")
 
    st.markdown("---")
 
    # --- 可编辑预览（实时同步）---
    st.text_area(
        "🖊️ 地名列表（可直接编辑，修改后自动同步右侧站点）",
        value=st.session_state['temp_preview_text'],
        height=100,
        key="modified_input",
        on_change=sync_stations,
        placeholder="AI/规则提取后地名将显示在这里，用逗号分隔..."
    )
 
    # 当前站点数预览
    count = len(st.session_state['final_station_list'])
    if count > 0:
        st.caption(f"✅ 已识别 {count} 个站点：{'、'.join(st.session_state['final_station_list'][:5])}{'...' if count > 5 else ''}")
 
    if st.button("🚀 强制同步站点列表", use_container_width=True):
        sync_stations()
        st.rerun()
 
# ============================================================
# 右栏：站点确认 + 测距
# ============================================================
with col_confirm:
    st.markdown('<div class="section-title">2️⃣ 站点确认与测距</div>', unsafe_allow_html=True)
 
    station_names = st.session_state['final_station_list']
    current_coords = []  # 最终用于测距的坐标列表
 
    if not station_names:
        st.info("⬅️ 请先在中间栏提取地名")
    else:
        # 超过16个途经点时提示
        if len(station_names) > 18:
            st.warning(f"⚠️ 站点较多({len(station_names)}个)，高德途经点上限16个，中间站点将自动截断")
 
        for i, name in enumerate(station_names):
            with st.container():
                st.markdown(f'<div class="station-card">', unsafe_allow_html=True)
 
                # 搜索关键词输入框
                search_kw = st.text_input(
                    f"站点 {i+1}",
                    value=name,
                    key=f"kw_{i}_{name}",
                    label_visibility="collapsed",
                    placeholder=f"站点{i+1}搜索关键词"
                )
 
                if search_kw.strip():
                    tips = fetch_tips(search_kw)
                    if tips:
                        options = [f"{t['name']}（{t.get('district', t.get('city', ''))}）" for t in tips]
                        sel = st.selectbox(
                            f"确认位置_{i}",
                            options=options,
                            key=f"sel_{i}_{name}",
                            label_visibility="collapsed"
                        )
                        # 找到选中项的坐标
                        sel_name = sel.split("（")[0]
                        matched = next((t for t in tips if t['name'] == sel_name), None)
                        if matched:
                            current_coords.append(matched['location'])
                        else:
                            # 降级：用地理编码精确查询
                            geo = geocode(search_kw)
                            if geo:
                                current_coords.append(geo)
                    else:
                        # 无候选时直接用地理编码
                        geo = geocode(search_kw)
                        if geo:
                            current_coords.append(geo)
                            st.caption(f"📍 已通过地理编码定位")
                        else:
                            st.markdown(f'<div class="error-box">⚠️ 未找到"{search_kw}"，请修改关键词</div>', unsafe_allow_html=True)
 
                st.markdown('</div>', unsafe_allow_html=True)
 
        st.markdown("---")
 
        # 坐标状态提示
        st.caption(f"📌 已匹配坐标：{len(current_coords)} / {len(station_names)} 个站点")
 
        # 测距按钮
        if len(current_coords) >= 2:
            if st.button(
                f"🗺️ 计算全程里程（{len(current_coords)}个站点）",
                use_container_width=True,
                type="primary"
            ):
                with st.spinner("正在规划路线，计算总里程..."):
                    dist = calc_distance(current_coords)
                if dist:
                    st.session_state['km_auto'] = dist
                    st.session_state['route_error'] = ""
                    st.success(f"✅ 测距完成：{dist} 公里")
                    st.rerun()
                elif st.session_state['route_error']:
                    st.error(st.session_state['route_error'])
        else:
            st.info(f"需要至少2个有效站点坐标才能测距（当前：{len(current_coords)}个）")
 
    # 里程结果固定展示
    if st.session_state['km_auto'] > 0:
        st.markdown(f"""
        <div class="km-badge">
            🗺️ 最新测距结果<br>
            <span class="km-num">{st.session_state['km_auto']}</span> KM
            <br><small style="color:#6b7280">已同步至左侧报价</small>
        </div>
        """, unsafe_allow_html=True)
 
        if st.button("🔄 重置里程", use_container_width=True):
            st.session_state['km_auto'] = 0
            st.rerun()
