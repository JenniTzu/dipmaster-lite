import re
import streamlit as st
import plotly.graph_objects as go
from src.data_loader import get_stock_data, get_market_evidence
from src.analyzer import analyze_stock
from src.capital_manager import calculate_investment_plan


def build_ladder_chart(df, table, ana, symbol):
    recent_close = df['Close'].tail(120)
    recent_ma240 = df['MA240'].tail(120)
    current_price = ana['Current_Price']

    fig = go.Figure()

    # 收盤價
    fig.add_trace(go.Scatter(
        x=recent_close.index, y=recent_close.values,
        name='收盤價', mode='lines',
        line=dict(color='#90E0EF', width=2),
        hovertemplate='%{x|%Y-%m-%d}　收盤：%{y:.2f}<extra></extra>'
    ))

    # MA240 年線
    valid_ma = recent_ma240.dropna()
    if not valid_ma.empty:
        fig.add_trace(go.Scatter(
            x=valid_ma.index, y=valid_ma.values,
            name='MA240 年線', mode='lines',
            line=dict(color='#FFB703', width=2, dash='dot'),
            hovertemplate='MA240：%{y:.2f}<extra></extra>'
        ))

    # 現價線
    fig.add_hline(
        y=current_price,
        line=dict(color='rgba(255,255,255,0.9)', width=2),
        annotation_text=f"現價 {current_price:.2f}",
        annotation_position="top right",
        annotation=dict(
            font=dict(size=11, color='#FFFFFF'),
            bgcolor='rgba(30,30,30,0.6)', borderpad=4
        )
    )

    # 批次目標線（前幾批淺綠 → 中段橘 → 深部深紅，越深越有安全邊際）
    batch_colors = [
        '#b7e4c7', '#74c69d', '#40916c', '#1b4332',
        '#fca311', '#f48c06', '#e85d04',
        '#dc2f02', '#9d0208', '#6a040f',
    ]

    for idx, row in table.iterrows():
        color = batch_colors[min(idx, len(batch_colors) - 1)]
        target = row['目標成交價']
        label = f"  {row['階梯']}  {row['觸發條件 (Bias%)']}  →  {target:.2f}"
        yanchor = "top" if idx % 2 == 0 else "bottom"
        fig.add_hline(
            y=target,
            line=dict(color=color, width=1.2, dash='dash'),
            annotation_text=label,
            annotation_position="right",
            annotation=dict(
                font=dict(size=9, color=color),
                yanchor=yanchor, xanchor="left"
            )
        )

    fig.update_layout(
        title=dict(text=f"📍 {symbol}　近 120 日走勢 × 加碼梯子", font=dict(size=15)),
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.07)', tickformat='%m/%d'),
        yaxis=dict(title='價格', showgrid=True, gridcolor='rgba(255,255,255,0.07)'),
        template='plotly_dark',
        height=500,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        hovermode='x unified',
        margin=dict(l=60, r=210, t=60, b=40)
    )

    return fig


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

col_title, col_refresh = st.columns([6, 1])
with col_title:
    st.caption(f"🕒 數據最後同步：{ev['Last_Synced']} | 來源：TWSE, Yahoo Finance")
with col_refresh:
    if st.button("🔄 重新整理"):
        del st.session_state['evidence']
        st.rerun()

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

            st.subheader("💰 2. 資金管理建議")
            s1, s2, s3 = st.columns(3)
            s1.metric("計畫配置總額", f"${plan['summary']['allocated']:,.0f}")
            s2.metric("剩餘備用購買力", f"${budget - plan['summary']['allocated']:,.0f}")
            s3.metric("本金使用率", f"{plan['summary']['usage']:.1f}%")
            st.progress(plan['summary']['usage'] / 100)

            st.divider()
            st.subheader(f"📊 3. {symbol} 專家診斷報告")

            if plan['summary'].get('is_downtrend', False):
                st.error("🚨 警告：目前標的處於下彎趨勢 (Slope < 0)，階梯計畫僅供參考，不建議立即執行。")
            else:
                st.success("✅ 趨勢實證：目前標的長期趨勢向上，具備較高安全邊際。")

            st.info(ana['Narrative'])

            if not plan['table'].empty:
                st.write("### 📈 加碼梯子視覺化 (Ladder Chart)")
                st.plotly_chart(
                    build_ladder_chart(df, plan['table'], ana, symbol),
                    use_container_width=True
                )

                st.write("### 📋 決策建議總表 (The Master Table)")
                st.dataframe(plan['table'], use_container_width=True)
                if not is_us:
                    st.caption("💡 台股支援零股交易，以整股計算。「加權平均成本 (每股)」單位為台幣（TWD）。")
                if len(plan['table']) < n_batches:
                    st.warning(f"⚠️ 部分批次因每批預算低於單股成交價而略過，實際執行 {len(plan['table'])}/{n_batches} 批。建議提高總預算或減少批次數。")
        else:
            st.error(f"❌ 無法讀取 '{symbol}' 數據。請確認代號是否正確（台股請加 .TW），或稍後再試。")

