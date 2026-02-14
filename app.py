import streamlit as st
import pandas as pd
import requests
import re
import plotly.express as px
import numpy as np
import math

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

# Callback pour le bassin
def update_bassin():
    st.session_state.bassin = st.session_state.bassin_radio

# =========================
# CSS (VERSION BOUTONS VERTS ROBUSTE)
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
div.stButton > button p {
    color: white !important;
}
div.row-widget.stRadio > label {
    font-size: 16px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# =========================
# Fonction Scraping Global (Cache 1h)
# =========================
@st.cache_data(ttl=3600)
def load_all_data():
    idrch_id = "3518107"
    results = []
    
    for b_code, b_label in [("25", "25m"), ("50", "50m")]:
        url = f"https://ffn.extranat.fr/webffn/nat_recherche.php?idact=nat&idrch_id={idrch_id}&idopt=prf&idbas={b_code}"
        try:
            response = requests.get(url, timeout=10)
            html = response.text
            
            pattern = re.compile(
                r'<tr[^>]*>.*?'
                r'<th[^>]*>([^<]+)</th>.*?'
                r'<td[^>]*font-bold[^>]*>(?:<button[^>]*>)?(?:<a[^>]*>)?\s*([\d:.]+)\s*(?:</a>)?(?:</button>)?</td>.*?'
                r'<td[^>]*>\(([^)]+)\)</td>.*?'
                r'<td[^>]*italic[^>]*>([^<]+)</td>.*?'
                r'<p>([A-ZÀ-ÿ\s-]+)</p>\s*<p>\(([A-Z]+)\)</p>.*?'
                r'<td[^>]*>(\d{2}/\d{2}/\d{4})</td>.*?'
                r'<td[^>]*>(\[[^\]]+\])</td>.*?'
                r'href="([^"]*resultats\.php[^"]*)".*?'
                r'</td>\s*<td[^>]*>([^<]+)</td>',
                re.DOTALL
            )
            
            matches = pattern.findall(html)
            for m in matches:
                results.append(list(m) + [b_label])
        except:
            continue

    if not results:
        return pd.DataFrame()

    colonnes = ["Épreuve", "Temps", "Âge", "Points", "Ville", "Code pays",
                "Date", "Catégorie", "Lien résultats", "Club", "Bassin_Type"]

    df = pd.DataFrame(results, columns=colonnes)
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
    df["Temps_sec"] = df["Temps"].apply(
        lambda t: int(t.split(":")[0])*60 + float(t.split(":")[1]) if ":" in t else float(t)
    )

    ordre_nages = {"NL": 0, "Brasse": 1, "Papillon": 2, "Dos": 3, "4 Nages": 4}
    
    def get_sort_tuple(epreuve):
        index_nage = 99
        for nage, idx in ordre_nages.items():
            if nage in epreuve:
                index_nage = idx
                break
        dist_match = re.findall(r"\d+", epreuve)
        distance = int(dist_match[0]) if dist_match else 0
        return (index_nage, distance)

    df["sort_tuple"] = df["Épreuve"].apply(get_sort_tuple)
    df = df.sort_values(by="sort_tuple").drop(columns=["sort_tuple"])
    
    return df

# =========================
# APPLICATION
# =========================

full_df = load_all_data()
df_current = full_df[full_df["Bassin_Type"] == st.session_state.bassin]

if st.session_state.page == "home":
    # AJOUT DE L'ICÔNE ICI 🏊‍♂️
    st.title("Performances Tristan 🏊‍♂️")

    st.radio(
        "Bassin", ["25m", "50m"],
        index=["25m","50m"].index(st.session_state.bassin),
        horizontal=True, key="bassin_radio", on_change=update_bassin
    )

    if df_current.empty:
        st.warning("Aucune donnée disponible.")
    else:
        st.markdown("### Épreuves")
        epreuves = df_current["Épreuve"].unique().tolist()
        cols = st.columns(3)
        for i, epreuve in enumerate(epreuves):
            col = cols[i % 3]
            col.button(epreuve, key=f"home_{epreuve}", 
                       on_click=lambda e=epreuve: (st.session_state.update({"nage": e, "page": "perf"})), 
                       use_container_width=True)

elif st.session_state.page == "perf":
    if st.button("⬅ Autres nages"):
        st.session_state.page = "home"
        st.rerun()

    st.radio(
        "Bassin", ["25m", "50m"],
        index=["25m","50m"].index(st.session_state.bassin),
        horizontal=True, key="bassin_radio", on_change=update_bassin
    )

    nage_choisie = st.session_state.nage
    df_nage = df_current[df_current["Épreuve"] == nage_choisie].sort_values("Date", ascending=False)

    st.title(f"{nage_choisie} ({st.session_state.bassin})")

    if not df_nage.empty:
        table_df = df_nage[["Date","Temps","Âge","Points","Ville","Catégorie"]].copy()
        table_df["Date"] = table_df["Date"].dt.date
        best_idx = df_nage["Temps_sec"].idxmin()
        
        st.dataframe(table_df.style.apply(
            lambda r: ["background-color: #ffe4e1" if r.name==best_idx else "" for _ in r], axis=1
        ), use_container_width=True)

        df_graph = df_nage.sort_values("Date")
        t_min, t_max = math.floor(df_graph["Temps_sec"].min()) - 1, math.ceil(df_graph["Temps_sec"].max()) + 1
        y_ticks = np.linspace(t_min, t_max, 7)

        def sec_to_mmss(s):
            m, sec = int(s // 60), int(s % 60)
            return f"{m:02d}:{sec:02d}" if m > 0 else f"{sec:02d}"

        fig = px.scatter(df_graph, x="Date", y="Temps_sec", text="Temps", title="Progression")
        fig.update_traces(mode="lines+markers", marker=dict(size=10))
        fig.update_layout(
            yaxis=dict(
                title="Temps",
                tickvals=y_ticks, 
                ticktext=[sec_to_mmss(y) for y in y_ticks], 
                showgrid=True
            ),
            xaxis=dict(title="Date", tickformat="%d/%m/%Y"),
            margin=dict(l=60,r=20,t=60,b=60)
        )
        st.plotly_chart(fig, use_container_width=True)
