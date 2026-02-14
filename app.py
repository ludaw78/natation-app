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

# Callback pour le bassin (Règle le problème du double clic)
def update_bassin():
    st.session_state.bassin = st.session_state.bassin_radio

# =========================
# CSS CORRECTIF (VERT + TEXTE BLANC)
# =========================
st.markdown("""
<style>
/* Style de TOUS les boutons (Accueil et Page Perf) */
div.stButton > button {
    width: 100% !important;
    height: 50px !important;
    background-color: #4CAF50 !important; /* VERT */
    color: white !important;               /* TEXTE BLANC */
    border-radius: 10px !important;
    border: none !important;
    font-weight: bold !important;
}

/* Force la couleur du texte à l'intérieur du bouton */
div.stButton > button p {
    color: white !important;
}

/* Style spécifique pour le survol (hover) pour éviter qu'il redevienne blanc */
div.stButton > button:hover {
    background-color: #45a049 !important;
    color: white !important;
}

div.row-widget.stRadio > label {
    font-size: 16px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# =========================
# Fonction récupération données
# =========================
@st.cache_data(ttl=300)
def load_data(bassin):
    idrch_id = "3518107"
    idopt = "prf"
    idbas = "25" if bassin == "25m" else "50"
    url = f"https://ffn.extranat.fr/webffn/nat_recherche.php?idact=nat&idrch_id={idrch_id}&idopt={idopt}&idbas={idbas}"
    response = requests.get(url)
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
    if not matches:
        return pd.DataFrame()

    colonnes = ["Épreuve", "Temps", "Âge", "Points", "Ville", "Code pays",
                "Date", "Catégorie", "Lien résultats", "Club"]

    df = pd.DataFrame(matches, columns=colonnes)
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
    df["Temps_sec"] = df["Temps"].apply(
        lambda t: int(t.split(":")[0])*60 + float(t.split(":")[1]) if ":" in t else float(t)
    )

    ordre_styles = ["NL", "Brasse", "Papillon", "Dos", "4 Nages"]
    def style_key(epreuve):
        for i, style in enumerate(ordre_styles):
            if style in epreuve:
                dist_res = re.findall(r"\d+", epreuve)
                distance = int(dist_res[0]) if dist_res else 0
                return (i, distance)
        return (999, 0)
    df["TypeDist"] = df["Épreuve"].apply(style_key)
    df = df.sort_values("TypeDist")
    return df

# =========================
# Callbacks navigation
# =========================
def select_nage(epreuve):
    st.session_state.nage = epreuve
    st.session_state.page = "perf"

def go_home():
    st.session_state.nage = None
    st.session_state.page = "home"

# =========================
# PAGE ACCUEIL
# =========================
if st.session_state.page == "home":
    st.title("Performances natation Tristan")

    st.radio(
        "Bassin",
        ["25m", "50m"],
        index=["25m","50m"].index(st.session_state.bassin),
        horizontal=True,
        key="bassin_radio",
        on_change=update_bassin
    )

    df = load_data(st.session_state.bassin)
    if df.empty:
        st.warning("Impossible de récupérer les performances.")
        st.stop()

    st.markdown("### Épreuves")
    epreuves = df["Épreuve"].unique().tolist()
    n_col = 3
    cols = st.columns(n_col)
    for i, epreuve in enumerate(epreuves):
        col = cols[i % n_col]
        col.button(epreuve, key=f"home_{epreuve}", on_click=select_nage, args=(epreuve,), use_container_width=True)

# =========================
# PAGE PERFORMANCE
# =========================
elif st.session_state.page == "perf":

    st.button("⬅ Autres nages", on_click=go_home)

    st.radio(
        "Bassin",
        ["25m", "50m"],
        index=["25m","50m"].index(st.session_state.bassin),
        horizontal=True,
        key="bassin_radio",
        on_change=update_bassin
    )

    df = load_data(st.session_state.bassin)
    nage_choisie = st.session_state.nage
    df_nage = df[df["Épreuve"] == nage_choisie].sort_values("Date", ascending=False)

    st.title(f"Performances {nage_choisie} ({st.session_state.bassin})")

    if df_nage.empty:
        st.warning("Pas encore de performances pour cette nage.")
    else:
        table_df = df_nage[["Date","Temps","Âge","Points","Ville","Catégorie"]].copy()
        table_df["Date"] = table_df["Date"].dt.date

        best_idx = df_nage["Temps_sec"].idxmin()
        def highlight_best(row):
            return ["background-color: #ffe4e1" if row.name==best_idx else "" for _ in row]

        st.dataframe(table_df.style.apply(highlight_best, axis=1), use_container_width=True)

        # Graphique d'origine
        df_graph = df_nage.sort_values("Date")
        t_min = math.floor(df_graph["Temps_sec"].min()) - 1
        t_max = math.ceil(df_graph["Temps_sec"].max()) + 1
        y_ticks = np.linspace(t_min, t_max, 7)

        def sec_to_mmss(s):
            m = int(s // 60)
            sec = int(s % 60)
            return f"{m:02d}:{sec:02d}" if m > 0 else f"{sec:02d}"

        fig = px.scatter(
            df_graph,
            x="Date",
            y="Temps_sec",
            text="Temps",
            title=f"{nage_choisie} - progression ({st.session_state.bassin})"
        )
        fig.update_traces(mode="lines+markers")
        fig.update_layout(
            yaxis=dict(
                tickvals=y_ticks,
                ticktext=[sec_to_mmss(y) for y in y_ticks],
                showgrid=True
            ),
            xaxis=dict(
                tickformat="%d/%m/%Y",
                range=[df_graph["Date"].min()-pd.Timedelta(days=7),
                        df_graph["Date"].max()+pd.Timedelta(days=7)]
            ),
            margin=dict(l=60,r=20,t=60,b=60)
        )
        st.plotly_chart(fig, use_container_width=True)
