import streamlit as st
import pandas as pd
import requests
import re
import plotly.express as px
import numpy as np
import math

st.set_page_config(page_title="Performances Natation Tristan", layout="wide")
st.title("Performances Natation Tristan")

# ---- Session State pour mémoriser les choix ----
if 'bassin' not in st.session_state:
    st.session_state.bassin = "50m"
if 'nage' not in st.session_state:
    st.session_state.nage = None

# ---- Sélection du bassin ----
bassin = st.selectbox(
    "Choisissez le bassin :",
    ["25m", "50m"],
    index=["25m", "50m"].index(st.session_state.bassin)
)
st.session_state.bassin = bassin

# ---- URL selon le bassin ----
idrch_id = "3518107"
idopt = "prf"
idbas = "25" if bassin == "25m" else "50"
url = f"https://ffn.extranat.fr/webffn/nat_recherche.php?idact=nat&idrch_id={idrch_id}&idopt={idopt}&idbas={idbas}"

# ---- Récupération du HTML ----
response = requests.get(url)
html = response.text

# ---- Regex ----
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

    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)

    def time_to_sec(t):
        parts = t.strip().split(":")
        if len(parts) == 2:
            return int(parts[0])*60 + float(parts[1])
        else:
            return float(parts[0])

    df['Temps_sec'] = df['Temps'].apply(time_to_sec)

    # ---- Menu nage ----
    nage_options = df['Épreuve'].unique().tolist()
    if st.session_state.nage not in nage_options:
        st.session_state.nage = nage_options[0]

    nage_choisie = st.selectbox(
        "Choisissez la nage :",
        options=nage_options,
        index=nage_options.index(st.session_state.nage)
    )
    st.session_state.nage = nage_choisie

    # ---- Filtrage ----
    df_nage = df[df['Épreuve'] == nage_choisie].sort_values('Date', ascending=False)

    # tableau sans heure
    df_table = df_nage.copy()
    df_table['Date'] = df_table['Date'].dt.date

    st.subheader(f"Performances pour {nage_choisie} ({bassin})")
    st.dataframe(df_table[["Date", "Temps", "Âge", "Points", "Ville", "Catégorie", "Club"]])

    # ---- Graphique progression ----
       
    if not df_nage.empty:
        df_nage_sorted = df_nage.sort_values('Date')

        perf_min = df_nage_sorted['Temps_sec'].min()
        perf_max = df_nage_sorted['Temps_sec'].max()

        # ticks Y : 1 seconde en dessous et au-dessus
        tick_min = math.floor(perf_min) - 1
        tick_max = math.ceil(perf_max) + 1

        # nombre de ticks souhaité
        n_ticks = 7
        y_ticks = np.linspace(tick_min, tick_max, n_ticks)

        # format mm:ss
        def sec_to_mmss(s):
            s = int(round(s))
            m = s // 60
            sec = s % 60
            return f"{m}:{sec:02d}" if m > 0 else f"{sec}"

        y_tick_labels = [sec_to_mmss(y) for y in y_ticks]

        fig = px.scatter(
            df_nage_sorted,
            x='Date',
            y='Temps_sec',
            text='Temps',
            title=f"{nage_choisie} - progression ({bassin})",
        )

        fig.update_traces(
            mode='lines+markers',
            hovertemplate='Date: %{x}<br>Temps: %{text}'
        )

        fig.update_layout(
            yaxis=dict(
                tickvals=y_ticks,
                ticktext=y_tick_labels,
                range=[tick_min, tick_max],
                showgrid=True,
                gridcolor="LightGray",
                zeroline=False,
            ),
            xaxis=dict(
                tickformat="%d/%m/%Y",
                tickangle=-45,
                range=[
                    df_nage_sorted['Date'].min() - pd.Timedelta(days=7),
                    df_nage_sorted['Date'].max() + pd.Timedelta(days=7)
                ]
            ),
            margin=dict(l=60, r=20, t=60, b=60),
        )

        st.plotly_chart(fig, use_container_width=True)

