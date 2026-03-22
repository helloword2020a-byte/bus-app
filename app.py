import streamlit as st
import pandas as pd
import requests
import re
import base64
import json

# ==================== 1. 核心密钥配置 ====================

# [必填] 这里填入你最新的 V2 版本 API Key (bce-v3/ALTAK-EMZixkEbLJ0iEkFcaJCFc/...)
AI_API_KEY_V2 = "bce-v3/ALTAK-EMZixkEbLJ0iEkFcaJCFc/74514893890101d198dd642b3b95ea68bed95897"

# 百度 OCR 密钥 (已为你配置好)
BAIDU_OCR_AK = "1vBiCqNtSYFRx6GYsGwpwXdM"         
BAIDU_OCR_SK = "ObUQToQCiOIaUTtBhMivJhA4nAhRdMvO"  

# 高德地图密钥 (已为你配置好)
AMAP_KEY = "5f1fff45fdb87c675a67685b8e0e6a74"

st.set_page_config(page_title="九江祥隆报价系统-AI旗舰版", layout="wide")

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
    try:
        res = requests.post(url, data={"image": img64}, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
        return "".join([i['words'] for i in res.get('words_result', [])])
    except: return "识别异常"

def ai_extract_locations_v2(text):
    """【旗舰级】大模型智能提取：精准拆分景点，绝不漏点"""
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-pro-128k"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY_V2}" # V2专用Bearer模式认证
    }
    
    # 旗舰版 Prompt：重点解决文末景点漏点和连词拆分
    prompt = (
        f"你是一个专业的旅游行程调度专家。请从以下文本中提取所有的目的地【地名】或【城市】。\n"
        f"特别注意：严禁漏掉结尾处的景点名或返程点（如：陶阳里、滕王阁、南昌）。\n"
        f"要求：\n"
        f"1. 只输出地名，地名之间用空格分隔。\n"
        f"2. 严禁输出数字序号（如1. 2. 3.）、严禁输出标点符号和动作动词。\n"
        f"3. 如果地名连在一起（如：陶阳里滕王阁），也请将其拆分为独立的景点。\n"
        f"原文：{text}"
    )
    
    payload = {"messages": [{"role": "user", "content": prompt}]}
    try:
        response = requests.post(url, headers=headers, json=payload)
        res = response.json()
        if "error_code" in res:
            # 这里会自动打印出报错码，方便我们排查
            return f"AI 错误({res['error_code']}): {res.get('error_msg')}"
        
        # 二次强力去噪清理
        raw_result = res.get("result", "").strip()
        clean_text = re.sub(r'\d+', ' ', raw_result)
        for junk in ["目的地", "地名", "地点", "：", ":", ".", "、", "接", "住", "前往", "返程", "车程"]:
            clean_text = clean_text.replace(junk, " ")
        return " ".join(clean_text.split())
    except Exception as e:
        return f"AI 连接异常: {str(e)}"

def rule_extract_locations(text):
    """【旗舰级】自动规则提取：极致正则表达式暴力去除非地名文字"""
    if not text: return ""
    # 1. 最核心：删掉所有括号及其内容 (车程约3h)
    clean_text = re.sub(r'\(.*?\)', ' ', text)
    clean_text = re.sub(r'（.*?）', ' ', clean_text)
    # 2. 精准剔除日期 (如4.11)
    clean_text = re.sub(r'\d+\.?\d*', ' ', clean_text)
    
    # 3. 过滤掉常见干扰词
    for word in ['接', '送', '前往', '返程', '车程', '约', 'h', '住', '陶阳里', '滕王阁', '陶溪川']:
        clean_text = clean_text.replace(word, ' ')
    
    # 4. 针对昨天那连在一起的词，可以用正则拆分预处理（因为规则提取不能理解意思）
    clean_text = re.sub(r'陶阳里滕王阁', '陶阳里 滕王阁', clean_text)
        
    return " ".join(clean_text.split()).strip()

# ==================== 3. 侧边栏：核心报价计费 ====================

if 'km_auto' not in st.session_state: st.session_state['km_auto'] = 0

