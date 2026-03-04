import streamlit as st
import pandas as pd

st.set_page_config(page_title="包车报价助手", layout="wide")

# 侧边栏修改单价
st.sidebar.header("⚙️ 价格配置")
p39_km = st.sidebar.number_input("39座-每公里(元)", value=2.6)
p39_day = st.sidebar.number_input("39座-每天(元)", value=700)
p56_km = st.sidebar.number_input("56座-每公里(元)", value=3.6)
p56_day = st.sidebar.number_input("56座-每天(元)", value=900)

st.title("🚌 包车报价统一计算系统")

# 输入数据
c1, c2 = st.columns(2)
with c1:
    km_input = st.number_input("高德导航公里数", min_value=0.0, step=1.0)
    final_km = round(km_input)
with c2:
    days = st.number_input("用车天数", min_value=1, step=1)

# 计算结果
results = [
    {
        "车型": "39座", 
        "预计公里": f"{final_km}KM", 
        "公里费": round(final_km * p39_km, 2),
        "用车天数": days,
        "包车费总": days * p39_day,
        "总报价": round(final_km * p39_km + days * p39_day, 2)
    },
    {
        "车型": "56座", 
        "预计公里": f"{final_km}KM", 
        "公里费": round(final_km * p56_km, 2),
        "用车天数": days,
        "包车费总": days * p56_day,
        "总报价": round(final_km * p56_km + days * p56_day, 2)
    }
]

# 显示表格
st.subheader("📋 报价明细表")
st.table(pd.DataFrame(results))

# 微信一键生成
if st.button("生成微信报价文本"):
    msg = f"【包车报价单】\n里程：{final_km}公里\n天数：{days}天\n"
    for r in results:
        msg += f"👉{r['车型']}：{r['总报价']}元\n"
    st.code(msg)
