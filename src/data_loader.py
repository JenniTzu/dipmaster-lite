# 檔案位置： src/data_loader.py

import yfinance as yf
import pandas as pd
import requests
import io
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. 個股偵察兵 (台股抗斷線強化版 + V1.7 斜率) ---
def get_stock_data(ticker):
    """【連線強化版】解決台股讀取不到的問題，並計算 V1.7 斜率"""
    try:
        stock = yf.Ticker(ticker)
        # 嘗試抓取 5 年資料，強制還原權息
        df = stock.history(period="5y", auto_adjust=True)
        
        # 💡 若歷史資料為空 (Yahoo 常見 bug)，嘗試改用 1 年資料作為緩衝
        if df.empty:
            df = stock.history(period="1y", auto_adjust=True)
            
        if df.empty:
            return None
            
        # 計算 V1.7 斜率與 240MA
        df['MA240'] = df['Close'].rolling(window=240).mean()
        # 補齊最近的 MA240 (若資料不足 240 筆，則用現有資料平均)
        if df['MA240'].isnull().all():
            df['MA240'] = df['Close'].expanding().mean()
            
        df['MA240_Slope'] = df['MA240'].diff(5)
        return df
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None

# --- 2. 證交所 P/E 抓取 ---
def get_dynamic_taiex_pe_info_with_hist():
    """從證交所抓取 P/E 並回傳歷史數列"""
    try:
        url = "https://www.twse.com.tw/indicesReport/MI_5MINS_HIST?response=csv"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        
        content = res.content.decode('cp950', errors='ignore')
        df = pd.read_csv(io.StringIO(content), skiprows=1)
        df.columns = [c.strip() for c in df.columns]
        df = df[df['日期'].str.contains("/", na=False)].copy()
        
        pe_series = pd.to_numeric(df['本益比'], errors='coerce').dropna()
        if pe_series.empty:
            return {'latest': 18.2, 'label': "中性", 'history': pd.Series([18.2]*20)}
            
        latest = float(pe_series.iloc[-1])
        pct = (pe_series < latest).mean() * 100
        label = "偏高" if pct > 70 else ("偏低" if pct < 30 else "中性")
        
        return {'latest': latest, 'label': f"{pct:.1f}% ({label})", 'history': pe_series}
    except:
        return {'latest': 18.2, 'label': "72% (中性)", 'history': pd.Series([18.2]*20)}

# --- 3. 全球戰情實證看板數據整合 ---
def get_market_evidence():
    """整合台美數據與歷史趨勢"""
    pe_info = get_dynamic_taiex_pe_info_with_hist()
    
    evidence = {
        'TAIEX_PE': pe_info['latest'],
        'TAIEX_Label': pe_info['label'],
        'PE_Hist': pe_info['history'],
        'Charts': {},
        'Metrics': {},
        'Last_Synced': datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    try:
        configs = {
            "SPY": "美股標普",
            "QQQ": "納指科技",
            "^TWII": "台指位階",
            "^VIX": "VIX",
            "TWD=X": "美元匯率"
        }

        def _fetch(ticker):
            period = "5y" if ticker == "TWD=X" else "1y"
            return ticker, yf.Ticker(ticker).history(period=period)

        results = {}
        with ThreadPoolExecutor(max_workers=5) as ex:
            futures = {ex.submit(_fetch, t): t for t in configs}
            for future in as_completed(futures):
                ticker, hist = future.result()
                results[ticker] = hist

        fx_5y_close = None
        for ticker, name in configs.items():
            hist = results.get(ticker)
            if hist is None or hist.empty:
                continue
            close = hist['Close']
            if ticker not in ["^VIX", "TWD=X"]:
                ma240 = close.rolling(window=240).mean()
                bias = ((close - ma240) / ma240) * 100
                evidence['Charts'][name] = bias.dropna()
                evidence['Metrics'][name] = f"{bias.iloc[-1]:.1f}%"
            else:
                evidence['Charts'][name] = close.iloc[-365:]
                evidence['Metrics'][name] = round(float(close.iloc[-1]), 2)
                if ticker == "TWD=X":
                    fx_5y_close = close

        if fx_5y_close is not None:
            curr_fx = evidence['Metrics']['美元匯率']
            evidence['FX_Percentile'] = round((fx_5y_close < curr_fx).mean() * 100, 1)

    except Exception as e:
        print(f"⚠️ 全球數據異常: {e}")
        
    return evidence