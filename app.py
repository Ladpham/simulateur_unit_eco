import streamlit as st
import pandas as pd
import altair as alt
from datetime import date

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Waribei – Unit Economics",
    layout="wide"
)

DUREE_PERIODE_LIQUIDITE_JOURS = 10

# --------------------------------------------------
# PRESETS (historique + défaut)
# --------------------------------------------------
PRESETS_BY_DATE = {
    # Historique demandé
    date(2025, 6, 1): {
        "name": "Historique – Jun 2025",
        "revenu_pct": 3.73,
        "cout_paiement_pct": 1.75,
        "cout_liquidite_10j_pct": 0.21,
        "defaut_30j_pct": 1.43,
    },
    date(2025, 12, 1): {
        "name": "Historique – Dec 2025",
        "revenu_pct": 3.76,
        "cout_paiement_pct": 1.80,
        "cout_liquidite_10j_pct": 0.36,
        "defaut_30j_pct": 1.00,
    },
    # Défaut dynamique demandé
    date(2026, 6, 1): {
        "name": "Default – Jun 2026",
        "revenu_pct": 3.80,
        "cout_paiement_pct": 1.20,
        "cout_liquidite_10j_pct": 0.40,
        "defaut_30j_pct": 1.00,
    },
}

DEFAULT_DATE = date(2026, 6, 1)

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------
if "scenarios" not in st.session_state:
    st.session_state.scenarios = []
if "baseline" not in st.session_state:
    st.session_state.baseline = None

# Date par défaut = juin 2026
if "scenario_date" not in st.session_state:
    st.session_state.scenario_date = DEFAULT_DATE

# Pour éviter d’écraser les réglages manuels sans arrêt
if "last_loaded_date" not in st.session_state:
    st.session_state.last_loaded_date = None

# Initialisation des keys unit economics si absentes
for k, default_val in [
    ("revenu_pct", 3.8),
    ("cout_paiement_pct", 1.8),
    ("cout_liquidite_10j_pct", 0.55),
    ("defaut_30j_pct", 1.7),
    ("cycles_per_month", 2.9),
    ("loan_book_k", 100.0),
    ("avg_loan_value_eur", 300.0),
    ("tx_per_client_per_month", 2.9),
]:
    if k not in st.session_state:
        st.session_state[k] = default_val

# --------------------------------------------------
# HELPERS UI (barres + molettes)
# --------------------------------------------------
def _clamp(x, lo, hi):
    return max(lo, min(hi, x))

def rate_widget(label: str, key: str, vmin: float, vmax: float, step: float, help_txt: str = ""):
    """Taux : barre verticale + slider natif."""
    if key not in st.session_state:
        st.session_state[key] = (vmin + vmax) / 2

    val = float(st.session_state[key])
    pct = 0 if vmax == vmin else (val - vmin) / (vmax - vmin)
    pct = _clamp(pct, 0, 1)

    st.markdown(f"**{label}**")
    bar_html = f"""
    <div style="display:flex; align-items:center; gap:12px;">
      <div style="height:140px; width:14px; border-radius:10px; border:1px solid rgba(0,0,0,0.25); background:#f3f4f6; position:relative;">
        <div style="position:absolute; bottom:0; left:0; width:100%; height:{pct*100:.1f}%; border-radius:10px;
                    background: linear-gradient(180deg, rgba(6,76,114,0.95), rgba(248,49,49,0.90));">
        </div>
      </div>
      <div style="flex:1;">
        <div style="font-size:22px; font-weight:700; line-height:1;">{val:.2f}%</div>
        <div style="font-size:12px; opacity:0.7;">min {vmin:g}% • max {vmax:g}%</div>
      </div>
    </div>
    """
    st.markdown(bar_html, unsafe_allow_html=True)

    st.slider(
        label="",
        min_value=float(vmin),
        max_value=float(vmax),
        value=float(val),
        step=float(step),
        key=key,
        help=help_txt,
        label_visibility="collapsed",
    )

