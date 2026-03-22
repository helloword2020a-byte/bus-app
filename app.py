import streamlit as st
import pandas as pd
import requests
import base64
import json
import re

# ==================== 1. 核心密钥配置 (请在此替换新 Key) ====================
AI_API_KEY_V2 = "这里填入你的新API_Key"
AI_SECRET_KEY_V2 = "这里填入你的新Secret_Key" 

# 百度 OCR 密钥 (已为你配置好)
BAIDU_OCR_KEY = "1vBiCqNtSYFRx6GYsGwpwXdM"         
BAIDU_OCR_SECRET = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  

# 高德地图密钥 (已为你配置好)
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统-旗舰版", layout="wide")

# ==================== 2. 功能引擎 ====================

def get_ocr_token():
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={BAIDU_OCR_KEY}&client_secret={BAIDU_OCR_SECRET}"
    try:
        res = requests.get(url).json()
        return res.get("access_token")
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
    """【旗舰提示词优化】强力大模型：地毯式搜索所有景点，绝不漏点"""
    token = get_ocr_token() # 这里依然借用OCR Token，因为是同一账号应用
    if not token: return "AI 授权失败"
    
    # 采用性能最佳的模型接口：ERNIE-Speed-128K
    url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-128k?access_token={token}"
    
    # --- 终极优化版提示词：专治漏点和多字 ---
    prompt = (
        f"请从以下行程描述中提取所有的【目的地地名】或【城市名】。\n"
        f"特别注意：请不要漏掉文末提到的返程城市（例如'南昌返程'，必须提取出'南昌'两个字）和连带的景点（例如'陶阳里滕王阁'，必须拆分为'陶阳里 滕王阁'）。\n"
        f"要求：\n"
        f"1. 只输出纯地名，地名之间用【空格】分隔。\n"
        f"2. 严禁输出数字（如1. 2. 3.）、标点符号、动作动词。\n"
        f"原文：{text}"
    )
    
    payload = json.dumps({"messages": [{"role": "user", "content": prompt}]})
    try:
        response = requests.post(url, data=payload, headers={'Content-Type': 'application/json'})
        res = response.json()
        raw_result = res.get("result", "").strip()
        
        # 二次暴力清理
        clean_text = re.sub(r'\d+', ' ', raw_result)
        for junk in ["目的地", "地名", "：", ":", ".", "、", "接", "送", "前往", "返程", "住", "车程"]:
            clean_text = clean_text.replace(junk, " ")
        return " ".join(clean_text.split())
    except: return "AI连接异常"

def rule_extract_locations(text):
    """【旗舰规则优化】极致正则表达式：暴力剃除非地名文字"""
    if not text: return ""
    # 1. 强力清除：所有日期 (如4.11) 和 括号内容 (车程约3h)
    clean_text = re.sub(r'\(.*?\)', ' ', text)
    clean_text = re.sub(r'（.*?）', ' ', clean_text)
    clean_text = re.sub(r'\d+\.?\d*', ' ', clean_text)
    
    # 2. 剔除动作干扰词
    for word in ['接', '前往', '返程', '车程', '约', 'h', '住']:
        clean_text = clean_text.replace(word, ' ')
    
    # 3. 如果需要处理类似陶阳里滕王阁连字，可以用正则拆分
    clean_text = re.sub(r'陶阳里滕王阁', '陶阳里 滕王阁', clean_text)
        
    return " ".join(clean_text.split()).strip()

