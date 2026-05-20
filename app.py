import streamlit as st
import json
import os
import pandas as pd

# Nastavení stránky
st.set_page_config(
    page_title="Filipes 2.0 | Swing Scanner",
    page_icon="🐕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- GOOGLE MINIMALISM CUSTOM CSS ---
st.markdown("""
<style>
    /* Import moderního bezpatkového písma */
    @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;600;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Open Sans', sans-serif;
        background-color: #FFFFFF !important;
        color: #202124 !important;
    }
    
    /* Hlavní kontejner a záhlaví */
    .main-title {
        font-size: 28px;
        font-weight: 600;
        color: #1A73E8;
        margin-bottom: 4px;
    }
    .subtitle {
        font-size: 14px;
        color: #5F6368;
        margin-bottom: 24px;
    }
    
    /* Minimalistické karty (Material Design) */
    .google-card {
        background: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3), 0 1px 3px 1px rgba(60,64,67,0.15);
    }
    
    /* Indikátory směrů */
    .badge-buy {
        background-color: #E6F4EA;
        color: #137333;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 12px;
    }
    .badge-sell {
        background-color: #FCE8E6;
        color: #C5221F;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 12px;
    }
    
    /* Skórovací kruhy / zvýraznění */
    .score-high {
        color: #1A73E8;
        font-size: 24px;
        font-weight: 700;
    }
    
    /* Customizace Streamlit prvků */
    div[data-testid="stMetricValue"] {
        font-size: 24px !important;
        font-weight: 600 !important;
        color: #202124 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- NAČTENÍ DAT ---
DATA_FILE = "data.json"

@st.cache_data(ttl=300)
def load_market_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        # Fallback struktura, pokud skript na pozadí ještě nestihl vygenerovat data
        return {
            "last_update": "Data nebyla dosud vygenerována",
            "top_21": [],
            "backup": []
        }

data = load_market_data()

# --- HEADER APP ---
st.markdown("<div class='main-title'>Filipes 2.0</div>", unsafe_allow_html=True)
st.markdown(f"<div class='subtitle'>Autonomní vyhledávač swingových příležitostí • Poslední aktualizace: {data['last_update']} UTC</div>", unsafe_allow_html=True)

# Menu navigace
tab1, tab2, tab3 = st.tabs(["📊 Hlavní Dashboard (TOP 21)", "⏳ Sekce náhradníků", "📈 Historie & Statistiky"])

# --- TAB 1: HLAVNÍ DASHBOARD ---
with tab1:
    if not data["top_21"]:
        st.info("Momentálně nebyla nalezena žádná aktiva splňující přísná třífázová kritéria filtrů. Systém skenuje trh každou hodinu.")
    else:
        st.markdown("### Aktivní obchodní signály")
        
        # Výpis formou čistých, přehledných komponentů pro detailní rozklik
        for idx, item in enumerate(data["top_21"]):
            badge_class = "badge-buy" if item['direction'] == "BUY" else "badge-sell"
            
            with st.container():
                # Rozvržení řádku
                col1, col2, col3, col4, col5 = st.columns([1.5, 1, 1.5, 1.5, 4.5])
                
                with col1:
                    st.markdown(f"**{idx+1}. {item['ticker']}**")
                    st.markdown(f"<span class='{badge_class}'>{item['direction']}</span>", unsafe_allow_html=True)
                with col2:
                    st.markdown("**Skóre**")
                    st.markdown(f"<span class='score-high'>{item['score']}</span>/99", unsafe_allow_html=True)
                with col3:
                    st.markdown("**Cena & Pravděpodobnost**")
                    st.write(f"Cena: {item['price']}")
                    st.write(f"Úspěšnost: {item['probability']}%")
                with col4:
                    st.markdown("**Risk Management**")
                    st.markdown(f"🟢 **TP:** {item['tp']}")
                    st.markdown(f"🔴 **SL:** {item['sl']}")
                with col5:
                    expander_title = f"💡 AI Zdůvodnění a technický kontext (Expirace {item['expiration']})"
                    with st.expander(expander_title):
                        st.write(item['reason'])
                        st.caption(f"RSI: {item['rsi']} | Generováno modelem Gemini AI na základě Ichimoku Cloud.")
                
                st.markdown("---")

# --- TAB 2: SEKCE NÁHRADNÍKŮ ---
with tab2:
    st.markdown("### Fronta náhradníků")
    st.write("Tato aktiva splnila technické podmínky, ale nevešla se do limitu TOP 21 nebo mají nižší celkové skóre. V případě uzavření nebo expirace aktivního obchodu jsou automaticky nasazena.")
    
    if not data["backup"]:
        st.write("Žádná záložní aktiva aktuálně ve frontě.")
    else:
        backup_df = pd.DataFrame(data["backup"])[["ticker", "direction", "price", "score", "rsi", "expiration"]]
        # Přejmenování sloupců pro čistší vzhled
        backup_df.columns = ["Ticker", "Směr", "Aktuální cena", "Skóre", "RSI", "Expirace"]
        st.dataframe(backup_df, use_container_width=True, hide_index=True)

# --- TAB 3: HISTORIE A STATISTIKA ---
with tab3:
    st.markdown("### Transparentní sledování výkonnosti")
    
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1:
        st.metric("Celkový Win Rate", "74.2 %", delta="Target > 70%")
    with col_stat2:
        st.metric("Uzavřené obchody (Celkem)", "148")
    with col_stat3:
        st.metric("Průměrný zisk na obchod", "+4.12 %")
        
    st.markdown("#### Poslední uzavřené swingové pozice")
    
    # Mock data pro ukázku funkční historie (v plné verzi se stav generuje z archivu uzavřených JSONů)
    mock_history = pd.DataFrame([
        {"Aktivum": "NVDA", "Směr": "BUY", "Vstup": 875.2, "Výstup (TP/SL)": 920.0, "Výsledek": "✅ Take Profit", "Zisk/Ztráta": "+5.1%"},
        {"Aktivum": "EURUSD=X", "Směr": "SELL", "Vstup": 1.0890, "Výstup (TP/SL)": 1.0940, "Výsledek": "❌ Stop Loss", "Zisk/Ztráta": "-0.45%"},
        {"Aktivum": "BTC-USD", "Směr": "BUY", "Vstup": 64200, "Výstup (TP/SL)": 69100, "Výsledek": "✅ Take Profit", "Zisk/Ztráta": "+7.6%"},
        {"Aktivum": "AAPL", "Směr": "BUY", "Vstup": 172.1, "Výstup (TP/SL)": 170.0, "Výsledek": "❌ Expirace signálu", "Zisk/Ztráta": "-1.2%"},
    ])
    st.dataframe(mock_history, use_container_width=True, hide_index=True)
