import streamlit as st
import pandas as pd
import requests
import re
import plotly.express as px
import numpy as np
import math

st.set_page_config(page_title="Performances Natation", layout="wide")
st.title("Performances natation")

# ---- Session State pour mémoriser les choix ----
if 'bassin' not in st.session_state:
    st.session_state.bassin = "50m"
if 'nage' not in st.session_state:
    st.session_state.nage = None

# ---- Sidebar : choix du bassin ----
with st.sidebar:
    st.header("Paramètres")

    bassin = st.radio(
        "Choisissez le bassin :",
        ["25m", "50m"],
        index=["25m", "50m"].index(st.session_state.bassin),
        horizontal=True
    )
    st.session_state.bassin = bassin

# ---- URL selon le bassin ----
idrch_id = "3518107"
idopt = "prf"
idbas = "25" if bassin == "25m" else "50"

url = f"https://ffn.extranat.fr/webffn/nat_recherche.php?idact=nat&idrch_id={idrch_id}&idopt={idopt}&idbas={idbas}"

# ---- Récupération HTML ----
response = requests.get(url)
html = response.text

# ---- Regex extraction ----
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
    st.warning("Impossible de récupérer les performances.")
else:
    colonnes = ["Épreuve", "Temps", "Âge", "Points", "Ville", "Code pays",
                "Date", "Catégorie", "Lien résultats", "Club"]

    df = pd.DataFrame(matches, columns=colonnes)

    # ---- Conversion date ----
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)

    # ---- Conversion temps en secondes ----
    def time_to_sec(t):
        parts = t.strip().split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        else:
            return float(parts[0])

    df['Temps_sec'] = df['Temps'].apply(time_to_sec)

    # ---- Choix nage (sidebar) ----
    nage_options = df['Épreuve'].unique().tolist()

    if st.session_state.nage not in nage_options:
        st.session_state.nage = nage_options[0]

    with st.sidebar:
        nage_choisie = st.selectbox(
            "Choisissez la nage :",
            options=nage_options,
            index=nage_options.index(st.session_state.nage)
        )
        st.session_state.nage = nage_choisie

    # ---- Filtrage ----
    df_nage = df[df['Épreuve'] == nage_choisie].sort_values('Date', ascending=False)

    st.subheader(f"Performances pour {nage_choisie} ({bassin})")

    # afficher date sans heure
    df_affichage = df_nage.copy()
    df_affichage["Date"] = df_affichage["Date"].dt.strftime("%d/%m/%Y")

    st.dataframe(df_affichage[["Date", "Temps", "Âge", "Points", "Ville", "Catégorie", "Club"]],
                 use_container_width=True)

    # ---- Graphique ----
    if not df_nage.empty:
        df_nage_sorted = df_nage.sort_values('Date')

        # bornes Y : 1 seconde marge
        t_min = math.floor(df_nage_sorted['Temps_sec'].min()) - 1
        t_max = math.ceil(df_nage_sorted['Temps_sec'].max()) + 1

        n_ticks = 7
        y_ticks = np.linspace(t_min, t_max, n_ticks)

        def sec_to_mmss(s):
            m = int(s // 60)
            sec = int(s % 60)
            return f"{m:02d}:{sec:02d}" if m > 0 else f"{sec:02d}"

        y_tick_labels = [sec_to_mmss(y) for y in y_ticks]

        fig = px.scatter(
            df_nage_sorted,
            x='Date',
            y='Temps_sec',
            text='Temps',
            title=f"{nage_choisie} - progression ({bassin})"
        )

        fig.update_traces(
            mode='lines+markers',
            hovertemplate='Date: %{x|%d/%m/%Y}<br>Temps: %{text}'
        )

        # marges en dates
        date_min = df_nage_sorted['Date'].min() - pd.Timedelta(days=7)
        date_max = df_nage_sorted['Date'].max() + pd.Timedelta(days=7)

        fig.update_layout(
            yaxis=dict(
                tickvals=y_ticks,
                ticktext=y_tick_labels,
                range=[t_min, t_max],
                showgrid=True,
                gridcolor="LightGray",
                zeroline=False
            ),
            xaxis=dict(
                range=[date_min, date_max],
                tickformat="%d/%m/%Y",
                tickangle=-45,
                showgrid=False
            ),
            margin=dict(l=60, r=20, t=60, b=60),
        )

        st.plotly_chart(fig, use_container_width=True)
