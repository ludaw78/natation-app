import streamlit as st
import pandas as pd
import requests
import re
import plotly.express as px
import numpy as np
import base64
from datetime import datetime

# ==========================================
# 1. CONFIGURATION & ICÔNE SVG
# ==========================================
LOG_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
    <rect width="100" height="100" rx="20" fill="#4CAF50"/>
    <path d="M30,55 q5,-5 10,0 t10,0 t10,0 t10,0" stroke="white" fill="none" stroke-width="4" stroke-linecap="round"/>
    <circle cx="50" cy="35" r="8" fill="white"/>
    <path d="M35,42 q15,-10 30,0" stroke="white" fill="none" stroke-width="5" stroke-linecap="round"/>
</svg>
"""
encoded_svg = base64.b64encode(LOG_SVG.encode()).decode()
icon_data = f"data:image/svg+xml;base64,{encoded_svg}"

st.set_page_config(
    page_title="Performances Tristan",
    page_icon=icon_data,
    layout="wide"
)

# Icône pour écran d'accueil mobile
st.markdown(f'<link rel="apple-touch-icon" href="{icon_data}">', unsafe_allow_html=True)

# =========================
# 2. NAVIGATION & ÉTAT
# =========================
if "page" not in st.session_state:
    st.session_state.page = "home"
if "bassin" not in st.session_state:
    st.session_state.bassin = "50m"
if "nage" not in st.session_state:
    st.session_state.nage = None

def update_bassin():
    st.session_state.bassin = st.session_state.bassin_radio

# =========================
# 3. CSS : DESIGN & FLUIDITÉ
# =========================
st.markdown("""
<style>
/* Boutons de nage stylisés */
div.stButton > button {
    width: auto !important;
    min-width: 90px !important;
    height: 45px !important;
    background-color: #4CAF50 !important;
    color: white !important;
    border-radius: 10px !important;
    border: none !important;
    font-weight: bold !important;
    padding: 0 15px !important;
}

/* Alignement horizontal fluide (Flexbox) - Pas de colonnes rigides */
[data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-flow: row wrap !important;
    justify-content: flex-start !important;
    gap: 10px !important;
}

[data-testid="column"] {
    width: auto !important;
    flex: 0 1 auto !important;
    min-width: 0px !important;
}

/* Radio boutons horizontaux propres */
.stRadio > div {
    flex-direction: row !important;
    gap: 15px;
}

.small-font { font-size:12px !important; color: gray; font-style: italic; text-align: center; }
</style>
""", unsafe_allow_html=True)

# =========================
# 4. CHARGEMENT DES DONNÉES
# =========================
@st.cache_data(ttl=600)
def load_all_data():
    idrch_id = "3518107"
    results = []
    sync_time = datetime.now().strftime("%d/%m/%Y à %H:%M")
    
    for b_code, b_label in [("25", "25m"), ("50", "50m")]:
        url = f"https://ffn.extranat.fr/webffn/nat_recherche.php?idact=nat&idrch_id={idrch_id}&idopt=prf&idbas={b_code}"
        try:
            response = requests.get(url, timeout=10)
            html = response.text
            pattern = re.compile(r'<tr[^>]*>.*?<th[^>]*>([^<]+)</th>.*?<td[^>]*font-bold[^>]*>(?:<button[^>]*>)?(?:<a[^>]*>)?\s*([\d:.]+)\s*(?:</a>)?(?:</button>)?</td>.*?<td[^>]*>\(([^)]+)\)</td>.*?<td[^>]*italic[^>]*>([^<]+)</td>.*?<p>([A-ZÀ-ÿ\s-]+)</p>\s*<p>\(([A-Z]+)\)</p>.*?<td[^>]*>(\d{2}/\d{2}/\d{4})</td>.*?<td[^>]*>(\[[^\]]+\])</td>.*?href="([^"]*resultats\.php[^"]*)".*?</td>\s*<td[^>]*>([^<]+)</td>', re.DOTALL)
            matches = pattern.findall(html)
            for m in matches:
                name = re.sub(r'[^a-zA-Z0-9\.\s]', '', m[0]).strip()
                results.append([name] + list(m[1:]) + [b_label])
        except: continue
    
    df = pd.DataFrame(results, columns=["Épreuve", "Temps", "Âge", "Points", "Ville", "Code pays", "Date", "Catégorie", "Lien résultats", "Club", "Bassin_Type"])
    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
        df["Temps_sec"] = df["Temps"].apply(lambda t: int(t.split(":")[0])*60 + float(t.split(":")[1]) if ":" in t else float(t))
    return df, sync_time

full_df, last_sync = load_all_data()

# =========================
# 5. PAGE ACCUEIL
# =========================
if st.session_state.page == "home":
    st.title("Performances Tristan 🏊‍♂️")
    
    st.radio("Bassin", ["25m", "50m"], 
             index=["25m","50m"].index(st.session_state.bassin), 
             horizontal=True, key="bassin_radio", on_change=update_bassin)

    df_current = full_df[full_df["Bassin_Type"] == st.session_state.bassin]

    if not df_current.empty:
        tab_list = ["Nage Libre", "Brasse", "Papillon", "Dos", "4 Nages"]
        tabs = st.tabs(tab_list)
        filters = {"Nage Libre": "NL", "Brasse": "BRA.", "Papillon": "PAP.", "Dos": "DOS", "4 Nages": "4 N."}
        
        all_names = df_current["Épreuve"].unique()

        for i, label in enumerate(tab_list):
            with tabs[i]:
                tag = filters[label]
                matches = [n for n in all_names if tag in n.upper()]
                # Tri numérique (50, 100, 200...)
                matches = sorted(matches, key=lambda x: int(''.join(c for c in x if c.isdigit())) if any(c.isdigit() for c in x) else 0)

                if matches:
                    cols = st.columns(len(matches))
                    for idx, epreuve in enumerate(matches):
                        with cols[idx]:
                            if st.button(epreuve, key=f"btn_{epreuve}_{st.session_state.
