import streamlit as st
import pandas as pd
import requests
import re
import plotly.express as px
import numpy as np
from datetime import datetime

# Configuration de la page
st.set_page_config(page_title="Performances Tristan", layout="wide")

# ==========================================
# GESTION DE LA NAVIGATION (Bouton Retour)
# ==========================================

# Récupération des paramètres dans l'URL
query_params = st.query_params

# Si "nage" est dans l'URL, on affiche la page perf, sinon accueil
if "nage" in query_params:
    st.session_state.page = "perf"
    st.session_state.nage = query_params["nage"]
else:
    st.session_state.page = "home"

# Fonction pour aller à la page performance
def go_to_perf(nage_name):
    st.query_params["nage"] = nage_name  # Met à jour l'URL
    st.session_state.page = "perf"
    st.session_state.nage = nage_name

# Fonction pour revenir à l'accueil
def go_to_home():
    st.query_params.clear() # Vide l'URL
    st.session_state.page = "home"

# =========================
# État du Bassin
# =========================
if "bassin" not in st.session_state:
    st.session_state.bassin = "50m"

def update_bassin():
    st.session_state.bassin = st.session_state.bassin_radio

# =========================
# CSS : DESIGN ET FLEXBOX
# =========================
st.markdown("""
<style>
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
/* Aligne les boutons de gauche à droite et passe à la ligne */
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
.small-font { font-size:12px !important; color: gray; font-style: italic; text-align: center; }
</style>
""", unsafe_allow_html=True)

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

# --- PAGE ACCUEIL ---
if st.session_state.page == "home":
    st.title("Performances Tristan 🏊‍♂️")
    st.radio("Bassin", ["25m", "50m"], index=["25m","50m"].index(st.session_state.bassin), 
             horizontal=True, key="bassin_radio", on_change=update_bassin)

    df_current = full_df[full_df["Bassin_Type"] == st.session_state.bassin]
    if not df_current.empty:
        tabs = st.tabs(["Nage Libre", "Brasse", "Papillon", "Dos", "4 Nages"])
        filters = {"Nage Libre": "NL", "Brasse": "BRA.", "Papillon": "PAP.", "Dos": "DOS", "4 Nages": "4 N."}
        all_names = df_current["Épreuve"].unique()

        for i, (label, tag) in enumerate(filters.items()):
            with tabs[i]:
                # Tri numérique (50, 100, 200...)
                matches = sorted([n for n in all_names if tag in n.upper()], 
                                 key=lambda x: int(''.join(c for c in x if c.isdigit())) if any(c.isdigit() for c in x) else 0)
                if matches:
                    cols = st.columns(len(matches))
                    for idx, epreuve in enumerate(matches):
                        with cols[idx]:
                            # Utilisation de la fonction qui change l'URL
                            if st.button(epreuve, key=f"btn_{epreuve}"):
                                go_to_perf(epreuve)
                                st.rerun()
    st.markdown("---")
    st.markdown(f'<p class="small-font">Dernière mise à jour FFN : {last_sync}</p>', unsafe_allow_html=True)

# --- PAGE PERFORMANCE ---
elif st.session_state.page == "perf":
    col_back, col_bassin = st.columns([1, 2])
    with col_back:
        if st.button("⬅ Retour"):
            go_to_home()
            st.rerun()
    with col_bassin:
        st.radio("Bassin", ["25m", "50m"], index=["25m","50m"].index(st.session_state.bassin), 
                 horizontal=True, key="bassin_radio", on_change=update_bassin)

    df_nage = full_df[(full_df["Épreuve"] == st.session_state.nage) & (full_df["Bassin_Type"] == st.session_state.bassin)].sort_values("Date", ascending=False)
    st.title(f"{st.session_state.nage} - {st.session_state.bassin}")

    if not df_nage.empty:
        # Mise en valeur de la meilleure performance (RP)
        best_idx = df_nage["Temps_sec"].idxmin()
        table_df = df_nage[["Date","Temps","Âge","Points","Ville","Catégorie"]].copy()
        table_df["Date"] = table_df["Date"].dt.date
        st.dataframe(table_df.style.apply(lambda row: ['background-color: #ffe4e1' if row.name == best_idx else '' for _ in row], axis=1), use_container_width=True)
        
        # Graphique de progression
        df_graph = df_nage.sort_values("Date")
        fig = px.scatter(df_graph, x="Date", y="Temps_sec", text="Temps", title="Progression")
        fig.update_traces(mode="lines+markers", marker=dict(size=10, color="#4CAF50"), line=dict(color="#4CAF50"))
        st.plotly_chart(fig, use_container_width=True)