with st.sidebar:
    st.header("📊 报价核算中心")
    # 需求修改 1：取消折叠，常开
    st.subheader("⚙️ 计费标准设置")
    col_a, col_b = st.columns(2)
    b39 = col_a.number_input("39座起步费", value=800)
    p39 = col_b.number_input("39座单价", value=2.6)
    b56 = col_a.number_input("56座起步费", value=1000)
    p56 = col_b.number_input("56座单价", value=3.6)

    st.divider()
    # 这里的公里优先读取地图计算的记忆值
    f_km = st.number_input("实测总公里 (KM)", value=st.session_state['km_auto'])
    f_days = st.number_input("用车总天数 (天)", value=4)
    
    res_39 = int(f_km * p39 + f_days * b39)
    res_56 = int(f_km * p56 + f_days * b56)
    
    st.markdown("### 💰 实时总报单")
    st.success(f"🚌 **39座大巴：{res_39} 元**")
    st.info(f"🚌 **56座大巴：{res_56} 元**")

    # 需求修改 2：增加可复制发送文本框
    st.divider()
    st.markdown("📄 **报价发送文案 (全选复制)**")
    quote_text = (
        f"【九江祥隆旅游运输报价单】\n"
        f"实测公里数：{f_km} KM\n"
        f"用车总天数：{f_days} 天\n"
        f"--------------------\n"
        f"🚌 39座大巴全包价：{res_39} 元\n"
        f"🚌 56座大巴全包价：{res_56} 元\n"
        f"（包含全包车费用）"
    )
    st.text_area("直接复制此文字发给客户：", value=quote_text, height=180)

# ==================== 4. 主页面：流程操作 ====================
st.header("🚌 九江祥隆旅游运输报价系统 (AI 旗舰版)")
m_left, m_right = st.columns([1, 1.2])

with m_left:
    st.markdown("### 1️⃣ 行程文字识别 (OCR)")
    up_file = st.file_uploader("上传截图", type=["jpg", "png", "jpeg"])
    if up_file:
        img_bytes = up_file.read()
        st.image(img_bytes, width=300)
        if st.button("🚀 开始文字提取识别", use_container_width=True):
            with st.spinner('文字提取中...'):
                st.session_state['ocr_raw'] = ocr_engine(img_bytes)
    
    raw_txt = st.text_area("校对文本框 (如要改顺序请改这里)：", value=st.session_state.get('ocr_raw', ""), height=150)
    
    st.markdown("---")
    # 需求修改 3：保留两个提取方案
    st.markdown("#### **站点提取方案选择**")
    c1, c2 = st.columns(2)
    
    if c1.button("✨ 智能 AI 提取", use_container_width=True):
        if raw_txt:
            with st.spinner('大模型正在智能读心提取所有地名...'):
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
    # 这就是你今天发的那段干净的结果，代码会自动填到这里
    site_input = st.text_input("待匹配关键词 (空格隔开，AI提取的站点会在这里排队)：", value=st.session_state.get('sites_final', ""))
    
    confirmed_locs = []
    if site_input:
        # 去掉自动识别中可能带入的标点
        clean_site_input = site_input.replace(",", " ").replace("，", " ")
        names = clean_site_input.split()
        for i, name in enumerate(names):
            if not name.strip(): continue
            url = f"https://restapi.amap.com/v3/assistant/inputtips?keywords={name}&key={AMAP_KEY}"
            try:
                tips = requests.get(url).json().get('tips', [])
                valid_tips = [t for t in tips if t.get('location')]
                if valid_tips:
                    # 分站确认下拉框
                    sel = st.selectbox(f"确认第 {i+1} 站: {name}", [f"{t['name']} ({t.get('district','')})" for t in valid_tips], key=f"site_sel_{i}")
                    coord = next(t['location'] for t in valid_tips if sel.startswith(t['name']))
                    confirmed_locs.append(coord)
            except: pass

    # 需求修改 4：去掉按钮，直接显示计算出的公里数
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
                st.success(f"🚩 规划成功！实测公里数：{km_val} KM。报价已实时更新！")
            else:
                st.error("高德地图无法计算此路径，请检查站点模糊。")
        except:
            st.error("地图测距服务异常，请检查高德 KEY。")
