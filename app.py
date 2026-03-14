import reflex as rx
import urllib.request
import re
import html
import json
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Union

# ── 1. PARSEUR ───────────────────────────────────────────────────────────────

@dataclass
class Split:
    distance_m: int
    cumulative_time: str
    lap_time: str
    half_time: Optional[str] = None

@dataclass
class Performance:
    epreuve: str
    temps_final: str
    age_categorie: str
    points: str
    club: str
    pays: str
    date: str
    type_compet: str
    competition: str
    lien_resultats: str
    splits: list[Split] = field(default_factory=list)

def strip_tags(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text)).strip()

def find_all(pattern: str, text: str) -> list[str]:
    return re.findall(pattern, text, re.DOTALL)

def find_one(pattern: str, text: str, default: str = "") -> str:
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1).strip() if m else default

def extract_split_from_cells(cells: list[str], offset: int) -> Optional[Split]:
    if offset + 3 > len(cells): return None
    dist_text = strip_tags(cells[offset])
    dist_match = re.match(r"(\d+)", dist_text)
    if not dist_match: return None
    return Split(
        distance_m=int(dist_match.group(1)),
        cumulative_time=strip_tags(cells[offset+1]),
        lap_time=strip_tags(cells[offset+2]).replace("(", "").replace(")", ""),
        half_time=strip_tags(cells[offset+3]).replace("[", "").replace("]", "") if offset + 3 < len(cells) else None
    )

def parse_splits(tippy_raw: str) -> list[Split]:
    decoded = html.unescape(tippy_raw)
    splits = []
    for row in find_all(r"<tr[^>]*>(.*?)</tr>", decoded):
        cells = find_all(r"<td[^>]*>(.*?)</td>", row)
        raw_td_attrs = find_all(r"<td([^>]*)>", row)
        separator_idx = next((i for i, attrs in enumerate(raw_td_attrs) if "border-right" in attrs), None)
        if separator_idx is not None:
            left  = extract_split_from_cells(cells, 0)
            right = extract_split_from_cells(cells, separator_idx + 1)
            if left:  splits.append(left)
            if right: splits.append(right)
        else:
            s = extract_split_from_cells(cells, 0)
            if s: splits.append(s)
    return sorted(splits, key=lambda s: s.distance_m)

def parse_row(row: str, base_url: str = "https://ffn.extranat.fr") -> Optional[Performance]:
    th = find_one(r"<th[^>]*>(.*?)</th>", row)
    if not th: return None
    tds = find_all(r"<td[^>]*>(.*?)</td>", row)
    if len(tds) < 8: return None
    tippy_match = re.search(r'data-tippy-content=[\'"]([^\'"]*)[\'"]', tds[0])
    splits = parse_splits(tippy_match.group(1)) if tippy_match else []
    ps = find_all(r"<p[^>]*>(.*?)</p>", tds[3])
    return Performance(
        epreuve=strip_tags(th),
        temps_final=strip_tags(tds[0]),
        age_categorie=strip_tags(tds[1]).strip("()"),
        points=strip_tags(tds[2]),
        club=strip_tags(tds[3].split("<p")[0]),
        pays=strip_tags(tds[3].split("<p")[2]) if len(tds[3].split("<p")) > 2 else "",
        date=strip_tags(tds[4]),
        type_compet=strip_tags(tds[5]),
        competition=strip_tags(ps[0]) if ps else strip_tags(tds[3]),
        lien_resultats=base_url + find_one(r'href=["\']([^"\']+)["\']', tds[6]),
        splits=splits
    )

# ── 2. TYPES REFLEX ──────────────────────────────────────────────────────────

class SplitRow(rx.Base):
    dist:    str
    cumul:   str
    partiel: str
    half:    str

class Result(rx.Base):
    E: str
    T: str
    P: str
    D: str
    B: str
    S: str
    N: str
    V: str

# ── 3. CONSTANTES ────────────────────────────────────────────────────────────