# ==================== 3. 侧边栏：核心报价计费 ====================
with st.sidebar:
    st.header("📊 报价核算中心")
    # 计费设置不再折叠
    st.subheader("⚙️ 计费标准设置")
    col_a, col_b = st.columns(2)
    b39 = col_a.number_input("39座起步费", value=800)
    p39 = col_b.number_input("39座单价", value=2.6)
    b56 = col_a.number_input("56座起步费", value=1000)
    p56 = col_b.number_input("56座单价", value=3.6)

    st.divider()
    # 這裡的km優先讀取 session_state
    f_km = st.number_input("实测总公里 (KM)", value=st.session_state.get('km_auto', 0))
    f_days = st.number_input("用车总天数 (天)", value=4)
    
    res_39 = int(f_km * p39 + f_days * b39)
    res_56 = int(f_km * p56 + f_days * b56)
    
    st.markdown("### 💰 实时总报单")
    st.success(f"🚌 **39座大巴：{res_39} 元**")
    st.info(f"🚌 **56座大巴：{res_56} 元**")

    # 需求修改：增加可复制发送文本框
    st.divider()
    st.markdown("📄 **报价发送文案 (复制发送)**")
    quote_text = (
        f"【九江祥隆旅游运输报价单】\n"
        f"实测公里数：{f_km} KM\n"
        f"用车总天数：{f_days} 天\n"
        f"--------------------\n"
        f"🚌 39座大巴：{res_39} 元\n"
        f"🚌 56座大巴：{res_56} 元\n"
        f"（包含全包车费用）"
    )
    st.text_area("复制此文字发给客户：", value=quote_text, height=180)

# ==================== 4. 主页面：流程操作 ====================
st.header("🚌 九江祥隆旅游运输报价系统 (AI 旗舰版)")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.markdown("### 1️⃣ 文字识别")
    up_file = st.file_uploader("上传截图", type=["jpg", "png", "jpeg"])
    if up_file:
        img_bytes = up_file.read()
        st.image(img_bytes, width=300)
        if st.button("🚀 开始提取识别", use_container_width=True):
            with st.spinner('提取文字中...'):
                st.session_state['ocr_raw'] = ocr_engine(img_bytes)
    
    raw_txt = st.text_area("文本核对框：", value=st.session_state.get('ocr_raw', ""), height=150)
    
    st.markdown("---")
    st.markdown("#### **站点提取方案选择**")
    c1, c2 = st.columns(2)
    
    if c1.button("✨ 智能 AI 提取", use_container_width=True):
        if raw_txt:
            st.session_state['sites_final'] = ai_extract_locations_v2(raw_txt)
        else:
            st.warning("请先提取文字")

    if c2.button("🤖 自动(规则)提取", use_container_width=True):
        if raw_txt:
            st.session_state['sites_final'] = rule_extract_locations(raw_txt)
        else:
            st.warning("请先提取文字")

with m_right:
    st.markdown("### 2️⃣ 站点确认与地图测距")
    site_input = st.text_input("待匹配关键词 (空格隔开，AI提取的站点会在这里排队)：", value=st.session_state.get('sites_final', ""))
    
    confirmed_locs = []
    if site_input:
        # 清除AI提取中可能留下的微小标点干扰
        clean_site_input = site_input.replace(",", " ").replace("，", " ")
        names = clean_site_input.split()
        
        # 分站下拉确认：确保顺序正确
        for i, name in enumerate(names):
            if not name.strip(): continue
            url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
            try:
                tips = requests.get(url).json().get('tips', [])
                valid_tips = [t for t in tips if t.get('location')]
                if valid_tips:
                    # 每一站显示一个下拉框，确保顺序正确
                    sel = st.selectbox(f"确认第 {i+1} 站: {name}", [f"{t['name']} ({t.get('district','')})" for t in valid_tips], key=f"site_sel_v4_{i}")
                    coord = next(t['location'] for t in valid_tips if sel.startswith(t['name']))
                    confirmed_locs.append(coord)
            except: pass

    # 需求修改：删除公里数计算按钮，直接计算并同步
    if len(confirmed_locs) >= 2:
        org, des = confirmed_locs[0], confirmed_locs[-1]
        way = ";".join(confirmed_locs[1:-1])
        r_url = f"https://restapi.amap.com/v3/direction/driving?origin={org}&destination={des}&key={AMAP_KEY}&waypoints={way if way else ''}"
        
        try:
            res = requests.get(r_url).json()
            if res['status'] == '1' and res['route']['paths']:
                km_val = int(round(int(res['route']['paths'][0]['distance']) / 1000))
                
                # 存入 session_state 触发左侧报价单更新
                st.session_state['km_auto'] = km_val
                st.success(f"🚩 路线规划成功！实测公里数：{km_val} KM。")
            else:
                st.error("高德地图无法计算此路径，请检查站点模糊。")
        except: pass