# --- 5. 策略白皮書 ---
st.divider()
with st.expander("📖 策略白皮書：為什麼這樣買？(Investment Strategy Report)"):
    st.markdown("## 年線乖離階梯加碼法（240MA Bias Ladder DCA）")
    st.caption("Strategy Report v1.0 | 本白皮書對應 STRATEGY_REPORT.txt 完整版")

    st.markdown("### 策略分類")
    st.info("**策略類型**：價值錨點 × 技術過濾 × 系統性分批買入  \n**適用標的**：具備長期正報酬歷史的寬基 ETF（如 QQQ、SPY、0050.TW）  \n**核心信仰**：優質資產的長期均值回歸特性，系統紀律優於主觀判斷")

    st.markdown("### 四大學術支柱")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 1. 均值回歸（Mean Reversion）")
        st.write("De Bondt & Thaler (1985) 研究顯示，過度下跌的資產長期會回歸歷史均值。本系統以 240 日均線（MA240，約一個完整交易年）作為長期均值的代理指標，價格低於 MA240 即進入潛在價值買入區。")

        st.markdown("#### 2. 分批買入降低時間風險（Systematic DCA）")
        st.write("Statman (1995) 研究顯示，相較一次性全倉，分批買入能有效降低擇時錯誤的衝擊，在波動市場取得更優的平均成本。本系統將資金等分為 N 批，每批以固定 2% 乖離率間距遞進，愈跌愈買，自動實現成本平攤。")

    with col_b:
        st.markdown("#### 3. 安全邊際（Margin of Safety）")
        st.write("Benjamin Graham《智慧型股票投資人》：以低於內在價值的價格買入，可提供下行緩衝。乖離率為負（價格低於年均值）即是本系統定義的「安全邊際區」，乖離率每下跌 2% 觸發一個新批次，邊際安全性遞增。")

        st.markdown("#### 4. 趨勢過濾防止落刃（Slope Intercept）")
        st.write("Faber (2007) 量化研究顯示，加入移動平均趨勢過濾能顯著提升長期報酬並降低最大回撤。本系統計算 MA240 的 5 日斜率，若斜率 < 0（年線轉頭向下），發出警告暫緩加碼，等待趨勢確認翻多後再進場。")

    st.divider()
    st.markdown("### 核心指標計算邏輯")

    st.markdown("#### 年線乖離率（Bias%）— 核心觸發指標")
    st.latex(r"Bias\% = \frac{Price_{adj} - MA240_{adj}}{MA240_{adj}} \times 100")
    st.write("使用「還原股利後收盤價（Adjusted Close）」計算，避免配息造成技術失真。Bias% < 0 代表價格位於年線之下，進入加碼觀察區。")

    st.markdown("#### MA240 斜率（Slope）— 趨勢閘門")
    st.latex(r"Slope = MA240_{today} - MA240_{5\ days\ ago}")
    st.write("Slope > 0：年線向上，趨勢健康可加碼。Slope < 0：年線轉頭，發出紅色警報，暫緩執行。")

    st.markdown("#### 階梯觸發價（Target Price）")
    st.latex(r"Target\_Price_n = MA240 \times (1 + (Bias\%_{current} - (n-1) \times 2\%))")
    st.write("每批間距固定 2%，第一批不得高於當前市價。每批投入金額 = 總預算 ÷ N（等額分配）。")

    st.divider()
    st.markdown("### 各市場指標解讀框架")

    d1, d2, d3 = st.columns(3)
    with d1:
        st.markdown("**台股 P/E 百分位**")
        st.write("< 30%：歷史低估，有利加碼  \n30–70%：中性  \n> 70%：偏高，提高戒心")
    with d2:
        st.markdown("**VIX 恐懼指數**")
        st.write("< 15：市場平靜，折價有限  \n20–30：正常波動，可觀察  \n> 30：市場恐慌，歷史加碼良機  \n> 40：黑天鵝極端恐慌")
    with d3:
        st.markdown("**USD/TWD 匯率百分位（5年）**")
        st.write("美元偏強（高百分位）：換匯成本高  \n美元偏弱（低百分位）：換匯時機相對有利")

    st.divider()
    st.markdown("### 策略適用條件")
    ok1, ok2 = st.columns(2)
    with ok1:
        st.success("✅ **適用**\n- 寬基指數 ETF（S&P 500、NASDAQ-100、台灣 50）\n- 長期持有 3 年以上\n- 接受短期帳面虧損，相信長期均值回歸")
    with ok2:
        st.error("❌ **不適用**\n- 個股（可能永久下市，無均值回歸保障）\n- 槓桿型 ETF（內含損耗，長期不具均值回歸）\n- 需短期動用的緊急備用金")

    st.caption("⚠️ 免責聲明：本系統所有分析結果僅供教育與研究參考，不構成任何形式之投資建議。投資涉及風險，過去績效不代表未來表現。")

# --- 6. 系統運算邏輯說明 ---
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