GRILLE_QUALIF_FULL = {
    "U14": {"50 NL": "26.69", "100 NL": "58.35", "200 NL": "2:07.82", "400 NL": "4:30.66", "800 NL": "9:20.58", "1500 NL": "17:57.75", "50 Dos": "31.01", "100 Dos": "1:07.51", "200 Dos": "2:27.36", "50 Bra": "34.37", "100 Bra": "1:15.49", "200 Bra": "2:45.40", "50 Pap": "28.69", "100 Pap": "1:04.55", "200 Pap": "2:27.53", "200 4 N": "2:26.46", "400 4 N": "5:09.80"},
    "U15": {"50 NL": "25.84", "100 NL": "56.40", "200 NL": "2:03.32", "400 NL": "4:19.17", "800 NL": "8:56.13", "1500 NL": "17:06.91", "50 Dos": "29.75", "100 Dos": "1:03.80", "200 Dos": "2:19.06", "50 Bra": "32.44", "100 Bra": "1:11.83", "200 Bra": "2:36.44", "50 Pap": "27.57", "100 Pap": "1:01.68", "200 Pap": "2:17.95", "200 4 N": "2:19.61", "400 4 N": "4:57.12"},
    "U16": {"50 NL": "25.12", "100 NL": "54.74", "200 NL": "1:59.17", "400 NL": "4:13.10", "800 NL": "8:43.25", "1500 NL": "16:37.59", "50 Dos": "28.82", "100 Dos": "1:02.16", "200 Dos": "2:15.12", "50 Bra": "31.47", "100 Bra": "1:08.99", "200 Bra": "2:29.68", "50 Pap": "26.72", "100 Pap": "59.46", "200 Pap": "2:14.77", "200 4 N": "2:15.93", "400 4 N": "4:48.11"},
    "U17": {"50 NL": "24.62", "100 NL": "53.58", "200 NL": "1:57.16", "400 NL": "4:06.12", "800 NL": "8:31.04", "1500 NL": "16:13.01", "50 Dos": "28.08", "100 Dos": "1:00.70", "200 Dos": "2:11.69", "50 Bra": "30.79", "100 Bra": "1:07.27", "200 Bra": "2:27.33", "50 Pap": "26.05", "100 Pap": "58.19", "200 Pap": "2:11.64", "200 4 N": "2:12.61", "400 4 N": "4:42.69"},
    "U18": {"50 NL": "24.12", "100 NL": "52.84", "200 NL": "1:55.48", "400 NL": "4:02.58", "800 NL": "8:25.11", "1500 NL": "16:02.04", "50 Dos": "27.69", "100 Dos": "59.70", "200 Dos": "2:10.64", "50 Bra": "30.10", "100 Bra": "1:06.34", "200 Bra": "2:26.62", "50 Pap": "25.55", "100 Pap": "57.14", "200 4 N": "2:10.50", "400 4 N": "4:39.07"},
}

BIRTH_YEAR = 2011
SEP_CHAMP  = "§"
SEP_SPLIT  = ";"

# Codes épreuves FFN
EPREUVE_CODES = {
    "50 NL": 51, "100 NL": 52, "200 NL": 53, "400 NL": 54, "800 NL": 55, "1500 NL": 56,
    "50 Dos": 61, "100 Dos": 62, "200 Dos": 63,
    "50 Bra": 71, "100 Bra": 72, "200 Bra": 73,
    "50 Pap": 81, "100 Pap": 82, "200 Pap": 83,
    "100 4 N": 90, "200 4 N": 91, "400 4 N": 92,
}

def current_season_year() -> int:
    """idsai = année civile courante."""
    return datetime.now().year

def epreuve_to_code(epreuve: str) -> Optional[int]:
    """Convertit un nom d'épreuve FFN en idepr. Ex: '50 NL' -> 51."""
    n = epreuve.upper().strip()
    # Normalisation : "50 LIBRE" -> "50 NL", "100 BRASSE" -> "100 Bra", etc.
    for key in EPREUVE_CODES:
        ku = key.upper()
        if ku == n: return EPREUVE_CODES[key]
    # Tentative partielle
    for key, code in EPREUVE_CODES.items():
        parts = key.upper().split()
        if all(p in n for p in parts): return code
    return None