def dial_widget(label: str, key: str, vmin: float, vmax: float, step: float, suffix: str = "", help_txt: str = ""):
    """Volume : number_input + anneau (dial) en CSS."""
    if key not in st.session_state:
        st.session_state[key] = (vmin + vmax) / 2

    val = float(st.session_state[key])
    pct = 0 if vmax == vmin else (val - vmin) / (vmax - vmin)
    pct = _clamp(pct, 0, 1)

    st.markdown(f"**{label}**")
    dial_html = f"""
    <div style="display:flex; align-items:center; gap:14px; margin:6px 0 2px 0;">
      <div style="height:78px; width:78px; border-radius:50%;
                  background: conic-gradient(rgba(6,76,114,0.95) {pct*360:.1f}deg,
                                            rgba(0,0,0,0.10) 0deg);
                  display:flex; align-items:center; justify-content:center;
                  border:1px solid rgba(0,0,0,0.18);">
        <div style="height:54px; width:54px; border-radius:50%;
                    background:white; display:flex; align-items:center; justify-content:center;
                    font-weight:800; font-size:12px; color:#111;">
          {pct*100:.0f}%
        </div>
      </div>
      <div style="flex:1;">
        <div style="font-size:12px; opacity:0.75;">min {vmin:g} • max {vmax:g}</div>
      </div>
    </div>
    """
    st.markdown(dial_html, unsafe_allow_html=True)

    st.number_input(
        label="",
        min_value=float(vmin),
        max_value=float(vmax),
        value=float(val),
        step=float(step),
        key=key,
        help=help_txt,
        label_visibility="collapsed",
    )
    if suffix:
        st.caption(suffix)

def apply_preset_for_date(d: date, force: bool = False):
    """
    Applique le preset si la date correspond.
    - force=True : écrase les valeurs même si user a déjà touché.
    - force=False : ne réapplique que si on change de date (last_loaded_date).
    """
    if d not in PRESETS_BY_DATE:
        return

    if (not force) and (st.session_state.last_loaded_date == d):
        return

    preset = PRESETS_BY_DATE[d]
    st.session_state["revenu_pct"] = float(preset["revenu_pct"])
    st.session_state["cout_paiement_pct"] = float(preset["cout_paiement_pct"])
    st.session_state["cout_liquidite_10j_pct"] = float(preset["cout_liquidite_10j_pct"])
    st.session_state["defaut_30j_pct"] = float(preset["defaut_30j_pct"])
    st.session_state["scenario_name_autofill"] = preset.get("name", f"Preset – {d.isoformat()}")
    st.session_state.last_loaded_date = d

# --------------------------------------------------
# Seed historique (Jun 2025 + Dec 2025) une seule fois
# --------------------------------------------------
if "seeded_history" not in st.session_state:
    st.session_state.seeded_history = False

if not st.session_state.seeded_history:
    for d in [date(2025, 6, 1), date(2025, 12, 1)]:
        p = PRESETS_BY_DATE[d]
        st.session_state.scenarios.append(
            {
                "date": d,
                "name": p["name"],
                "revenu_pct": p["revenu_pct"],
                "cout_paiement_pct": p["cout_paiement_pct"],
                "cout_liquidite_10j_pct": p["cout_liquidite_10j_pct"],
                "defaut_30j_pct": p["defaut_30j_pct"],
            }
        )
    st.session_state.seeded_history = True

# Applique par défaut le preset de juin 2026 au chargement initial
apply_preset_for_date(st.session_state.scenario_date, force=False)

# --------------------------------------------------
# NAVIGATION
# --------------------------------------------------
page = st.sidebar.radio(
    "Navigation",
    ["Simulateur", "Comment je modélise une courbe ?"]
)

