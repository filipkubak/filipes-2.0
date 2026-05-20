import streamlit as str
import json
import os
import streamlit.components.v1 as components

# Nastavení čistého Google designu stránky
str.set_page_config(
    page_title="Filipes 2.0 • Vyhledávač",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- JAVASCRIPT PRO NOTIFIKACE V PROHLÍŽEČI ---
def inject_notification_js(new_tickers):
    # Převod seznamu tickerů do formátu pro JavaScript
    tickers_json = json.dumps(new_tickers)
    
    js_code = f"""
    <script>
    // Funkce pro vyžádání povolení k notifikacím
    if (Notification.permission !== "granted" && Notification.permission !== "denied") {{
        Notification.requestPermission();
    }}

    // Kontrola nových tickerů uložených v paměti prohlížeče
    const currentTickers = {tickers_json};
    const lastSeenRaw = localStorage.getItem("filipes_last_tickers");
    const lastSeen = lastSeenRaw ? JSON.parse(lastSeenRaw) : [];

    // Najdeme tickery, které jsou nové
    const freshTickers = currentTickers.filter(x => !lastSeen.includes(x));

    if (freshTickers.length > 0 && Notification.permission === "granted") {{
        freshTickers.forEach(ticker => {{
            new Notification("🎯 FILIPES 2.0: Nová příležitost", {{
                body: "Na trhu se objevil aktivní swing signál pro " + ticker + ". Zkontrolujte tabulku!",
                icon: "https://streamlit.io/images/brand/streamlit-mark-color.png"
            }});
        }});
    }}

    // Aktualizujeme paměť prohlížeče
    localStorage.setItem("filipes_last_tickers", JSON.stringify(currentTickers));
    </script>
    """
    # Skryté vložení komponenty do stránky
    components.html(js_code, height=0, width=0)


# --- NAČTENÍ DAT ---
DATA_FILE = "data.json"

str.markdown("""
    <style>
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    h1 { font-family: 'Roboto', 'Segoe UI', sans-serif; font-weight: 400; color: #1a73e8; }
    .stAlert { border-radius: 8px; }
    div[data-testid="stDataFrame"] { border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }
    </style>
""", unsafe-allowed_html=True)

str.title("📈 Filipes 2.0")
str.caption("Autonomní swingový skener trhu na bázi Ichimoku Cloud & S/R zón")

if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        last_update = data.get("last_update", "Neznámo")
        top_21 = data.get("top_21", [])
        
        str.info(f"🔄 Poslední aktualizace trhu: **{last_update}** (Skenování probíhá automaticky každou hodinu)")
        
        if top_21:
            # Extrahujeme tickery pro notifikační skript
            current_tickers = [x["ticker"] for x in top_21]
            inject_notification_js(current_tickers)
            
            # Příprava čisté tabulky pro zobrazení
            display_data = []
            for idx, item in enumerate(top_21, 1):
                display_data.append({
                    "Pořadí": f"#{idx}",
                    "Ticker": item["ticker"],
                    "Směr": "🟢 BUY" if item["direction"] == "BUY" else "🔴 SELL",
                    "Vstupní zóna": f"{item['price']} USD",
                    "Stop Loss (SL)": f"{item['sl']} USD",
                    "Take Profit (TP)": f"{item['tp']} USD",
                    "RSI": item["rsi"],
                    "Expirace": item["expiration"],
                    "Skóre": f"{item['score']}/99",
                    "Analýza trhu (AI Kontext)": item["reason"]
                })
            
            # Zobrazení interaktivní tabulky v Google stylu
            str.dataframe(
                display_data,
                use_container_width=True,
                hide_index=True
            )
        else:
            # Spustíme skript s prázdným polem, aby se vyčistila cache prohlížeče
            inject_notification_js([])
            str.warning("⏳ *Momentálně nebyla nalezena žádná aktiva splňující přísná třífázová kritéria filtrů.*")
            str.write("Robot nenašel optimální poměr risku a zisku u žádného sledovaného titulu. Vyčkejte na další hodinnový sken.")
            
    except Exception as e:
        str.error("Chyba při zpracování datového souboru.")
else:
    str.error("Datový soubor data.json zatím nebyl vytvořen. Spusťte nejdříve workflow na GitHubu.")