def parse_ranking_row(html_content: str, swimmer_id: str = "3518107") -> dict:
    """Extrait les rangs dept/région/national par catégorie depuis la page de classement FFN."""
    result = {"dept": "-", "region": "-", "national": "-"}
    rows = find_all(r"<tr[^>]*>(.*?)</tr>", html_content)
    target_row = next((r for r in rows if swimmer_id in r), None)
    if not target_row:
        return result
    all_tippies = re.findall(r'data-tippy-content="(.*?)"(?:\s|>)', target_row, re.DOTALL)
    if not all_tippies:
        all_tippies = re.findall(r"data-tippy-content='(.*?)'(?:\s|>)", target_row, re.DOTALL)
    raw_tippy = next((t for t in all_tippies if "Rang" in html.unescape(t)), None)
    if not raw_tippy:
        return result
    tippy = html.unescape(raw_tippy)

    def extract_rank(pattern):
        m = re.search(pattern, tippy, re.DOTALL)
        if not m: return "-"
        clean = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        return clean.split(" : ")[0].strip()

    result["national"] = extract_rank(r"Rang national par cat[^→]*→\s*<b>(.*?)</b>")
    result["region"]   = extract_rank(r"Rang r[ée]gional[^→]*par cat[^→]*→\s*<b>(.*?)</b>")
    result["dept"]     = extract_rank(r"Rang d[ée]part[^→]*par cat[^→]*→\s*<b>(.*?)</b>")
    return result

def encode_splits(splits: list[Split]) -> str:
    return SEP_SPLIT.join(
        f"{s.distance_m}{SEP_CHAMP}{s.cumulative_time}{SEP_CHAMP}{s.lap_time}{SEP_CHAMP}{s.half_time or ''}"
        for s in splits
    )

# ── 4. STATE ─────────────────────────────────────────────────────────────────

def flag_svg():
    return rx.box(
        rx.html('<svg width="14" height="10" viewBox="0 0 3 2" style="display:inline-block;vertical-align:middle;margin-left:4px;border-radius:1px;"><rect width="1" height="2" fill="#002395"/><rect width="1" height="2" x="1" fill="#fff"/><rect width="1" height="2" x="2" fill="#ed2939"/></svg>'),
        display="inline-block",
    )

