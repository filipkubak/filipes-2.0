import os
import json
import datetime
import pandas as pd
import numpy as np
import yfinance as yf
import google.generativeai as genai

# --- CONFIGURATION ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "JNJ", "V",
    "XOM", "JPM", "WMT", "PG", "LLY", "MA", "AVGO", "HD", "CVX", "MRK",
    "GLD", "SLV", "USO", "UNG", "BTC-USD", "ETH-USD", "EURUSD=X", "GBPUSD=X"
]

def fetch_data_with_fallback(ticker):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df.empty or len(df) < 120:
            return None
        return df
    except:
        return None

def compute_indicators(df):
    """Čistý výpočet indikátorů bez externích knihoven"""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    close = df['Close']
    high = df['High']
    low = df['Low']
    
    # Ichimoku Cloud (Tenkan=20, Kijun=60, Senkou B=120)
    tenkan_sen = (high.rolling(window=20).max() + low.rolling(window=20).min()) / 2
    kijun_sen = (high.rolling(window=60).max() + low.rolling(window=60).min()) / 2
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(60)
    senkou_span_b = ((high.rolling(window=120).max() + low.rolling(window=120).min()) / 2).shift(60)
    
    # MACD (12, 26, 9)
    exp1 = close.ewm(span=12, adjust=False).mean()
    exp2 = close.ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    
    # RSI (14)
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / np.where(loss == 0, 1e-10, loss)
    rsi = 100 - (100 / (1 + rs))
    
    # ATR (14)
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    atr = true_range.rolling(14).mean()
    
    df['Tenkan'] = tenkan_sen
    df['Kijun'] = kijun_sen
    df['SpanA'] = senkou_span_a
    df['SpanB'] = senkou_span_b
    df['MACD'] = macd
    df['MACD_Signal'] = signal
    df['RSI'] = rsi
    df['ATR'] = atr
    
    return df

def validate_fundamentals(ticker):
    if "=" in ticker or "USD" in ticker or ticker in ["GLD", "SLV", "USO", "UNG"]:
        return True
    try:
        t = yf.Ticker(ticker)
        info = t.info
        if info.get("debtToEquity", 0) > 200: return False
        if info.get("revenueGrowth", 0) < -0.15: return False
        return True
    except:
        return True

def generate_ai_analysis(ticker, direction, price, rsi, score):
    prompt = f"Jsi seniorní analytik. Napiš stručné a kritické zhodnocení v češtině pro swingovou příležitost: Aktivum {ticker}, Směr {direction}, Cena {price}, RSI {rsi:.1f}, Skóre {score}/99. Napiš přesně 3 stručné věty bez zbytečných frází."
    try:
        if not GEMINI_API_KEY: raise ValueError()
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return f"Technická formace indikuje {direction} impuls. RSI je na hodnotě {rsi:.1f}. Sledujte hladiny risk managementu pro potvrzení trendu."

def run_pipeline():
    candidates = []
    
    for ticker in TICKERS:
        df = fetch_data_with_fallback(ticker)
        if df is None: continue
            
        df = compute_indicators(df)
        last_row = df.iloc[-1]
        
        if pd.isna(last_row['Tenkan']) or pd.isna(last_row['ATR']): continue
            
        current_price = float(last_row['Close'])
        atr = float(last_row['ATR'])
        rsi = float(last_row['RSI'])
        
        if current_price <= 0 or atr <= 0 or pd.isna(rsi): continue
        if not validate_fundamentals(ticker): continue
            
        direction = None
        if current_price > last_row['SpanA'] and current_price > last_row['SpanB'] and last_row['Tenkan'] > last_row['Kijun']:
            direction = "BUY"
        elif current_price < last_row['SpanA'] and current_price < last_row['SpanB'] and last_row['Tenkan'] < last_row['Kijun']:
            direction = "SELL"
            
        if not direction: continue
            
        base_score = 70
        if direction == "BUY" and rsi < 45: base_score += 15
        if direction == "SELL" and rsi > 55: base_score += 15
        if last_row['MACD'] > last_row['MACD_Signal'] and direction == "BUY": base_score += 14
        if last_row['MACD'] < last_row['MACD_Signal'] and direction == "SELL": base_score += 14
        score = min(int(base_score), 99)
        
        if direction == "BUY":
            sl = current_price - (2 * atr)
            tp = current_price + (3.5 * atr)
        else:
            sl = current_price + (2 * atr)
            tp = current_price - (3.5 * atr)
            
        if sl <= 0 or tp <= 0: continue
            
        candidates.append({
            "ticker": ticker,
            "direction": direction,
            "price": round(current_price, 4),
            "score": score,
            "probability": int(score * 0.85),
            "sl": round(sl, 4),
            "tp": round(tp, 4),
            "rsi": round(rsi, 2),
            "expiration": "48 hodin"
        })

    candidates = sorted(candidates, key=lambda x: x['score'], reverse=True)
    top_21 = candidates[:21]
    backup = candidates[21:]
    
    for c in top_21:
        c["reason"] = generate_ai_analysis(c["ticker"], c["direction"], c["price"], c["rsi"], c["score"])
    for b in backup:
        b["reason"] = "Aktivum v záložní frontě."

    output_data = {
        "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "top_21": top_21,
        "backup": backup
    }
    
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    run_pipeline()
