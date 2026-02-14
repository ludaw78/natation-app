import streamlit as st
import pandas as pd
import requests
import re
import plotly.express as px
import numpy as np
import base64
from datetime import datetime

# ==========================================
# 1. CONFIGURATION & ICÔNE
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

st.set_page_config(page_title="Tristan Swim", page_icon=icon_data, layout="wide")

# Forçage icône mobile
st.markdown(f'<link rel="apple-touch-icon" href="{icon_data}">', unsafe_allow_html=True)

# =========================
# 2. NAVIGATION
# =========================
if "page" not in st.session_state: st.session_state.page = "home"
if "bassin" not in st.session_state: st.session_state.bassin = "50m"
if "nage" not in st.session_state: st.session_state.nage = None

def update_bassin():
    st.session_state.bassin = st.session_state.bassin_radio

# =========================
# 3. CSS
# =========================
st.markdown("""
<style>
div.stButton > button { width: auto !important; min-width: 90px !important; height: 45px !important; background-color: #4CAF50 !important; color: white !important; border-radius: 10px !important; font-weight: bold !important; }
[data-testid="stHorizontalBlock"] { display: flex !important; flex-flow: row wrap !important; gap: 10px !important; }
[data-testid="column"] { width: auto !important; flex: 0 1 auto !important; }
.stRadio > div { flex-direction: row !important; gap: 15px; }
</style>
""", unsafe_allow_html=True)

# =========================
# 4. DATA
# =========================
@st.cache_data(ttl=600)
def load_data():
    idrch_id = "3518107"
    results = []
    for b_code, b_label in [("25", "25m"), ("50", "50m")]:
        url = f"https://ffn.extranat.fr/webffn/nat_recherche.php?idact=nat&idrch_id={idrch_id}&idopt=prf&idbas={b_code}"
        try:
            r = requests.get(url, timeout=10)
            matches = re.findall(r'<tr[^>]*>.*?<th[^>]*>([^<]+)</th>.*?<td[^>]*font-bold[^>]*>(?:<button[^>]*>)?(?:<a[^>]*>)?\s*([\d:.]+)\s*(?:</a>)?(?:</button>)?</td>.*?<td[^>]*>\(([^)]+)\)</td>.*?<td[^>]*italic[^>]*>([^<]+)</td>.*?<p>([A-ZÀ-ÿ\s-]+)</p>\s*<p>\(([A-Z]+)\)</p>.*?<td[^>]*>(\d{2}/\d{2}/\d{4})</td>.*?<td[^>]*>(\[[^\]]+\])</td>.*?href="([^"]*resultats\.php[^"]*)".*?</td>\s*<td[^>]*>([^<]+)</td>', r.text, re.DOTALL)
            for m in matches:
                name = re.sub(r'[^a-zA-Z0-9\.\s]', '', m[0]).strip()
                results.append([name, m[1], m[2], m[3], m[4], m[6], b_label])
        except: continue
    df = pd.DataFrame(results, columns=["Épreuve", "Temps", "Âge", "Points", "Ville", "Date", "Bassin"])
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
    df["Temps_sec"] = df["Temps"].apply(lambda t: int(t.split(":")[0])*60 + float(t.split(":")[1]) if ":" in t else float(t))
    return df

full_df = load_data()

# =========================
# 5. PAGES
# =========================

if st.session_state.page == "home":
    st.title("Performances Tristan 🏊‍♂️")
    st.radio("Bassin", ["25m", "50m"], index=["25m","50m"].index(st.session_state.bassin), horizontal=True, key="bassin_radio", on_change=update_bassin)
    
    df_c = full_df[full_df["Bassin"] == st.session_state.bassin]
    tabs = st.tabs(["Nage Libre", "Brasse", "Papillon", "Dos", "4 Nages"])
    filters = {"Nage Libre": "NL", "Brasse": "BRA.", "Papillon": "PAP.", "Dos": "DOS", "4 Nages": "4 N."}
    
    for i, (label, tag) in enumerate(filters.items()):
        with tabs[i]:
            matches = sorted(df_c[df_c["Épreuve"].str.contains(tag, case=False)]["Épreuve"].unique(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
            if matches:
                cols = st.columns(len(matches))
                for idx, n in enumerate(matches):
                    if cols[idx].button(n):
                        st.session_state.nage = n
                        st.session_state.page = "perf"
                        st.rerun()

else:
    if st.button("⬅ Retour"):
        st.session_state.page = "home"
        st.rerun()
    
    st.title(st.session_state.nage)
    st.radio("Bassin :", ["25m", "50m"], index=["25m","50m"].index(st.session_state.bassin), horizontal=True, key="bassin_radio", on_change=update_bassin)
    
    df_n = full_df[(full_df["Épreuve"] == st.session_state.nage) & (full_df["Bassin"] == st.session_state.bassin)].sort_values("Date", ascending=False)
    
    if not df_n.empty:
        # TABLEAU SANS INDEX ET AVEC RP EN COULEUR
        def highlight_max(s):
            is_best = s == df_n["Temps_sec"].min()
            return ['background-color: #ffe4e1' if v else '' for v in is_best]

        display_df = df_n[["Date", "Temps", "Âge", "Points", "Ville"]].copy()
        display_df["Date"] = display_df["Date"].dt.strftime('%d/%m/%Y')
        
        # On affiche le dataframe sans la colonne d'index
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # GRAPHIQUE
        df_g = df_n.sort_values("Date")
        # On crée une colonne de texte pour le format min'sec''
        df_g["Temps_label"] = df_g["Temps_sec"].apply(lambda x: f"{int(x//60)}'{int(x%60):02}''{int((x*100)%100):02}")
        
        fig = px.line(df_g, x="Date", y="Temps_sec", markers=True, title="Évolution")
        fig.update_traces(
            line_color='#4CAF50', 
            marker=dict(size=10),
            text=df_g["Temps_label"],
            hovertemplate="Date: %{x}<br>Temps: %{text}<extra></extra>"
        )
        
        # Correction axe Y pour afficher min'sec
        min_y = df_g["Temps_sec"].min() * 0.98
        max_y = df_g["Temps_sec"].max() * 1.02
        
        fig.update_layout(
            yaxis=dict(
                tickmode='array',
                tickvals=np.linspace(df_g["Temps_sec"].min(), df_g["Temps_sec"].max(), 5),
                ticktext=[f"{int(v//60)}'{int(v%60):02}''" for v in np.linspace(df_g["Temps_sec"].min(), df_g["Temps_sec"].max(), 5)]
            ),
            xaxis_title=None,
            yaxis_title="Temps (min'sec'')"
        )
        st.plotly_chart(fig, use_container_width=True)
