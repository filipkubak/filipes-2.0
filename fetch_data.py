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

def find_nearest_resistance(df, current_price):
    """Najde nejbližší logickou historickou rezistenci nad aktuální cenou (pro BUY)"""
    highs = df['High'].values
    resistances = []
    # Hledáme lokální maxima v okně 5 dní před a 5 dní po
    for i in range(5, len(highs) - 5):
        if highs[i] == max(highs[i-5:i+6]):
            if highs[i] > current_price:
                resistances.append(highs[i])
    
    if resistances:
        # Vrátíme tu, která je nejblíže nad aktuální cenou
        return min(resistances)
    return current_price * 1.05 # Nouzový fallback +5% pokud historie nemá jasný pivot

def find_nearest_support(df, current_price):
    """Najde nejbližší logický historický support pod aktuální cenou (pro SELL)"""
    lows = df['Low'].values
    supports = []
    # Hledáme lokální minima v okně 5 dní před a 5 dní po
    for i in range(5, len(lows) - 5):
        if lows[i] == min(lows[i-5:i+6]):
            if lows[i] < current_price:
                supports.append(lows[i])
                
    if supports:
        # Vrátíme ten, který je nejblíže pod aktuální cenou
        return max(supports)
    return current_price * 0.95 # Nouzový fallback -5%

def compute_indicators(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    close = df['Close']
    high = df['High']
    low = df['Low']
    
    # Ichimoku Cloud (20, 60, 120)
    tenkan_sen = (high.rolling(window=20).max() + low.rolling(window=20).min()) / 2
    kijun_sen = (high.rolling(window=60).max() + low.rolling(window=60).min()) / 2
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(60)
    senkou_span_b = ((high.rolling(window=120).max() + low.rolling(window=120).min()) / 2).shift(60)
    
    # MACD
    exp1 = close.ewm(span=12, adjust=False).mean()
    exp2 = close.ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    
    # RSI
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / np.where(loss == 0, 1e-10, loss)
    rsi = 100 - (100 / (1 + rs))
    
    # ATR
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
        if info.get("debtToEquity", 0) > 150: return False
        if info.get("revenueGrowth", 0) < -0.10: return False
        return True
    except:
        return True

def generate_ai_analysis(ticker, direction, price, rsi, score):
    prompt = f"Jsi špičkový hedge-fund manažer. Napiš chladné, kritické zhodnocení v češtině pro swing trade: {ticker}, Směr {direction}, Vstupní zóna {price}, RSI {rsi:.1f}, Skóre {score}/99. Zmiň, že Take Profit respektuje klíčovou historickou bariéru (support/rezistenci) na grafu. Napiš přesně 3 věty bez omáčky."
    try:
        if not GEMINI_API_KEY: raise ValueError()
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return f"Formace potvrzuje trend ve směru {direction}. Stop Loss je bezpečně ukotven pod strukturou Ichimoku Kijun-sen. Take Profit byl upraven podle nejbližší historické S/R zóny."

def run_pipeline():
    candidates = []
    
    for ticker in TICKERS:
        df = fetch_data_with_fallback(ticker)
        if df is None: continue
            
        df = compute_indicators(df)
        last_row = df.iloc[-1]
        
        if pd.isna(last_row['Tenkan']) or pd.isna(last_row['ATR']) or pd.isna(last_row['SpanB']): continue
            
        current_price = float(last_row['Close'])
        atr = float(last_row['ATR'])
        rsi = float(last_row['RSI'])
        
        tenkan = float(last_row['Tenkan'])
        kijun = float(last_row['Kijun'])
        span_a = float(last_row['SpanA'])
        span_b = float(last_row['SpanB'])
        
        if current_price <= 0 or atr <= 0 or pd.isna(rsi): continue
        if not validate_fundamentals(ticker): continue
            
        direction = None
        if current_price > span_a and current_price > span_b and tenkan > kijun:
            direction = "BUY"
        elif current_price < span_a and current_price < span_b and tenkan < kijun:
            direction = "SELL"
            
        if not direction: continue
        if direction == "BUY" and rsi > 65: continue
        if direction == "SELL" and rsi < 35: continue
            
        # --- RISK MANAGEMENT S REPEKTEM K S/R ÚROVNÍM ---
        if direction == "BUY":
            entry_price = tenkan if abs(current_price - tenkan) < (0.5 * atr) else current_price
            strong_support = min(kijun, span_b)
            sl = strong_support - (0.5 * atr)
            
            if (entry_price - sl) / entry_price > 0.10: continue
            
            # Nalezení historické rezistence
            nearest_res = find_nearest_resistance(df, entry_price)
            # TP umístíme kousek POD rezistenci (o 0.2x ATR) pro jistotu vybrání zisku
            tp = nearest_res - (0.2 * atr)
            
            # Kontrola reálného RRR: Pokud S/R zóna dává příliš malý prostor (RRR < 1.2), obchod vyřadíme
            risk = entry_price - sl
            reward = tp - entry_price
            if risk <= 0 or (reward / risk) < 1.2: continue
                
        else: # Šortová pozice (SELL)
            entry_price = tenkan if abs(current_price - tenkan) < (0.5 * atr) else current_price
            strong_resistance = max(kijun, span_b)
            sl = strong_resistance + (0.5 * atr)
            
            if (sl - entry_price) / entry_price > 0.10: continue
            
            # Nalezení historického supportu
            nearest_sup = find_nearest_support(df, entry_price)
            # TP umístíme kousek NAD support (o 0.2x ATR)
            tp = nearest_sup + (0.2 * atr)
            
            risk = sl - entry_price
            reward = entry_price - tp
            if risk <= 0 or (reward / risk) < 1.2: continue
            
        # Výpočet finálního skóre
        base_score = 75
        if last_row['MACD'] > last_row['MACD_Signal'] and direction == "BUY": base_score += 10
        if last_row['MACD'] < last_row['MACD_Signal'] and direction == "SELL": base_score += 10
        score = min(int(base_score), 99)
            
        candidates.append({
            "ticker": ticker,
            "direction": direction,
            "price": round(entry_price, 2),
            "score": score,
            "probability": int(score * 0.82),
            "sl": round(sl, 2),
            "tp": round(tp, 2),
            "rsi": round(rsi, 1),
            "expiration": "3 až 5 dní"
        })

    candidates = sorted(candidates, key=lambda x: x['score'], reverse=True)
    top_21 = candidates[:21]
    backup = candidates[21:]
    
    for c in top_21:
        c["reason"] = generate_ai_analysis(c["ticker"], c["direction"], c["price"], c["rsi"], c["score"])
    for b in backup:
        b["reason"] = "Čeká v záloze."

    output_data = {
        "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "top_21": top_21,
        "backup": backup
    }
    
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    run_pipeline()