class State(rx.State):
    current_bassin: str = "50m"
    results_json: str = rx.LocalStorage("[]", name="swim_v91")
    last_update_str_store: str = rx.LocalStorage("0", name="up_v91")
    loading: bool = False
    rankings_json: str = rx.LocalStorage("{}", name="rank_v94")
    dialog_open: bool = False
    dialog_key:  str = ""
    dialog_lieu: str = ""
    dialog_type: str = ""
    dialog_date: str = ""

    def on_load(self): return rx.console_log("v90")

    @rx.var
    def selected_nage(self) -> str:
        try: return self.router.page.params.get("nage", "")
        except: return ""

    def change_bassin(self, v: Union[str, list[str]]):
        self.current_bassin = v[0] if isinstance(v, list) else v

    @rx.var
    def current_category(self) -> str: return f"U{2026 - BIRTH_YEAR}"

    def to_sec(self, t):
        try:
            t = str(t).replace(" ", "").strip()
            if ":" in t:
                m, s = t.split(":")
                return int(m) * 60 + float(s)
            return float(t)
        except: return 9999.0

    def format_min_sec_short(self, s):
        m = int(s // 60); sec = int(s % 60)
        return f"{m}:{sec:02d}" if m > 0 else f"{sec}s"

    def get_qualif_key(self, nage_full: str) -> str:
        n = nage_full.upper()
        dist = re.search(r'\d+', n).group() if re.search(r'\d+', n) else ""
        type_n = "NL" if "NL" in n or "LIBRE" in n else "Bra" if "BRA" in n else "Dos" if "DOS" in n else "Pap" if "PAP" in n else "4 N" if "4 N" in n else ""
        return f"{dist} {type_n}".strip()

    @rx.var
    def qualif_time_val(self) -> str:
        if self.current_bassin != "50m": return ""
        return GRILLE_QUALIF_FULL.get(self.current_category, {}).get(self.get_qualif_key(self.selected_nage), "")

    @rx.var
    def gap_to_qualif_txt(self) -> str:
        if not self.qualif_time_val or not self.best_time_val: return ""
        diff = self.to_sec(self.best_time_val) - self.to_sec(self.qualif_time_val)
        return "Qualifié ! 🎉" if diff <= 0 else f"+{diff:.2f}s (Cible {self.current_category})"

    @rx.var
    def last_up_display(self) -> str:
        try:
            val = float(self.last_update_str_store)
            return f"MAJ : {datetime.fromtimestamp(val).strftime('%d/%m/%Y %H:%M')}" if val > 0 else ""
        except: return ""

    @rx.var
    def current_results_list(self) -> list[Result]:
        try: return [Result(**r) for r in json.loads(self.results_json)]
        except: return []

    @rx.var
    def available_nages(self) -> list[str]:
        return sorted(
            list({r.E for r in self.current_results_list if r.B == self.current_bassin}),
            key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0,
        )

    @rx.var
    def filtered_data(self) -> list[Result]:
        if not self.selected_nage: return []
        d = [r for r in self.current_results_list if r.E == self.selected_nage and r.B == self.current_bassin]
        return sorted(d, key=lambda x: datetime.strptime(x.D, "%d/%m/%Y"), reverse=True)

    @rx.var
    def best_time_val(self) -> str:
        if not self.filtered_data: return ""
        try: return min(self.filtered_data, key=lambda x: self.to_sec(x.T)).T
        except: return ""

    @rx.var
    def plot_fig(self) -> go.Figure:
        d = sorted(self.filtered_data, key=lambda x: datetime.strptime(x.D, "%d/%m/%Y"))
        if not d: return go.Figure()
        dates = [datetime.strptime(x.D, "%d/%m/%Y") for x in d]
        secs  = [self.to_sec(x.T) for x in d]
        f = go.Figure(go.Scatter(
            x=dates, y=secs, mode='lines+markers',
            text=[f"{x.D}<br>{x.T}" for x in d], hoverinfo='text',
            line=dict(color='#3b82f6', width=2),
            marker=dict(size=10, color='#3b82f6', line=dict(width=2, color='white')),
        ))
        q_val = self.qualif_time_val
        vals  = secs + ([self.to_sec(q_val)] if q_val else [])
        min_v, max_v = min(vals) * 0.99, max(vals) * 1.01
        tick_vals = np.linspace(min_v, max_v, 5)
        if self.current_bassin == "50m" and q_val:
            f.add_hline(y=self.to_sec(q_val), line_dash="dash", line_color="#ef4444", line_width=2,
                        annotation_text=f"Cible {self.current_category} ({q_val})",
                        annotation_position="top left", annotation_font_size=11, annotation_font_color="#ef4444")
        f.update_layout(
            yaxis=dict(tickmode='array', tickvals=tick_vals, ticktext=[self.format_min_sec_short(v) for v in tick_vals]),
            margin=dict(l=50, r=20, t=30, b=30), height=230,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="gray", size=10), showlegend=False, dragmode=False,
        )
        return f

    @rx.var
    def splits_per_result(self) -> dict[str, list[SplitRow]]:
        out: dict[str, list[SplitRow]] = {}
        for r in self.filtered_data:
            rows: list[SplitRow] = []
            if r.S:
                for seg in r.S.split(SEP_SPLIT):
                    parts = seg.split(SEP_CHAMP)
                    if len(parts) == 4:
                        rows.append(SplitRow(dist=parts[0]+"m", cumul=parts[1], partiel=parts[2], half=parts[3]))
            out[r.D + r.T] = rows
        return out

    @rx.var
    def has_50m_splits(self) -> bool:
        """True si les splits de la nage sélectionnée commencent à 50m (pas 100m)."""
        for r in self.filtered_data:
            if r.S:
                first_seg = r.S.split(SEP_SPLIT)[0]
                parts = first_seg.split(SEP_CHAMP)
                if len(parts) >= 1:
                    try: return int(parts[0]) == 50
                    except: pass
        return False

    @rx.var
    def dialog_has_50m_splits(self) -> bool:
        """True si les splits du dialog commencent à 50m (pas 100m)."""
        splits = self.dialog_splits
        if not splits:
            return False
        try:
            return int(splits[0].dist.replace("m", "")) == 50
        except:
            return False

    @rx.var
    def dialog_splits(self) -> list[SplitRow]:
        """Splits du dialog ouvert. Si 16 splits (800m 25m), filtre aux multiples de 100m."""
        all_splits = self.splits_per_result.get(self.dialog_key, [])
        if len(all_splits) == 16:
            return [s for s in all_splits if int(s.dist.replace("m", "")) % 100 == 0]
        return all_splits

    def open_dialog(self, key: str, lieu: str, type_compet: str, date: str):
        self.dialog_key  = key
        self.dialog_lieu = lieu
        self.dialog_type = type_compet
        self.dialog_date = date
        self.dialog_open = True

    def close_dialog(self):
        self.dialog_open = False

    @rx.var
    def current_rankings(self) -> dict:
        try: return json.loads(self.rankings_json)
        except: return {}

    @rx.var
    def selected_nage_rankings(self) -> dict:
        """Classements pour la nage+bassin sélectionnée."""
        # Normaliser : "50 Bra." -> "50 Bra", "200 Pap." -> "200 Pap"
        nage = self.selected_nage.rstrip(".")
        key = f"{nage}|{self.current_bassin}"
        return self.current_rankings.get(key, {"dept": "—", "region": "—", "national": "—"})

    def force_refresh(self):
        if self.loading: return
        self.loading = True
        yield
        all_res = []
        all_ranks = {}
        try:
            # ── Performances ──────────────────────────────────────────
            for bc, bl in [("25", "25m"), ("50", "50m")]:
                url = f"https://ffn.extranat.fr/webffn/nat_recherche.php?idact=nat&idrch_id=3518107&idopt=prf&idbas={bc}"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with opener.open(req, timeout=15) as resp:
                    html_content = resp.read().decode("utf-8", errors="replace")
                rows = find_all(r"<tr\b[^>]*class=[^>]*border-b[^>]*>(.*?)</tr>", html_content)
                for row in rows:
                    perf = parse_row(row)
                    if perf:
                        all_res.append({
                            "E": perf.epreuve, "T": perf.temps_final, "P": perf.points,
                            "D": perf.date, "B": bl, "S": encode_splits(perf.splits),
                            "N": perf.competition, "V": perf.type_compet,
                        })
            self.results_json = json.dumps(all_res)
            self.last_update_str_store = str(time.time())
            yield
            # ── Classements ───────────────────────────────────────────
            sai = current_season_year()
            cat = sai - BIRTH_YEAR
            for bc, bl in [("25", "25m"), ("50", "50m")]:
                for epr_name, idepr in EPREUVE_CODES.items():
                    try:
                        url_dep = f"https://ffn.extranat.fr/webffn/nat_rankings.php?idact=nat&idopt=sai&go=epr&idbas={bc}&idepr={idepr}&idsai={sai}&idcat={cat}&iddep=1611"
                        req = urllib.request.Request(url_dep, headers={"User-Agent": "Mozilla/5.0"})
                        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                        with opener.open(req, timeout=10) as resp:
                            html_content = resp.read().decode("utf-8", errors="replace")
                        all_ranks[f"{epr_name}|{bl}"] = parse_ranking_row(html_content)
                    except:
                        all_ranks[f"{epr_name}|{bl}"] = {"dept": "-", "region": "-", "national": "-"}
            self.rankings_json = json.dumps(all_ranks)
        finally:
            self.loading = False
            yield

    @rx.var
    def ranking_national_txt(self) -> str:
        return self.selected_nage_rankings.get("national", "-")

    @rx.var
    def ranking_region_txt(self) -> str:
        return self.selected_nage_rankings.get("region", "-")

    @rx.var
    def ranking_dept_txt(self) -> str:
        return self.selected_nage_rankings.get("dept", "-")

    @rx.var
    def ranking_title(self) -> str:
        return f"Classement {current_season_year()} U{current_season_year() - BIRTH_YEAR}"

    def nav_to_nage(self, n): return rx.redirect(f"/?nage={n}")
    def nav_back(self): return rx.redirect("/")

