import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt

st.title("Performances natation")

# URL FFN (bassin 50m pour l'exemple)
url = "https://ffn.extranat.fr/webffn/nat_recherche.php?idact=nat&idrch_id=3518107&idopt=prf&idbas=50"

# Récupérer la page
response = requests.get(url)
soup = BeautifulSoup(response.text, "lxml")

# Extraire le tableau principal
table = soup.find("table", {"class": "tableau"})

# Stocker les données
data = []
for row in table.find_all("tr")[1:]:
    cols = row.find_all("td")
    if len(cols) >= 6:
        date = cols[0].text.strip()
        epreuve = cols[1].text.strip()
        temps = cols[2].text.strip()
        points = cols[5].text.strip()
        data.append([date, epreuve, temps, points])

df = pd.DataFrame(data, columns=["Date", "Epreuve", "Temps", "Points"])

st.write("Voici les dernières performances :")
st.dataframe(df)

# Graphique exemple pour 50m NL
df_50nl = df[df["Epreuve"].str.contains("50 NL")]
if not df_50nl.empty:
    df_50nl['Temps_sec'] = df_50nl['Temps'].str.split(':').apply(lambda x: int(x[0])*60 + float(x[1]) if len(x)==2 else float(x[0]))
    df_50nl['Date'] = pd.to_datetime(df_50nl['Date'], dayfirst=True)
    df_50nl = df_50nl.sort_values('Date')

    plt.figure(figsize=(8,4))
    plt.plot(df_50nl['Date'], df_50nl['Temps_sec'], marker='o')
    plt.xlabel("Date")
    plt.ylabel("Temps (s)")
    plt.title("50 m NL - progression")
    plt.grid(True)
    st.pyplot(plt)
else:
    st.write("Pas encore de performances pour le 50 NL")
