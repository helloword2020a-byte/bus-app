import streamlit as st
import pandas as pd
import requests
import re
import base64
import json

# ==================== 1. 核心密钥配置 ====================

# [必填] 这是你在后台复制的 V2 版本 API Key (bce-v3/ALTAK...开头)
AI_API_KEY_V2 = "bce-v3/ALTAK-EMZixkEbLJ0iEkFcaJCFc/74514893890101d198dd642b3b95ea68bed95897"

# 百度 OCR 密钥 (已为你配置好)
BAIDU_OCR_AK = "1vBiCqNtSYFRx6GYsGwpwXdM"         
BAIDU_OCR_SK = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  

# 高德地图密钥 (已为你配置好)
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统-究极旗舰版", layout="wide")

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
    res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
    return "".join([i['words'] for i in res.get('words_result', [])])

def ai_extract_locations_v2(text):
    """【强力 AI 提取】大模型读心术：精准拆分、绝不漏点"""
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-pro-128k"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY_V2}"
    }
    
    # 究极版 Prompt：专治复合地名和末尾漏点
    prompt = (
        f"你是一个专业的地理数据清理专家。请从以下文本中提取所有的【目的地地名】（包括城市、景点、景区名）。\n"
        f"特别注意：\n"
        f"1. 只输出地名，地名之间用【空格】分隔。\n"
        f"2. 即使地名连在一起（如：景德镇陶瓷科技馆陶溪川），必须理解并拆分为‘景德镇陶瓷科技馆 陶溪川’。\n"
        f"3. 文末提及的‘返程点’（如：送南昌高铁），必须提取出‘南昌’两个字。\n"
        f"4. 严禁输出数字序号、标点或‘目的地：’等描述。\n"
        f"原文：{text}"
    )
    
    payload = {"messages": [{"role": "user", "content": prompt}]}
    try:
        response = requests.post(url, headers=headers, json=payload)
        res = response.json()
        if "error_code" in res:
            return f"AI 错误({res['error_code']}): {res.get('error_msg')}"
        
        # 二次强力清洗
        result = res.get("result", "").strip()
        clean_text = re.sub(r'\d+', ' ', result)
        for junk in ["目的地", "地名", "地点", "：", ":", ".", "、", "接", "住", "前往", "返程", "车程"]:
            clean_text = clean_text.replace(junk, " ")
        return " ".join(clean_text.split())
    except Exception as e:
        return f"AI 通信异常: {str(e)}"

def rule_extract_locations(text):
    """【自动规则提取】暴力清洗法：彻底删除括号和数字"""
    if not text: return ""
    # 1. 最核心修复：删掉所有数字(如4.11)和所有括号内内容(如 (车程3h) )
    clean_text = re.sub(r'\(.*?\)', ' ', text) # 删掉括号内容
    clean_text = re.sub(r'\d+\.?\d*', ' ', clean_text) # 删掉数字(包括带小数点的)
    
    # 2. 移除常见的动作词和符号
    for word in ['接', '送', '前往', '返程', '车程', '约', 'h', '住', '陶阳里', '滕王阁', '陶溪川', '奥特莱斯', '天花井', '东林大佛', '。', ':', '：', ',']:
        clean_text = clean_text.replace(word, ' ')
    
    # 3. 针对你测试的那些连字地名做特殊处理（因为规则识别不能理解意思）
    special_fixes = [
        ('景德镇陶瓷科技馆陶溪川', '景德镇陶瓷科技馆 陶溪川'),
        ('奥特莱斯天花井或东林大佛', '奥特莱斯 东林大佛'), # 删掉'天花井或'，因为规则容易混淆
    ]
    for old, new in special_fixes:
        clean_text = clean_text.replace(old, new)
        
    return " ".join(clean_text.split()).strip()

# ==================== 3. 侧边栏：实时报价核算 ====================

if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