# ==================================================
# PAGE 2 : EXPLICATION
# ==================================================
if page == "Comment je modélise une courbe ?":
    st.title("Comment fonctionne le simulateur Waribei ?")

    st.markdown("""
Ce simulateur relie les **unit economics (par transaction)** à des **hypothèses de volume**
pour produire des métriques lisibles (revenus, contribution, volumes nécessaires).

- Les points **Jun 2025** et **Dec 2025** sont préchargés comme historique.
- Par défaut, l’interface se positionne sur **Jun 2026** avec des paramètres “target”.
- Si tu changes la date vers une date qui a un preset (Jun 2025 / Dec 2025 / Jun 2026),
  les valeurs se repositionnent automatiquement.
""")

# ==================================================
# PAGE 1 : SIMULATEUR
# ==================================================
else:
    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------
    top = st.columns([0.7, 0.3])
    with top[0]:
        st.title("Unit Economics – Waribei")

    with top[1]:
        try:
            st.image("logo_waribei_icon@2x.png", width=100)
        except Exception:
            st.write("Logo Waribei (ajoute `logo_waribei_icon@2x.png`)")

    st.markdown("---")

    # --------------------------------------------------
    # MAIN ZONE
    # --------------------------------------------------
    left, right = st.columns([0.62, 0.38])

    # --------------------------------------------------
    # LEFT : INPUTS (nouvelle UI type croquis)
    # --------------------------------------------------
    with left:
        st.subheader("Inputs")

        # ---- Scénarios rapides
        with st.container(border=True):
            c1, c2 = st.columns([0.55, 0.45])
            with c1:
                scenario = st.selectbox(
                    "Scénarios rapides",
                    [
                        "Custom",
                        "Aujourd'hui",
                        "Open Banking",
                        "Supplier funding",
                        "OB + Supplier (défaut bon 0,8%)",
                        "OB + Supplier (défaut moyen 1,2%)",
                        "OB + Supplier (défaut mauvais 2,0%)",
                    ],
                )
            with c2:
                st.caption("Choisis un scénario puis ajuste les curseurs.")

        # Mapping scénarios rapides (sans casser les presets date)
        if scenario == "Aujourd'hui":
            # Si tu veux : tu peux décider que "Aujourd'hui" = ton preset Jun 2026,
            # ou garder tes anciennes valeurs. Ici, je le mets sur Jun 2026.
            apply_preset_for_date(date(2026, 6, 1), force=True)

        elif scenario == "Open Banking":
            st.session_state["cout_paiement_pct"] = 0.5

        elif scenario == "Supplier funding":
            st.session_state["cout_liquidite_10j_pct"] = 0.055

        elif scenario == "OB + Supplier (défaut bon 0,8%)":
            st.session_state["cout_paiement_pct"] = 0.5
            st.session_state["cout_liquidite_10j_pct"] = 0.055
            st.session_state["defaut_30j_pct"] = 0.8

        elif scenario == "OB + Supplier (défaut moyen 1,2%)":
            st.session_state["cout_paiement_pct"] = 0.5
            st.session_state["cout_liquidite_10j_pct"] = 0.055
            st.session_state["defaut_30j_pct"] = 1.2

        elif scenario == "OB + Supplier (défaut mauvais 2,0%)":
            st.session_state["cout_paiement_pct"] = 0.5
            st.session_state["cout_liquidite_10j_pct"] = 0.055
            st.session_state["defaut_30j_pct"] = 2.0

        st.markdown("")

        # ---- Date (et presets)
        with st.container(border=True):
            dcols = st.columns([0.7, 0.3])
            with dcols[1]:
                if st.button("Today"):
                    st.session_state["scenario_date"] = DEFAULT_DATE
                    apply_preset_for_date(DEFAULT_DATE, force=True)

            with dcols[0]:
                picked = st.date_input(
                    "Date",
                    value=st.session_state.get("scenario_date", DEFAULT_DATE),
                )
                st.session_state["scenario_date"] = picked

            # Applique preset si la date match une date spéciale
            apply_preset_for_date(st.session_state["scenario_date"], force=False)

        st.markdown("")

        # =========================
        # 1) HYPOTHESES PAR TRANSACTION (barres)
        # =========================
        with st.container(border=True):
            st.markdown("### Hypothèses par transaction")

            r1, r2, r3, r4 = st.columns(4)

            with r1:
                rate_widget(
                    label="Revenus / trx",
                    key="revenu_pct",
                    vmin=1.0, vmax=5.0,
                    step=0.01,
                    help_txt="Take-rate / commission moyenne sur une transaction."
                )

            with r2:
                rate_widget(
                    label="Coût paiement / trx",
                    key="cout_paiement_pct",
                    vmin=0.0, vmax=2.0,
                    step=0.01,
                    help_txt="Coût PSP / wallet / rails de paiement."
                )

            with r3:
                rate_widget(
                    label="Coût liquidité (10j)",
                    key="cout_liquidite_10j_pct",
                    vmin=0.0, vmax=1.5,
                    step=0.01,
                    help_txt="Coût de financement sur 10 jours."
                )

            with r4:
                rate_widget(
                    label="Défaut 30j / trx",
                    key="defaut_30j_pct",
                    vmin=0.0, vmax=5.0,
                    step=0.01,
                    help_txt="Perte attendue (net) à 30 jours."
                )

        st.markdown("")

        # =========================
        # 2) VARIABLES DE VOLUME (molette + slider latéral)
        # =========================
        with st.container(border=True):
            st.markdown("### Variables de volume")

            vcol1, vcol2 = st.columns([0.55, 0.45], gap="large")

            with vcol1:
                dial_widget(
                    label="Loan book moyen (k€)",
                    key="loan_book_k",
                    vmin=50.0, vmax=1000.0,
                    step=10.0,
                    suffix="Encours moyen."
                )

            with vcol2:
                st.markdown("**Cycles de liquidité / mois**")
                st.caption("1 → 4")
                st.slider(
                    label="",
                    min_value=1.0,
                    max_value=4.0,
                    value=float(st.session_state.get("cycles_per_month", 2.9)),
                    step=0.1,
                    key="cycles_per_month",
                    label_visibility="collapsed",
                )

        st.markdown("")

        # =========================
        # 3) HYPOTHESES OPERATIONNELLES (molettes)
        # =========================
        with st.container(border=True):
            st.markdown("### Hypothèses opérationnelles")

            o1, o2 = st.columns(2, gap="large")

            with o1:
                dial_widget(
                    label="Valeur moyenne par prêt (€)",
                    key="avg_loan_value_eur",
                    vmin=150.0, vmax=1000.0,
                    step=50.0,
                    suffix="Panier moyen financé."
                )

            with o2:
                dial_widget(
                    label="Transactions / client / mois",
                    key="tx_per_client_per_month",
                    vmin=1.0, vmax=12.0,
                    step=0.5,
                    suffix="Rythme de réachat."
                )

        # ---- récupère les valeurs depuis le state (moteur inchangé)
        revenu_pct = float(st.session_state["revenu_pct"])
        cout_paiement_pct = float(st.session_state["cout_paiement_pct"])
        cout_liquidite_10j_pct = float(st.session_state["cout_liquidite_10j_pct"])
        defaut_30j_pct = float(st.session_state["defaut_30j_pct"])
        cycles_per_month = float(st.session_state["cycles_per_month"])
        loan_book_k = float(st.session_state["loan_book_k"])
        avg_loan_value_eur = float(st.session_state["avg_loan_value_eur"])
        tx_per_client_per_month = float(st.session_state["tx_per_client_per_month"])

        # --------------------------------------------------
        # CALCULS (inchangés)
        # --------------------------------------------------
        taux_liquidite_annuel_pct = cout_liquidite_10j_pct * 365 / DUREE_PERIODE_LIQUIDITE_JOURS

        cout_total_pct = cout_paiement_pct + cout_liquidite_10j_pct + defaut_30j_pct
        contribution_margin_pct = revenu_pct - cout_total_pct

        monthly_volume_eur = loan_book_k * 1000 * cycles_per_month
        monthly_revenue_eur = monthly_volume_eur * (revenu_pct / 100)
        annual_revenue_eur = monthly_revenue_eur * 12

        contribution_value_k = loan_book_k * cycles_per_month * contribution_margin_pct / 100

        nb_loans_per_month = monthly_volume_eur / avg_loan_value_eur if avg_loan_value_eur > 0 else 0.0
        nb_clients_per_month = nb_loans_per_month / tx_per_client_per_month if tx_per_client_per_month > 0 else 0.0

        revenue_per_loan_eur = avg_loan_value_eur * (revenu_pct / 100)
        revenue_per_client_month_eur = revenue_per_loan_eur * tx_per_client_per_month

        take_rate_effective_pct = (monthly_revenue_eur / monthly_volume_eur * 100) if monthly_volume_eur > 0 else 0.0

        st.caption(f"Coût de liquidité annualisé ≈ **{taux_liquidite_annuel_pct:.1f} %**")

    # --------------------------------------------------
    # RIGHT : OUTPUTS
    # --------------------------------------------------
    with right:
        st.subheader("Contribution")

        st.markdown("Contribution margin / trx")
        st.markdown(
            f"""
            <div style="
                border:2px solid #064C72;
                padding:16px;
                border-radius:10px;
                font-size:28px;
                font-weight:800;
                text-align:center;
                background-color:#FFDBCC;
                color:#064C72;">
                {contribution_margin_pct:.2f} %
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("")

        st.markdown("Contribution value / mois")
        st.markdown(
            f"""
            <div style="
                border:2px solid #1B5A43;
                padding:14px;
                border-radius:10px;
                font-size:22px;
                font-weight:800;
                text-align:center;
                background-color:#D8ECFE;
                color:#1B5A43;">
                {contribution_value_k:.2f} k€
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            f"Hypothèses : loan book moyen {loan_book_k:.0f} k€, "
            f"{cycles_per_month:.1f} cycles / mois."
        )

        st.markdown("")

        st.subheader("Revenus")

        r1, r2 = st.columns(2)
        with r1:
            st.markdown(
                f"""
                <div style="border:1px solid #DDD;padding:10px;border-radius:10px;font-size:18px;font-weight:700;text-align:center;">
                    {monthly_revenue_eur:,.0f} €<br/>
                    <span style="font-size:13px;font-weight:400;opacity:0.75;">Revenue / mois</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with r2:
            st.markdown(
                f"""
                <div style="border:1px solid #DDD;padding:10px;border-radius:10px;font-size:18px;font-weight:700;text-align:center;">
                    {annual_revenue_eur:,.0f} €<br/>
                    <span style="font-size:13px;font-weight:400;opacity:0.75;">Revenue / an</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        r3, r4 = st.columns(2)
        with r3:
            st.markdown(
                f"""
                <div style="border:1px solid #DDD;padding:10px;border-radius:10px;font-size:18px;font-weight:700;text-align:center;">
                    {revenue_per_loan_eur:,.0f} €<br/>
                    <span style="font-size:13px;font-weight:400;opacity:0.75;">Revenue / prêt</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with r4:
            st.markdown(
                f"""
                <div style="border:1px solid #DDD;padding:10px;border-radius:10px;font-size:18px;font-weight:700;text-align:center;">
                    {revenue_per_client_month_eur:,.0f} €<br/>
                    <span style="font-size:13px;font-weight:400;opacity:0.75;">Revenue / client / mois</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.caption(
            f"Take-rate effectif ≈ {take_rate_effective_pct:.2f} % "
            f"sur un volume mensuel de {monthly_volume_eur:,.0f} €."
        )

        st.markdown("")
        st.markdown("**Volumes nécessaires / mois**")

        m1, m2 = st.columns(2)
        with m1:
            st.markdown(
                f"""
                <div style="border:1px solid #DDD;padding:10px;border-radius:10px;font-size:18px;font-weight:700;text-align:center;">
                    {nb_loans_per_month:,.0f}<br/>
                    <span style="font-size:13px;font-weight:400;opacity:0.75;">prêts / mois</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m2:
            st.markdown(
                f"""
                <div style="border:1px solid #DDD;padding:10px;border-radius:10px;font-size:18px;font-weight:700;text-align:center;">
                    {nb_clients_per_month:,.0f}<br/>
                    <span style="font-size:13px;font-weight:400;opacity:0.75;">clients / mois</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.caption(
            f"Basé sur {avg_loan_value_eur:.0f} € par prêt et {tx_per_client_per_month:.1f} transactions / client / mois."
        )

        st.markdown("")

        # ---- SAVE scenario (avec autofill du label si preset)
        default_label = st.session_state.get("scenario_name_autofill", "Scenario")
        scenario_name = st.text_input("Label du scénario", value=default_label)

        if st.button("SAVE"):
            scenario_obj = {
                "date": st.session_state["scenario_date"],
                "name": scenario_name,
                "revenu_pct": revenu_pct,
                "cout_paiement_pct": cout_paiement_pct,
                "cout_liquidite_10j_pct": cout_liquidite_10j_pct,
                "defaut_30j_pct": defaut_30j_pct,
                "taux_liquidite_annuel_pct": taux_liquidite_annuel_pct,
                "contribution_margin_pct": contribution_margin_pct,
                "cycles_per_month": cycles_per_month,
                "loan_book_k": loan_book_k,
                "contribution_value_k": contribution_value_k,
                "avg_loan_value_eur": avg_loan_value_eur,
                "tx_per_client_per_month": tx_per_client_per_month,
                "nb_loans_per_month": nb_loans_per_month,
                "nb_clients_per_month": nb_clients_per_month,
                "monthly_volume_eur": monthly_volume_eur,
                "monthly_revenue_eur": monthly_revenue_eur,
                "annual_revenue_eur": annual_revenue_eur,
                "revenue_per_loan_eur": revenue_per_loan_eur,
                "revenue_per_client_month_eur": revenue_per_client_month_eur,
                "take_rate_effective_pct": take_rate_effective_pct,
            }
            st.session_state.scenarios.append(scenario_obj)
            if st.session_state.baseline is None:
                st.session_state.baseline = scenario_obj
            st.success(f"Scénario '{scenario_name}' sauvegardé ({st.session_state['scenario_date']}).")

    st.markdown("---")

    # --------------------------------------------------
    # WATERFALL DATA PREP
    # --------------------------------------------------
    def make_waterfall_df(revenue, pay_cost, liq_cost, default_cost, margin):
        steps = ["Revenu", "Coût paiement", "Coût liquidité (10j)", "Défaut 30j", "Contribution"]
        values = [revenue, -pay_cost, -liq_cost, -default_cost, margin]

        start, end = [], []
        running = 0.0
        for v in values[:-1]:
            start.append(running)
            running += v
            end.append(running)

        start.append(0.0)
        end.append(margin)

        types = []
        for i, v in enumerate(values):
            if i == len(values) - 1:
                types.append("total")
            elif v >= 0:
                types.append("positive")
            else:
                types.append("negative")

        return pd.DataFrame({"step": steps, "value": values, "start": start, "end": end, "type": types})

    # --------------------------------------------------
    # WATERFALL CHART
    # --------------------------------------------------
    st.markdown("### Décomposition par transaction (waterfall)")

    wf_df = make_waterfall_df(
        revenu_pct,
        cout_paiement_pct,
        cout_liquidite_10j_pct,
        defaut_30j_pct,
        contribution_margin_pct
    )

    color_scale = alt.Scale(
        domain=["positive", "negative", "total"],
        range=["#1B5A43", "#F83131", "#064C72"],
    )

    waterfall_chart = (
        alt.Chart(wf_df)
        .mark_bar()
        .encode(
            x=alt.X("step:N", title=None, sort=list(wf_df["step"])),
            y=alt.Y("start:Q", axis=alt.Axis(title="%")),
            y2="end:Q",
            color=alt.Color("type:N", scale=color_scale, legend=None),
        )
    )

    wf_labels = (
        alt.Chart(wf_df)
        .mark_text(dy=-6, color="#333", fontSize=11)
        .encode(
            x=alt.X("step:N", sort=list(wf_df["step"])),
            y="end:Q",
            text=alt.Text("value:Q", format=".2f"),
        )
    )

    st.altair_chart((waterfall_chart + wf_labels).properties(height=260), use_container_width=True)

    # --------------------------------------------------
    # TIME SERIES CHART (inclut l’historique préchargé)
    # --------------------------------------------------
    st.markdown("### Évolution dans le temps")

    if st.session_state.scenarios:
        df_scenarios = pd.DataFrame(st.session_state.scenarios).sort_values("date")

        # Si certains anciens scénarios n'ont pas toutes les colonnes (seed historique),
        # on calcule contribution_margin_pct à la volée si manquante
        if "contribution_margin_pct" not in df_scenarios.columns:
            df_scenarios["contribution_margin_pct"] = (
                df_scenarios["revenu_pct"]
                - (df_scenarios["cout_paiement_pct"] + df_scenarios["cout_liquidite_10j_pct"] + df_scenarios["defaut_30j_pct"])
            )
        else:
            # fill NaN contribution_margin_pct
            mask = df_scenarios["contribution_margin_pct"].isna()
            if mask.any():
                df_scenarios.loc[mask, "contribution_margin_pct"] = (
                    df_scenarios.loc[mask, "revenu_pct"]
                    - (
                        df_scenarios.loc[mask, "cout_paiement_pct"]
                        + df_scenarios.loc[mask, "cout_liquidite_10j_pct"]
                        + df_scenarios.loc[mask, "defaut_30j_pct"]
                    )
                )

        line_df = df_scenarios[
            ["date", "revenu_pct", "cout_paiement_pct", "cout_liquidite_10j_pct", "defaut_30j_pct", "contribution_margin_pct"]
        ].melt(id_vars="date", var_name="metric", value_name="value")

        metric_order = [
            "revenu_pct",
            "cout_paiement_pct",
            "cout_liquidite_10j_pct",
            "defaut_30j_pct",
            "contribution_margin_pct",
        ]

        color_line = alt.Scale(
            domain=metric_order,
            range=["#1B5A43", "#F83131", "#8ECAE6", "#FFC444", "#064C72"],
        )

        line_chart = (
            alt.Chart(line_df)
            .mark_line(point=True)
            .encode(
                x=alt.X("date:T", title="Date"),
                y=alt.Y("value:Q", title="%"),
                color=alt.Color("metric:N", scale=color_line, title="Métrique"),
            )
            .properties(height=260)
        )

        st.altair_chart(line_chart, use_container_width=True)

        st.markdown("#### Scénarios enregistrés")
        st.dataframe(df_scenarios, use_container_width=True)

        labels = [f"{row.date} – {row.name}" for _, row in df_scenarios.reset_index(drop=True).iterrows()]
        to_delete = st.multiselect("Supprimer des scénarios", labels)

        if st.button("Delete"):
            new_list = []
            for scen, label in zip(df_scenarios.to_dict("records"), labels):
                if label not in to_delete:
                    new_list.append(scen)
            st.session_state.scenarios = new_list
            st.success("Scénarios mis à jour.")
    else:
        st.info("Aucun scénario sauvegardé pour l'instant. Utilise le bouton SAVE.")
