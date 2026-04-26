# DipMaster Lite — 快速乖離診斷

> 年線乖離階梯加碼法（240MA Bias Ladder DCA）的輕量實作
> 快速診斷 ETF 目前乖離率，產出分批買入計畫與梯子視覺化圖表

**Live Demo**: [dipmaster-lite-b8v8na4gubqcmum7urzhv2.streamlit.app](https://dipmaster-lite-b8v8na4gubqcmum7urzhv2.streamlit.app/)
**GitHub**: [JenniTzu/dipmaster-lite](https://github.com/JenniTzu/dipmaster-lite)

---

## 功能概覽

| 區塊 | 內容 |
| --- | --- |
| 🌐 全球戰情看板 | 台股 P/E 百分位、SPY/QQQ/台指對比年線、VIX 情境標籤、USD/TWD 5 年百分位 |
| 📊 個股診斷 | 即時 Bias%、MA240 斜率（含數值）、趨勢閘門判斷 |
| 📈 梯子視覺化 | Plotly 互動圖：近 120 日收盤價 × MA240 × 各批次目標線（黃→綠→青→藍漸層） |
| 📋 決策建議總表 | N 批階梯觸發點、目標成交價、投入金額、建議股數、加權均成（幣別標示） |
| 📖 策略白皮書 | 四大學術支柱、完整公式、指標解讀框架、適用條件 |
| 📝 決策速查卡 | 三步決策流程、4 個 LaTeX 公式、兩個保護機制 |

---

## 投資策略核心

**策略名稱**：年線乖離階梯加碼法（240MA Bias Ladder DCA）

| 元素 | 設計 |
| --- | --- |
| 均值錨點 | 240 日移動平均線（MA240，約 1 個完整交易年） |
| 觸發條件 | `Bias% = (Price_adj − MA240) / MA240 × 100`，Bias% < 0 進入買入觀察區 |
| 趨勢閘門 | `Slope = MA240[t] − MA240[t-5]`（5 日有限差分），Slope < 0 暫緩加碼 |
| 目標價計算 | `Target_n = MA240 × (1 + Bias_n / 100)`，每批間距 2%，錨點為年線非現價 |
| 資金分配 | 等額分批（總預算 ÷ N），台股支援零股，美股以整股計算 |

**學術依據**：De Bondt & Thaler (1985) 均值回歸、Statman (1995) DCA、Graham 安全邊際、Faber (2007) 趨勢過濾

---

## 快速開始

```bash
pip install -r requirements.txt
streamlit run app.py
```

### 標的代號輸入規則

| 輸入 | 系統行為 |
| --- | --- |
| `0050` / `00878` | 自動補全為 `0050.TW` / `00878.TW` |
| `0056.TWO` | 直接輸入（TPEx 上市，不自動補全） |
| `QQQ` / `SPY` | 美股直接輸入 |
| `2330.TW` | 台股個股（含後綴直接輸入） |

> 注意：本工具設計用於**寬基指數 ETF**，不適合個股或槓桿 ETF。

---

## 系統架構

```text
data_loader.py → analyzer.py → capital_manager.py → app.py
```

| 模組 | 職責 | 關鍵輸出 |
| --- | --- | --- |
| `src/data_loader.py` | 平行抓取市場數據（ThreadPoolExecutor × 5） | `get_stock_data()` → DataFrame；`get_market_evidence()` → 全球指標 dict |
| `src/analyzer.py` | 計算 Bias%、斜率、趨勢判斷 | 7 key dict：`Current_Price`, `MA240`, `Bias_%`, `Is_Downtrend`, `Slope`, `MA240_Reliable`, `Narrative` |
| `src/capital_manager.py` | 產出 N 批階梯買入計畫 | summary dict + 8 欄 DataFrame（含幣別標示加權均成） |
| `app.py` | Streamlit UI、梯子圖、所有警示邏輯 | 網頁前端 |

### 關鍵設計細節

- **MA240_Reliable**：當歷史資料 < 240 個交易日，以擴展均值替代並顯示警告，避免靜默精度劣化
- **正乖離預演模式**：Bias% > 0 時系統顯示警告，計畫為預演而非即時建議
- **幣別明確標示**：加權均成欄位顯示 `(USD/股)` 或 `(TWD/股)`，預算摘要使用 `NT$`
- **VIX 情境標籤**：5 個區間（平靜 / 低波動 / 正常 / 恐慌 / 極度恐慌）自動標示
- **資料快取**：`get_market_evidence()` 存於 `st.session_state`，瀏覽器 session 有效，可點「🔄 重新整理」強制更新

---

## 資料來源

| 來源 | 數據 | 更新頻率 |
| --- | --- | --- |
| Yahoo Finance (yfinance) | 個股/ETF 收盤價、SPY/QQQ/^TWII/^VIX/TWD=X | EOD（收盤後） |
| TWSE 證交所 API | 台股加權指數本益比歷史序列 | 月報 |

---

## 技術棧

- **Frontend**: Streamlit Community Cloud（免費部署，push to `main` 自動上線）
- **Charts**: Plotly（互動式梯子圖）
- **Data**: yfinance + TWSE API + pandas
- **Concurrency**: `ThreadPoolExecutor(max_workers=5)` 平行抓取全球指標

---

## 與 DipMaster Pro 的差異

本工具為 **Lite 版**，定位為快速單標的診斷。完整版（[DipMaster Pro](https://dipmaster-navigator-tzutzu.streamlit.app/)）另含：市場週期五指標系統、反向金字塔資金池、LINE 通知、機會過期偵測、AuditLogger 等進階功能。

詳細差異對照請參閱 [`differences_lite_vs_pro.txt`](differences_lite_vs_pro.txt)。

---

## 免責聲明

本工具所有分析結果僅供教育與研究參考，不構成任何形式之投資建議。投資涉及風險，過去績效不代表未來表現。