# ── 5. COMPOSANTS UI ─────────────────────────────────────────────────────────

def split_row_ui(s: SplitRow) -> rx.Component:
    """Avec partiel bleu (splits aux 50m) + half vert optionnel."""
    return rx.hstack(
        rx.text(s.dist + " :",        font_size="0.75em", color=rx.color("gray", 10), width="52px", text_align="right"),
        rx.text(s.cumul,              font_size="0.75em", font_weight="bold", color=rx.color("gray", 12), width="64px"),
        rx.text("(" + s.partiel + ")", font_size="0.75em", color=rx.color("blue", 9), width="62px"),
        rx.cond(
            s.half != "",
            rx.text("[" + s.half + "]", font_size="0.72em", color=rx.color("green", 9)),
            rx.box(),
        ),
        spacing="2", align="center",
    )

def split_row_ui_100m(s: SplitRow) -> rx.Component:
    """Sans partiel bleu (splits aux 100m uniquement) — juste cumulé + [half]."""
    return rx.hstack(
        rx.text(s.dist + " :", font_size="0.75em", color=rx.color("gray", 10), width="52px", text_align="right"),
        rx.text(s.cumul,       font_size="0.75em", font_weight="bold", color=rx.color("gray", 12), width="64px"),
        rx.cond(
            s.half != "",
            rx.text("[" + s.half + "]", font_size="0.72em", color=rx.color("green", 9)),
            rx.box(),
        ),
        spacing="2", align="center",
    )

