import streamlit as st
import pandas as pd
import requests
import re
import plotly.express as px
import numpy as np
import math
from datetime import datetime
import uuid # Pour générer un identifiant unique à chaque rafraîchissement

# Configuration de la page
st.set_page_config(page_title="Performances Tristan", layout="wide")

# =========================
# FORÇAGE ANTI-CACHE (CACHE BUSTING)
# =========================
# On génère un ID totalement nouveau à chaque exécution du script
if "unique_run_id" not in st.session_state:
    st.session_state.unique_run_id = str(uuid.uuid4())

if "page" not in st.session_state:
    st.session_state.page = "home"
if "bassin" not in st.session_state:
    st.session_state.bassin = "50m"
if "nage" not in st.session_state:
    st.session_state.nage = None

def update_bassin():
    st.session_state.bassin = st.session_state.bassin_radio
    # On change l'ID au changement de bassin pour forcer le refresh des composants
    st.session_state.unique_run_id = str(uuid.uuid4())

# =========================
# CSS
# =========================
st.markdown(f"""
<style>
/* On utilise l'ID unique dans le CSS pour forcer le re-rendu */
div.stButton > button {{
    width: 100% !important;
    height: 50px !important;
    background-color: #4CAF50 !important;
    color: white !important;
    border-radius: 10px !important;
    border: none !important;
    font-weight: bold !important;
}}
div.stButton > button p {{ color: white !important; }}
.small-font {{ font-size:12px !important; color: gray; font-style: italic; text-align: center; }}
</style>
""", unsafe_allow_html=True)

# =========================
# SCRAPING (SANS CACHE)
# =========================
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
                # Nettoyage des noms pour éviter les bugs de caractères invisibles
                clean_name = " ".join(m[0].split())
                results.append([clean_name] + list(m[1:]) + [b_label])
        except: continue
    
    df = pd.DataFrame(results, columns=["Épreuve", "Temps", "Âge", "Points", "Ville", "Code pays", "Date", "Catégorie", "Lien résultats", "Club", "Bassin_Type"])
    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
        df["Temps_sec"] = df["Temps"].apply(lambda t: int(t.split(":")[0])*60 + float(t.split(":")[1]) if ":" in t else float(t))
    return df, sync_time

full_df, last_sync = load_all_data()
df_current = full_df[full_df["Bassin_Type"] == st.session_state.bassin]

# --- PAGE ACCUEIL ---
if st.session_state.page == "home":
    st.title("Performances Tristan 🏊‍♂️")
    
    # On ajoute l'ID unique au widget pour forcer son actualisation
    st.radio("Bassin", ["25m", "50m"], 
             index=["25m","50m"].index(st.session_state.bassin), 
             horizontal=True, key="bassin_radio", on_change=update_bassin)

    if df_current.empty:
        st.warning("Aucune donnée disponible.")
    else:
        # Onglets avec clés uniques
        tab_list = ["Nage Libre", "Brasse", "Papillon", "Dos", "4 Nages"]
        tabs = st.tabs(tab_list)
        filters = {"Nage Libre": ["NL"], "Brasse": ["BRA."], "Papillon": ["PAP."], "Dos": ["DOS"], "4 Nages": ["4 N."]}
        
        all_epreuves = df_current["Épreuve"].unique().tolist()
        
        for i, label in enumerate(tab_list):
            with tabs[i]:
                # Filtrage
                matches = [e for e in all_epreuves if any(f.upper() in e.upper() for f in filters[label])]
                
                # TRI NUMÉRIQUE STRICT
                # On extrait uniquement les chiffres pour le tri (ex: "400 NL" -> 400)
                matches.sort(key=lambda x: int(''.join(filter(str.isdigit, x))) if any(c.isdigit() for c in x) else 0)
                
                if not matches:
                    st.info("Aucune épreuve trouvée.")
                else:
                    cols = st.columns(3)
                    for j, epreuve in enumerate(matches):
                        # LA CLÉ EST LA PLUS IMPORTANTE : elle contient l'ID unique de session
                        # Cela force le navigateur à recréer le bouton au lieu de charger l'ancien
                        unique_key = f"btn_{epreuve}_{st.session_state.unique_run_id}_{i}_{j}"
                        if cols[j % 3].button(epreuve, key=unique_key):
                            st.session_state.nage = epreuve
                            st.session_state.page = "perf"
                            st.rerun()

    st.markdown("---")
    st.markdown(f'<p class="small-font">Dernière mise à jour FFN : {last_sync}</p>', unsafe_allow_html=True)