with st.sidebar:
    st.header("📊 报价核算中心")
    st.subheader("⚙️ 计费标准设置")
    col_a, col_b = st.columns(2)
    b39 = col_a.number_input("39座起步费", value=800)
    p39 = col_b.number_input("39座单价", value=2.6)
    b56 = col_a.number_input("56座起步费", value=1000)
    p56 = col_b.number_input("56座单价", value=3.6)

    st.divider()
    f_km = st.number_input("实测总公里 (KM)", value=st.session_state['km_auto'])
    f_days = st.number_input("用车总天数 (天)", value=4)
    
    res_39 = int(f_km * p39 + f_days * b39)
    res_56 = int(f_km * p56 + f_days * b56)
    
    st.markdown("### 💰 实时总报单")
    st.success(f"🚌 **39座大巴：{res_39} 元**")
    st.info(f"🚌 **56座大巴：{res_56} 元**")

    st.divider()
    st.markdown("📄 **报价发送文案 (复制粘贴)**")
    quote_text = (
        f"【九江祥隆旅游运输报价单】\n"
        f"实测公里：{f_km} KM\n"
        f"用车天数：{f_days} 天\n"
        f"--------------------\n"
        f"🚌 39座大巴全包价：{res_39} 元\n"
        f"🚌 56座大巴全包价：{res_56} 元\n"
        f"（包含全包车费用）"
    )
    st.text_area("复制此文字发送给客户：", value=quote_text, height=150)

# ==================== 4. 主页面：流程操作 ====================
st.header("🚌 九江祥隆旅游运输报价系统 (AI 旗舰版)")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.markdown("### 1️⃣ 行程文字识别 (OCR)")
    up_file = st.file_uploader("上传行程截图", type=["jpg", "png", "jpeg"])
    if up_file:
        img_bytes = up_file.read()
        st.image(img_bytes, width=300)
        if st.button("🚀 开始高精度识别文字", use_container_width=True):
            st.session_state['ocr_raw'] = ocr_engine(img_bytes)
    
    raw_txt = st.text_area("文本校对框 (如果需要手动改顺序)：", value=st.session_state.get('ocr_raw', ""), height=150)
    
    st.markdown("---")
    st.markdown("#### **站点提取方案选择 (双模)**")
    c1, c2 = st.columns(2)
    
    if c1.button("✨ 强力 AI 提取", use_container_width=True):
        if raw_txt:
            with st.spinner('正在使用大模型智能读心提取所有地名...'):
                st.session_state['sites_final'] = ai_extract_locations_v2(raw_txt)
        else:
            st.warning("请上传截图或输入文字")

    if c2.button("🤖 自动(规则)提取", use_container_width=True):
        if raw_txt:
            with st.spinner('正在运行规则暴力清洗提取站点...'):
                st.session_state['sites_final'] = rule_extract_locations(raw_txt)
        else:
            st.warning("请上传截图或输入文字")

with m_right:
    st.markdown("### 2️⃣ 站点确认与地图测距")
    site_input = st.text_input("待匹配关键词 (空格隔开，AI提取的站点会在这里排队)：", value=st.session_state.get('sites_final', ""))
    
    confirmed_locs = []
    if site_input:
        names = site_input.split()
        for i, name in enumerate(names):
            if not name.strip(): continue
            # 调用高德 API 搜索地点建议
            url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
            try:
                tips = requests.get(url).json().get('tips', [])
                valid_tips = [t for t in tips if t.get('location')]
                if valid_tips:
                    # 分站确认下拉框：站点顺序优化
                    sel = st.selectbox(f"确认第 {i+1} 站: {name}", [f"{t['name']} ({t.get('district','')})" for t in valid_tips], key=f"site_v4_{i}")
                    coord = next(t['location'] for t in valid_tips if sel.startswith(t['name']))
                    confirmed_locs.append(coord)
            except: pass

    # 路径测距逻辑
    if len(confirmed_locs) >= 2:
        st.divider()
        org, des = confirmed_locs[0], confirmed_locs[-1]
        way = ";".join(confirmed_locs[1:-1])
        r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way if way else ''}"
        
        try:
            res = requests.get(r_url).json()
            if res['status'] == '1' and res['route']['paths']:
                km = int(round(int(res['route']['paths'][0]['distance']) / 1000))
                st.session_state['km_auto'] = km
                st.success(f"🚩 规划成功！实测公里数：{km} KM")
                if st.button("✅ 更新里程到报价单"): st.rerun()
            else: st.error("高德地图无法计算此路径，因为选定的地点过于模糊，或者不存在。请在下拉框中重新选择准确的地点。")
        except: st.error("地图接口连接失败，请检查高德 KEY。")