def splits_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # En-tête : lieu en gras, date + type en dessous, croix à droite
                rx.hstack(
                    rx.vstack(
                        rx.text(State.dialog_lieu, font_weight="bold", font_size="0.9em", color=rx.color("gray", 12)),
                        rx.text(
                            State.dialog_date + "  " + State.dialog_type,
                            font_size="0.72em", color=rx.color("gray", 10),
                        ),
                        spacing="0", align_items="start",
                    ),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.button(
                            rx.icon(tag="x", size=16),
                            variant="ghost", size="1",
                            on_click=State.close_dialog,
                        ),
                    ),
                    width="100%", align="start",
                ),
                rx.divider(),
                # Splits scrollables
                rx.cond(
                    State.dialog_splits.length() > 0,
                    rx.cond(
                        State.dialog_has_50m_splits,
                        rx.vstack(rx.foreach(State.dialog_splits, split_row_ui),      spacing="1", align_items="start", width="100%", overflow_y="auto", max_height="55vh"),
                        rx.vstack(rx.foreach(State.dialog_splits, split_row_ui_100m), spacing="1", align_items="start", width="100%", overflow_y="auto", max_height="55vh"),
                    ),
                    rx.text("Aucun temps de passage", font_size="0.8em", color=rx.color("gray", 10)),
                ),
                spacing="3", width="100%",
            ),
            background_color=rx.color("gray", 1),
            border="1px solid var(--gray-4)",
            border_radius="16px",
            padding="16px",
            max_width="360px",
            width="92vw",
        ),
        open=State.dialog_open,
        on_open_change=State.close_dialog,
    )

