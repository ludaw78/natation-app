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
# Session state navigation
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
# CSS (BOUTONS VERTS)
# =========================
st.markdown("""
<style>
div.stButton > button {
    width: 100% !important;
    height: 50px !important;
    background-color: #4CAF50 !important;
    color: white !important;
    border-radius: 10px !important;
    border: none !important;
    font-weight: bold !important;
}
div.stButton > button p { color: white !important; }
.small-font {
    font-size:12px !important;
    color: gray;
    font-style: italic;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# =========================
# Scraping Global (Cache 1h)
# =========================
@st.cache_data(ttl=3600)
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
                results.append(list(m) + [b_label])
        except: continue

    if not results: return pd.DataFrame(), sync_time
    
    colonnes = ["Épreuve", "Temps", "Âge", "Points", "Ville", "Code pays", "Date", "Catégorie", "Lien résultats", "Club", "Bassin_Type"]
    df = pd.DataFrame(results, columns=colonnes)
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
    df["Temps_sec"] = df["Temps"].apply(lambda t: int(t.split(":")[0])*60 + float(t.split(":")[1]) if ":" in t else float(t))
    
    return df, sync_time

full_df, last_sync = load_all_data()
df_current = full_df[full_df["Bassin_Type"] == st.session_state.bassin]

# --- PAGE ACCUEIL ---
if st.session_state.page == "home":
    st.title("Performances Tristan 🏊‍♂️")
    st.radio("Bassin", ["25m", "50m"], index=["25m","50m"].index(st.session_state.bassin), horizontal=True, key="bassin_radio", on_change=update_bassin)

    if df_current.empty:
        st.warning("Aucune donnée disponible.")
    else:
        tab_list = ["Nage Libre", "Brasse", "Papillon", "Dos", "4 Nages"]
        tabs = st.tabs(tab_list)
        
        filters = {
            "Nage Libre": ["NL"],
            "Brasse": ["BRA."],
            "Papillon": ["PAP."],
            "Dos": ["DOS"],
            "4 Nages": ["4 N."]
        }
        
        all_epreuves = df_current["Épreuve"].unique().tolist()
        
        # Fonction de tri robuste : extrait TOUS les chiffres et les transforme en nombre
        def extract_dist_robust(text):
            digits = "".join(filter(str.isdigit, text))
            return int(digits) if digits else 9999

        for i, label in enumerate(tab_list):
            with tabs[i]:
                # Filtrage strict
                cat_matches = [e for e in all_epreuves if any(f.upper() in e.upper() for f in filters[label])]
                # Tri forcé par la valeur numérique de la distance
                cat_matches = sorted(cat_matches, key=extract_dist_robust)
                
                if not cat_matches:
                    st.info("Aucune épreuve trouvée.")
                else:
                    cols = st.columns(3)
                    for j, epreuve in enumerate(cat_matches):
                        cols[j % 3].button(epreuve, key=f"btn_{epreuve}", on_click=lambda e=epreuve: st.session_state.update({"nage": e, "page": "perf"}), use_container_width=True)

    st.markdown("---")
    st.markdown(f'<p class="small-font">Dernière mise à jour FFN : {last_sync}</p>', unsafe_allow_html=True)

# --- PAGE PERFORMANCE ---
elif st.session_state.page == "perf":
    if st.button("⬅ Retour"):
        st.session_state.page = "home"
        st.rerun()

    st.radio("Bassin", ["25m", "50m"], index=["25m","50m"].index(st.session_state.bassin), horizontal=True, key="bassin_radio", on_change=update_bassin)
    
    nage_choisie = st.session_state.nage
    df_nage = df_current[df_current["Épreuve"] == nage_choisie].sort_values("Date", ascending=False)
    st.title(f"{nage_choisie} ({st.session_state.bassin})")

    if not df_nage.empty:
        table_df = df_nage[["Date","Temps","Âge","Points","Ville","Catégorie"]].copy()
        table_df["Date"] = table_df["Date"].dt.date
        best_idx = df_nage["Temps_sec"].idxmin()
        st.dataframe(table_df.style.apply(lambda r: ["background-color: #ffe4e1" if r.name==best_idx else "" for _ in r], axis=1), use_container_width=True)

        df_graph = df_nage.sort_values("Date")
        t_min, t_max = math.floor(df_graph["Temps_sec"].min()) - 1, math.ceil(df_graph["Temps_sec"].max()) + 1
        y_ticks = np.linspace(t_min, t_max, 7)
        def sec_to_mmss(s):
            m, sec = int(s // 60), int(s % 60)
            return f"{m:02d}:{sec:02d}" if m > 0 else f"{sec:02d}"

        fig = px.scatter(df_graph, x="Date", y="Temps_sec", text="Temps", title="Progression")
        fig.update_traces(mode="lines+markers", marker=dict(size=10, color="#4CAF50"), line=dict(color="#4CAF50"))
        fig.update_layout(yaxis=dict(title="Temps", tickvals=y_ticks, ticktext=[sec_to_mmss(y) for y in y_ticks], showgrid=True), xaxis=dict(title="Date"), margin=dict(l=60,r=20,t=60,b=60))
        st.plotly_chart(fig, use_container_width=True)
