# 檔案位置： src/analyzer.py
import pandas as pd

def analyze_stock(df):
    """軍師模組：負責技術面數據的計算與診斷"""
    # 確保不會因為空數據當機
    if df is None or df.empty:
        return {'Current_Price': 0, 'MA240': 0, 'Bias_%': 0, 'Is_Downtrend': False, 'Narrative': "無效數據"}
    
    current_price = df['Close'].iloc[-1]
    
    # 安全抓取 240MA，若無則用現價代替
    if 'MA240' in df.columns and not pd.isna(df['MA240'].iloc[-1]):
        ma240 = df['MA240'].iloc[-1]
    else:
        ma240 = current_price
        
    bias = ((current_price - ma240) / ma240) * 100 if ma240 else 0
    
    # V1.7 斜率判斷 (防禦落刃)
    slope = df['MA240_Slope'].iloc[-1] if 'MA240_Slope' in df.columns else 1
    is_downtrend = slope < 0
    
    narrative = f"📌 【即時診斷】最新收盤價為 **{current_price:.2f}**，年線 (240MA) 為 **{ma240:.2f}**，目前乖離率為 **{bias:.2f}%**。"
    
    # 💡 確保這裡的 5 個 Key 與 capital_manager 完美對齊
    return {
        'Current_Price': current_price,
        'MA240': ma240,
        'Bias_%': bias,
        'Is_Downtrend': is_downtrend,
        'Narrative': narrative
    }