def index():
    l_style = dict(font_size="0.75em", font_weight="bold", color=rx.color("gray", 11), margin_bottom="4px", margin_left="4px")
    return rx.theme(
        rx.center(
        splits_dialog(),
        rx.cond(
            State.selected_nage == "",
            # ── Page d'accueil ───────────────────────────────────────
            rx.vstack(
                rx.hstack(
                    rx.heading("Tristan Swim 🏊‍♂️", size="7", color=rx.color("gray", 12)),
                    rx.spacer(),
                    rx.color_mode.button(variant="ghost"),
                    rx.button(rx.icon(tag="refresh-cw"), on_click=State.force_refresh, variant="ghost", loading=State.loading),
                    width="100%", align="center",
                ),
                rx.vstack(
                    rx.text("Bassin", style=l_style),
                    rx.segmented_control.root(
                        rx.segmented_control.item("25m", value="25m"),
                        rx.segmented_control.item("50m", value="50m"),
                        on_change=State.change_bassin, value=State.current_bassin, width="100%",
                    ),
                    width="100%", align_items="start", spacing="0",
                ),
                rx.vstack(
                    rx.text("Nage", style=l_style),
                    rx.tabs.root(
                        rx.tabs.list(
                            rx.tabs.trigger("NL",   value="nl",  flex_grow="1"),
                            rx.tabs.trigger("Bra.", value="br",  flex_grow="1"),
                            rx.tabs.trigger("Pap.", value="pp",  flex_grow="1"),
                            rx.tabs.trigger("Dos",  value="ds",  flex_grow="1"),
                            rx.tabs.trigger("4N",   value="4n",  flex_grow="1"),
                            width="100%",
                        ),
                        rx.box(
                            rx.tabs.content(rx.grid(rx.foreach(State.available_nages, lambda n: rx.cond(n.contains("NL") | n.contains("Libre"), rx.button(n, on_click=lambda: State.nav_to_nage(n), variant="soft", width="100%"))), columns="2", spacing="2", padding_y="10px"), value="nl"),
                            rx.tabs.content(rx.grid(rx.foreach(State.available_nages, lambda n: rx.cond(n.contains("Bra"),  rx.button(n, on_click=lambda: State.nav_to_nage(n), variant="soft", width="100%"))), columns="2", spacing="2", padding_y="10px"), value="br"),
                            rx.tabs.content(rx.grid(rx.foreach(State.available_nages, lambda n: rx.cond(n.contains("Pap"),  rx.button(n, on_click=lambda: State.nav_to_nage(n), variant="soft", width="100%"))), columns="2", spacing="2", padding_y="10px"), value="pp"),
                            rx.tabs.content(rx.grid(rx.foreach(State.available_nages, lambda n: rx.cond(n.contains("Dos"),  rx.button(n, on_click=lambda: State.nav_to_nage(n), variant="soft", width="100%"))), columns="2", spacing="2", padding_y="10px"), value="ds"),
                            rx.tabs.content(rx.grid(rx.foreach(State.available_nages, lambda n: rx.cond(n.contains("4 N"), rx.button(n, on_click=lambda: State.nav_to_nage(n), variant="soft", width="100%"))), columns="2", spacing="2", padding_y="10px"), value="4n"),
                            min_height="350px", width="100%",
                        ),
                        default_value="nl", width="100%",
                    ),
                    width="100%", align_items="start", spacing="0",
                ),
                rx.text(State.last_up_display, font_size="0.7em", color=rx.color("gray", 10)),
                spacing="5", padding="1.2em", border_radius="20px",
                width=["98%", "420px"],
                background_color=rx.color("gray", 1),
                border="1px solid var(--gray-4)",
                margin_bottom="5em",
            ),
            # ── Page détail nage ─────────────────────────────────────
            rx.vstack(
                rx.button(
                    rx.hstack(rx.icon(tag="chevron-left"), rx.text("Retour")),
                    on_click=State.nav_back, variant="ghost", color_scheme="blue",
                ),
                rx.hstack(
                    rx.heading(f"{State.selected_nage} ({State.current_bassin})", size="4", color=rx.color("gray", 12)),
                    rx.spacer(),
                    rx.color_mode.button(variant="ghost"),
                    width="100%", align="center",
                ),
                rx.segmented_control.root(
                    rx.segmented_control.item("25m", value="25m"),
                    rx.segmented_control.item("50m", value="50m"),
                    on_change=State.change_bassin, value=State.current_bassin, width="100%",
                ),
                rx.hstack(
                    rx.badge(f"RECORD : {State.best_time_val}", color_scheme="blue", variant="solid", size="3", flex_grow="1"),
                    rx.cond(
                        State.qualif_time_val != "",
                        rx.badge(
                            rx.hstack(rx.text(State.gap_to_qualif_txt), flag_svg(), align="center"),
                            color_scheme=rx.cond(State.gap_to_qualif_txt.contains("Qualifié"), "green", "orange"),
                            variant="soft", size="3", flex_grow="1",
                        ),
                    ),
                    width="100%",
                ),
                # ── Classements ──────────────────────────────────────
                rx.vstack(
                    rx.text(State.ranking_title, font_size="0.72em", font_weight="bold", color=rx.color("gray", 11)),
                    rx.hstack(
                        # France
                        rx.vstack(
                            rx.hstack(
                                rx.html('<svg width="16" height="11" viewBox="0 0 3 2" style="display:inline-block;vertical-align:middle;border-radius:1px;"><rect width="1" height="2" fill="#002395"/><rect width="1" height="2" x="1" fill="#fff"/><rect width="1" height="2" x="2" fill="#ed2939"/></svg>'),
                                rx.text("France", font_size="0.7em", color=rx.color("gray", 11)),
                                spacing="1", align="center",
                            ),
                            rx.text(State.ranking_national_txt, font_size="1em", font_weight="bold", color=rx.color("blue", 9)),
                            spacing="0", align_items="center", flex_grow="1",
                        ),
                        rx.divider(orientation="vertical", height="32px"),
                        # Région
                        rx.vstack(
                            rx.hstack(
                                rx.text("🏔", font_size="0.8em"),
                                rx.text("AURA", font_size="0.7em", color=rx.color("gray", 11)),
                                spacing="1", align="center",
                            ),
                            rx.text(State.ranking_region_txt, font_size="1em", font_weight="bold", color=rx.color("green", 9)),
                            spacing="0", align_items="center", flex_grow="1",
                        ),
                        rx.divider(orientation="vertical", height="32px"),
                        # Département
                        rx.vstack(
                            rx.hstack(
                                rx.text("📍", font_size="0.8em"),
                                rx.text("Isère", font_size="0.7em", color=rx.color("gray", 11)),
                                spacing="1", align="center",
                            ),
                            rx.text(State.ranking_dept_txt, font_size="1em", font_weight="bold", color=rx.color("orange", 9)),
                            spacing="0", align_items="center", flex_grow="1",
                        ),
                        width="100%", align="center",
                    ),
                    spacing="2", align_items="start",
                    width="100%",
                    padding="10px 12px",
                    border_radius="8px",
                    background_color=rx.color("gray", 2),
                    border="1px solid var(--gray-4)",
                ),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Date"),
                            rx.table.column_header_cell("Temps"),
                            rx.table.column_header_cell("Pts"),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            State.filtered_data,
                            lambda r: rx.table.row(
                                rx.table.cell(r.D),
                                rx.table.cell(rx.text(r.T, font_weight=rx.cond(r.T == State.best_time_val, "bold", "normal"), color=rx.cond(r.T == State.best_time_val, rx.color("blue", 9), rx.color("gray", 12)))),
                                rx.table.cell(rx.text(r.P, color=rx.color("gray", 11))),
                                cursor="pointer",
                                _hover={"background_color": "var(--gray-3)"},
                                on_click=State.open_dialog(r.D + r.T, r.N, r.V, r.D),
                            ),
                        ),
                    ),
                    width="100%", size="1", variant="surface",
                ),
                rx.box(
                    rx.plotly(data=State.plot_fig, config={"displayModeBar": False, "responsive": True}, width="100%"),
                    width="100%", border="1px solid var(--gray-4)",
                    border_radius="12px", overflow="hidden", padding_y="10px",
                ),
                spacing="4", width=["98%", "500px"], padding="0.8em", margin_bottom="5em",
            ),
        ),
        min_height="100vh",
        ),
        appearance="inherit",
    )

app = rx.App(theme=rx.theme(appearance="inherit"))
app.add_page(index, route="/", on_load=State.on_load)
