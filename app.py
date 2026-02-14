import streamlit as st
import pandas as pd
import requests
import re
import plotly.express as px
import numpy as np
import math
from datetime import datetime

st.set_page_config(page_title="Performances Tristan", layout="wide")

# =========================
# Navigation & État
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
# CSS : FORÇAGE DE LA GRILLE 3 COLONNES
# =========================
st.markdown("""
<style>
/* Style des boutons */
div.stButton > button {
    width: 100% !important;
    height: 45px !important;
    background-color: #4CAF50 !important;
    color: white !important;
    border-radius: 8px !important;
    font-weight: bold !important;
    margin-bottom: 5px !important;
    border: none !important;
}

/* LE FIX POUR MOBILE : On force le conteneur de colonnes à rester en ligne */
[data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important; /* Interdit le passage à la ligne à l'intérieur d'un bloc de 3 */
    gap: 5px !important;
}

[data-testid="column"] {
    width: 33% !important; /* Chaque bouton prend exactement un tiers */
    flex: 1 1 33% !important;
    min-width: 0px !important; /* Supprime la limite qui fait sauter les lignes sur mobile */
}

.small-font { font-size:11px !important; color: gray; font-style: italic; text-align: center; }
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
df_current = full_df[full_df["Bassin_Type"] == st.session_state.bassin]

# --- ACCUEIL ---
if st.session_state.page == "home":
    st.title("Performances Tristan 🏊‍♂️")
    st.radio("Bassin", ["25m", "50m"], index=["25m","50m"].index(st.session_state.bassin), horizontal=True, key="bassin_radio", on_change=update_bassin)

    if not df_current.empty:
        tab_labels = ["Nage Libre", "Brasse", "Papillon", "Dos", "4 Nages"]
        tabs = st.tabs(tab_labels)
        filters = {"Nage Libre": "NL", "Brasse": "BRA.", "Papillon": "PAP.", "Dos": "DOS", "4 Nages": "4 N."}
        
        all_names = df_current["Épreuve"].unique()

        for i, label in enumerate(tab_labels):
            with tabs[i]:
                tag = filters[label]
                matches = [n for n in all_names if tag in n.upper()]
                
                # TRI NUMÉRIQUE (50, 100, 200, 400, 800)
                matches = sorted(matches, key=lambda x: int(''.join(c for c in x if c.isdigit())) if any(c.isdigit() for c in x) else 0)

                if matches:
                    # On crée manuellement des lignes de 3 colonnes
                    for j in range(0, len(matches), 3):
                        row_matches = matches[j:j+3]
                        cols = st.columns(3)
                        for idx, epreuve in enumerate(row_matches):
                            with cols[idx]:
                                if st.button(epreuve, key=f"btn_{epreuve}_{st.session_state.bassin}"):
                                    st.session_state.nage = epreuve
                                    st.session_state.page = "perf"
                                    st.rerun()
    
    st.markdown("---")
    st.markdown(f'<p class="small-font">Dernière mise à jour FFN : {last_sync}</p>', unsafe_allow_html=True)

# --- PERFORMANCE ---
elif st.session_state.page == "perf":
    if st.button("⬅ Retour"):
        st.session_state.page = "home"
        st.rerun()

    nage_choisie = st.session_state.nage
    df_nage = df_current[df_current["Épreuve"] == nage_choisie].sort_values("Date", ascending=False)
    st.title(f"{nage_choisie}")

    if not df_nage.empty:
        st.dataframe(df_nage[["Date","Temps","Âge","Points","Ville","Catégorie"]], use_container_width=True)
        df_graph = df_nage.sort_values("Date")
        fig = px.scatter(df_graph, x="Date", y="Temps_sec", text="Temps", title="Progression")
        fig.update_traces(mode="lines+markers", marker=dict(color="#4CAF50"))
        st.plotly_chart(fig, use_container_width=True)
