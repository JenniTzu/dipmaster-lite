這是一份為妳整理的 **DipMaster 投資導航系統 Ver 2.4 終極實戰導航版** 的 `.md` 檔案內容。

我已經將我們今天討論的所有優化細節——包含 **0-20 批次彈性、年線斜率攔截機制、加權平均成本實證、以及前端數據實證層**——全部整合進這份最新的工程藍圖中。妳可以直接複製這段內容到妳的 `README.md` 或專案文件中。

---

# 專案規畫書：DipMaster 投資導航系統 (Ver 2.4 終極實戰導航版)

## 一、 專案定位與願景
[cite_start]建立一個基於數據驅動（Data-Driven）的自動化投資系統。透過「還原股價位階」與「資金階梯計畫」在風險受控（Slope 攔截）下，加速平均成本下降並極大化複利效果，解決定期定額累積速度過慢的痛點 [cite: 48-50]。

## 二、 專業級系統架構 (Decoupled Architecture)
[cite_start]採用解耦架構，將數據獲取、邏輯分析與資金管理徹底分離，確保系統具備高度的可測試性與金融級嚴謹度 [cite: 51-52]：

```text
05_DipMaster_Navigator/
├── src/                     # 核心邏輯模組
│   ├── data_loader.py       # 【偵查兵】負責還原股價、VIX、P/E、匯率抓取
│   ├── analyzer.py           # 【軍師】負責算位階、240MA 斜率與診斷文案
│   └── capital_manager.py    # 【精算師】負責 0-20 批計畫、平均成本試算
├── app.py                   # 【接待員】Streamlit 網頁主程式 (UI 介面)
├── requirements.txt         # 套件清單
└── README.md                # 專案說明書 (本文件)
```

| 模組名稱 | 角色定位 | 核心職責 |
| :--- | :--- | :--- |
| **Data Loader** | 偵查兵 | 抓取 5 年還原股價、VIX、台股 P/E、USD/TWD 歷史匯率。 |
| **Logic Analyzer** | 軍師 | [cite_start]計算 $Bias\%$ 分位點、240MA 斜率 ($Slope$) 與攔截信號 [cite: 52, 59]。 |
| **Capital Manager** | 精算師 | [cite_start]處理 0-20 批加碼計畫、**加權平均成本追蹤** 與 匯率換算 [cite: 52, 66-67]。 |
| **UI Controller** | 接待員 | [cite_start]Streamlit 前端網頁，呈現數據實證看板與執行建議表 [cite: 52, 82-83]。 |

---

## 三、 核心業務邏輯 (Business Logic)

### 1. 財務數據運算：還原指標與趨勢
* **還原年線乖離位階**：
  $$Bias\% = \frac{Price_{adj} - 240MA_{adj}}{240MA_{adj}}$$
  [cite_start]計算該指標在過去 **5 年** 數據中的歷史分位點 ($Percentile$) [cite: 55-57]。
* **空頭鈍化過濾 (Interceptor)**：
  [cite_start]計算 240MA 斜率 ($Slope$)。若 $Slope < 0$ (下彎)，系統強制攔截資金投入，建議水位歸零 [cite: 58-60]。

### 2. 資金與成本實證
* **加權平均成本 (Avg Cost)**：
  $$\text{New Avg Cost} = \frac{(\text{Prev Shares} \times \text{Prev Avg}) + (\text{New Shares} \times \text{New Price})}{\text{Total Shares}}$$
  [cite_start]確保每一次加碼皆有明確的成本降幅實證 [cite: 66-67]。
* [cite_start]**自動匯率轉換**：偵測標的（美股/台股），自動按 USD/TWD 匯率換算預算（無條件捨去至整數股） [cite: 62-65]。

---

## 四、 前端介面設計 (UX Spec)

* **1. 市場環境掃描 (Global Gauges)**：
    * 顯示 VIX、台股 P/E 與 USD/TWD 匯率。
    * [cite_start]**數據實證**：數值下方標註 5 年位階，若台幣過弱 (FX > 80%) 則標註「避險不換匯」 [cite: 50-51]。
* **2. 用戶指揮中心 (Inputs)**：
    * 支援美股/台股標的、總加碼本金。
    * **彈性批次**：支援使用者手動輸入 **0 - 20 批** 加碼計畫。
* **3. 專家診斷看板 (Expert Narrative)**：
    * [cite_start]以專業分析師口吻動態產出診斷：包含位階判斷、趨勢預警與執行指令 [cite: 78-81]。
* **4. 決策建議總表 (Master Table)**：
    * [cite_start]包含：觸發條件、目標成交價、投入金額 (TWD/USD)、建議股數、**累積平均成本** [cite: 82-83]。

---

## 五、 重要結論與技術定案 (Critical Decisions)

1.  [cite_start]**數據準確性**：全系統強制使用 **「還原股價 (Adjusted Price)」** 排除息值干擾 [cite: 55-56]。
2.  **數據頻率**：定案為 **EOD (收盤後運算)**，隔日掛單，維持 $0 元 API 成本。
3.  [cite_start]**戰略攔截**：將「趨勢方向」視為資金准入的首要條件，斜率下彎則計畫自動失效 [cite: 60]。
4.  **模組解耦**：移除 `calculator.py`，將邏輯收納至軍師與精算師模組，提升維護效率。

---

## 六、 $0 元技術棧 (The $0 Stack)

* **雲端網頁**：Streamlit Community Cloud (Free)。
* **核心語言**：Python 3.10+。
* **數據來源**：yfinance (提供歷史 Adj Close 與宏觀指標)。
* **自動化**：GitHub Actions (每日收盤後自動掃描)。

---

## 七、 待辦事項：Version 3.0 Backlog
* [ ] 實作「一鍵傳送至 LINE」掛單通知。
* [ ] 多檔自選股 (Watchlist) 循環掃描雷達模式。
* [ ] 手續費與稅金自動精算模組。

---

### 👨‍💻 技術負責人的最後結語
這份 Ver 2.4 規格書已經完成從「想法」到「金融級工具」的蛻變。透過 **「軍師」** 的趨勢把關與 **「精算師」** 的成本導航，我們不僅是在寫程式，更是在建立一套能對抗市場恐懼、加速複利累積的數據體系。妳現在擁有的，是一個確定性的投資 Agent 架構。