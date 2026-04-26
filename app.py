import re
import streamlit as st
from src.data_loader import get_stock_data, get_market_evidence
from src.analyzer import analyze_stock
from src.capital_manager import calculate_investment_plan


def normalize_ticker(raw: str) -> str:
    s = raw.strip().upper()
    if not s:
        return s
    if "." in s:
        return s
    if re.match(r'^\d{4,6}[A-Z]?$', s):
        return s + ".TW"
    return s


# --- 0. 網頁配置 ---
st.set_page_config(page_title="DipMaster Lite — 快速乖離診斷", layout="wide")

# --- 1. 核心數據載入 ---
if 'evidence' not in st.session_state:
    with st.spinner("正在同步全球實證數據..."):
        st.session_state.evidence = get_market_evidence()

ev = st.session_state.evidence

# --- 2. 全球戰情實證看板 ---
st.subheader("🌐 1. 全球戰情實證看板 (Global Command Center)")
st.caption(f"🕒 數據最後同步：{ev['Last_Synced']} | 來源：TWSE, Yahoo Finance")

row1_1, row1_2, row1_3 = st.columns(3)
with row1_1:
    st.metric("台股 P/E (TWSE)", f"{ev['TAIEX_PE']}x", ev['TAIEX_Label'])
    st.line_chart(ev['PE_Hist'], height=150)
with row1_2:
    st.metric("美股 SPY 位階", ev['Metrics'].get('美股標普', 'N/A'), "S&P 500 對比 240MA")
    if '美股標普' in ev['Charts']: st.line_chart(ev['Charts']['美股標普'], height=150)
with row1_3:
    st.metric("匯率 (USD/TWD)", f"{ev['Metrics'].get('美元匯率', 'N/A')}", f"位階: {ev.get('FX_Percentile', 50)}%")
    if '美元匯率' in ev['Charts']: st.line_chart(ev['Charts']['美元匯率'], height=150)

row2_1, row2_2, row2_3 = st.columns(3)
with row2_1:
    st.metric("台指位階 (TAIEX)", ev['Metrics'].get('台指位階', 'N/A'), "對比 240MA")
    if '台指位階' in ev['Charts']: st.line_chart(ev['Charts']['台指位階'], height=150)
with row2_2:
    st.metric("納指 QQQ 位階 (科技)", ev['Metrics'].get('納指科技', 'N/A'), "科技成長核心錨點")
    if '納指科技' in ev['Charts']: st.line_chart(ev['Charts']['納指科技'], height=150)
with row2_3:
    st.metric("恐懼指標 (VIX)", f"{ev['Metrics'].get('VIX', 'N/A')}", "市場波動率")
    if 'VIX' in ev['Charts']: st.area_chart(ev['Charts']['VIX'], height=150)

st.divider()

# --- 3. 側邊欄：指揮中心 ---
with st.sidebar:
    st.header("🎯 指揮中心")
    raw_symbol = st.text_input("標的代號 (如 QQQ / 2330.TW / 0050.TW)", "QQQ")
    symbol = normalize_ticker(raw_symbol)
    if symbol != raw_symbol.strip().upper():
        st.caption(f"✅ 已自動轉換為：`{symbol}`")
    budget = st.number_input("總預算 (TWD)", value=1000000)
    n_batches = st.slider("加碼批次 (N)", 1, 20, 5)
    st.divider()
    run = st.button("🚀 啟動數據導航")

# --- 4. 決策診斷區 ---
if run:
    is_us = not (symbol.endswith(".TW") or symbol.endswith(".TWO"))
    with st.spinner(f'正在進行 {symbol} 深度診斷...'):
        df = get_stock_data(symbol)
        if df is not None:
            ana = analyze_stock(df)
            plan = calculate_investment_plan(budget, n_batches, ana, ev, is_us)

            # 資金管理建議
            st.subheader("💰 2. 資金管理建議")
            s1, s2, s3 = st.columns(3)
            s1.metric("計畫配置總額", f"${plan['summary']['allocated']:,.0f}")
            s2.metric("剩餘備用購買力", f"${budget - plan['summary']['allocated']:,.0f}")
            s3.metric("本金使用率", f"{plan['summary']['usage']:.1f}%")
            st.progress(plan['summary']['usage'] / 100)

            # 診斷報告
            st.divider()
            st.subheader(f"📊 3. {symbol} 專家診斷報告")

            if plan['summary'].get('is_downtrend', False):
                st.error("🚨 警告：目前標的處於下彎趨勢 (Slope < 0)，階梯計畫僅供參考，不建議立即執行。")
            else:
                st.success("✅ 趨勢實證：目前標的長期趨勢向上，具備較高安全邊際。")

            st.info(ana['Narrative'])

            # 決策建議總表
            if not plan['table'].empty:
                st.write("### 📋 決策建議總表 (The Master Table)")
                st.dataframe(plan['table'], width="stretch")
        else:
            st.error(f"❌ 無法讀取 '{symbol}' 數據。請確認代號是否正確（台股請加 .TW），或稍後再試。")

# --- 5. 系統運算邏輯說明 ---
st.divider()
with st.expander("📝 查看軍師運算邏輯 (Calculation Methodology)"):
    st.write("### 核心決策實證邏輯")
    st.markdown(r"#### 1. 趨勢過濾：斜率攔截 (V1.7 核心)")
    st.write("利用 240MA 之線性回歸斜率判斷長期慣性。若斜率 < 0，系統會發出警示以避免「接落下的刀子」。")

    st.markdown(r"#### 2. 觸發條件：還原年線負乖離 ($Bias\%$)")
    st.latex(r"Bias\% = \frac{Price_{adj} - 240MA_{adj}}{240MA_{adj}}")

    st.markdown(r"#### 3. 目標成交價精算 (Target Price)")
    st.latex(r"Target\ Price = Current\ Price \times (1 + Bias_{target}\%)")

    st.info("💡 數據實證：本系統所有指標皆由即時 API 抓取，杜絕人為誤判。")
