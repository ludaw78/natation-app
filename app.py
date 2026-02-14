import streamlit as st
import pandas as pd
import requests
import re
import plotly.express as px
import numpy as np
import math

st.set_page_config(page_title="Performances natation Tristan", layout="wide")

# =========================
# Session state navigation
# =========================

if "page" not in st.session_state:
    st.session_state.page = "home"

if "bassin" not in st.session_state:
    st.session_state.bassin = "50m"

if "nage" not in st.session_state:
    st.session_state.nage = None

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

    def time_to_sec(t):
        parts = t.strip().split(":")
        if len(parts) == 2:
            return int(parts[0])*60 + float(parts[1])
        else:
            return float(parts[0])

    df["Temps_sec"] = df["Temps"].apply(time_to_sec)

    return df


# =========================
# PAGE ACCUEIL
# =========================

if st.session_state.page == "home":

    st.title("Performances natation Tristan")

    bassin = st.radio("Choix du bassin", ["25m", "50m"], horizontal=True)
    st.session_state.bassin = bassin

    df = load_data(bassin)

    if df.empty:
        st.warning("Impossible de récupérer les performances.")
        st.stop()

    # classement des nages
    ordre_styles = ["NL", "Brasse", "Papillon", "Dos", "4 Nages"]

    def style_key(epreuve):
        for style in ordre_styles:
            if style in epreuve:
                return ordre_styles.index(style)
        return 999

    epreuves = sorted(df["Épreuve"].unique(),
                      key=lambda x: (style_key(x), int(re.findall(r"\d+", x)[0])))

    for epreuve in epreuves:
        if st.button(epreuve):
            st.session_state.page = "perf"
            st.session_state.nage = epreuve
            st.rerun()


# =========================
# PAGE PERFORMANCE
# =========================

elif st.session_state.page == "perf":

    bassin = st.radio(
        "Choix du bassin",
        ["25m", "50m"],
        index=["25m", "50m"].index(st.session_state.bassin),
        horizontal=True
    )
    st.session_state.bassin = bassin

    if st.button("⬅ Retour à l'accueil"):
        st.session_state.page = "home"
        st.rerun()

    df = load_data(bassin)

    nage_choisie = st.session_state.nage

    df_nage = df[df["Épreuve"] == nage_choisie].sort_values("Date", ascending=False)

    st.title(f"Performances {nage_choisie} ({bassin})")

    # Tableau sans index ni club
    table_df = df_nage[["Date", "Temps", "Âge", "Points", "Ville", "Catégorie"]].copy()
    table_df["Date"] = table_df["Date"].dt.date

    meilleur_temps = df_nage["Temps_sec"].min()

    def highlight_best(row):
        if row["Temps"] == df_nage.loc[df_nage["Temps_sec"].idxmin(), "Temps"]:
            return ["background-color: #ffe4e1"] * len(row)
        return [""] * len(row)

    st.dataframe(table_df.style.apply(highlight_best, axis=1), use_container_width=True)

    # Graphique
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
        title=f"{nage_choisie} - progression ({bassin})"
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
            range=[
                df_graph["Date"].min() - pd.Timedelta(days=7),
                df_graph["Date"].max() + pd.Timedelta(days=7)
            ]
        )
    )

    st.plotly_chart(fig, use_container_width=True)
