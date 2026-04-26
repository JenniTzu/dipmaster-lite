# 檔案位置： src/analyzer.py
import pandas as pd

def analyze_stock(df):
    """軍師模組：負責技術面數據的計算與診斷"""
    if df is None or df.empty:
        return {
            'Current_Price': 0, 'MA240': 0, 'Bias_%': 0,
            'Is_Downtrend': False, 'Slope': 0.0,
            'MA240_Reliable': True, 'Narrative': "無效數據"
        }

    current_price = df['Close'].iloc[-1]

    if 'MA240' in df.columns and not pd.isna(df['MA240'].iloc[-1]):
        ma240 = df['MA240'].iloc[-1]
    else:
        ma240 = current_price

    ma240_reliable = bool(df['MA240_Reliable'].iloc[-1]) if 'MA240_Reliable' in df.columns else True
    bias = ((current_price - ma240) / ma240) * 100 if ma240 else 0

    slope_raw = df['MA240_Slope'].iloc[-1] if 'MA240_Slope' in df.columns else 1.0
    slope = float(slope_raw) if not pd.isna(slope_raw) else 0.0
    is_downtrend = slope < 0

    if bias >= 0:
        gap_price = abs(current_price - ma240)
        narrative_zone = (
            f"目前在年線之上（正乖離 **+{bias:.2f}%**），尚未進入安全邊際區。"
            f"需再跌約 **{gap_price:.2f}**（{bias:.1f}%）才抵達年線，以下梯子計畫僅供預演。"
        )
    else:
        narrative_zone = (
            f"目前在年線之下（負乖離 **{bias:.2f}%**），已進入加碼觀察區，可依梯子計畫考慮分批執行。"
        )

    narrative = (
        f"📌 【即時診斷】收盤價 **{current_price:.2f}**，年線 MA240 **{ma240:.2f}**，"
        f"乖離率 **{bias:.2f}%**。{narrative_zone}"
    )

    return {
        'Current_Price': current_price,
        'MA240': ma240,
        'Bias_%': bias,
        'Is_Downtrend': is_downtrend,
        'Slope': slope,
        'MA240_Reliable': ma240_reliable,
        'Narrative': narrative
    }
