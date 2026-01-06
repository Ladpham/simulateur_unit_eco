import streamlit as st
import pandas as pd
import altair as alt
from datetime import date

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
st.set_page_config(page_title="Waribei – Unit Economics", layout="wide")
DUREE_PERIODE_LIQUIDITE_JOURS = 10

# --------------------------------------------------
# PRESETS (historique + défaut)
# --------------------------------------------------
PRESETS_BY_DATE = {
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
if "scenario_date" not in st.session_state:
    st.session_state.scenario_date = DEFAULT_DATE
if "last_loaded_date" not in st.session_state:
    st.session_state.last_loaded_date = None

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

def apply_preset_for_date(d: date, force: bool = False):
    if d not in PRESETS_BY_DATE:
        return
    if (not force) and (st.session_state.last_loaded_date == d):
        return

    p = PRESETS_BY_DATE[d]
    st.session_state["revenu_pct"] = float(p["revenu_pct"])
    st.session_state["cout_paiement_pct"] = float(p["cout_paiement_pct"])
    st.session_state["cout_liquidite_10j_pct"] = float(p["cout_liquidite_10j_pct"])
    st.session_state["defaut_30j_pct"] = float(p["defaut_30j_pct"])
    st.session_state["scenario_name_autofill"] = p.get("name", f"Preset – {d.isoformat()}")
    st.session_state.last_loaded_date = d

# Seed historique (une seule fois)
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

apply_preset_for_date(st.session_state.scenario_date, force=False)

# --------------------------------------------------
# GLOBAL CSS (look & feel)
# --------------------------------------------------
st.markdown("""
<style>
/* Enlève un peu de bruit visuel */
div.block-container { padding-top: 1.2rem; }
h1, h2, h3 { letter-spacing: -0.02em; }

/* Carte */
.wb-card {
  border: 1px solid rgba(0,0,0,0.10);
  border-radius: 14px;
  padding: 14px 14px 12px 14px;
  background: rgba(255,255,255,0.70);
}

/* Barre verticale visuelle */
.vbar-wrap { display:flex; align-items:center; gap:12px; }
.vbar {
  height: 168px;
  width: 16px;
  border-radius: 14px;
  border: 1px solid rgba(0,0,0,0.18);
  background: rgba(0,0,0,0.06);
  position: relative;
  overflow: hidden;
}
.vbar-fill {
  position:absolute;
  bottom:0;
  left:0;
  width:100%;
  border-radius: 14px;
}

/* Valeur à droite de la barre */
.vbar-metric {
  display:flex;
  flex-direction:column;
  gap:2px;
}
.vbar-metric .big { font-size: 22px; font-weight: 800; line-height: 1; }
.vbar-metric .sub { font-size: 12px; opacity: 0.7; }

/* Molette visuelle */
.knob-wrap { display:flex; align-items:center; gap:14px; }
.knob {
  height: 96px;
  width: 96px;
  border-radius: 50%;
  position: relative;
  background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.35), rgba(0,0,0,0.25));
  box-shadow: 0px 10px 22px rgba(0,0,0,0.25);
  border: 1px solid rgba(0,0,0,0.25);
}
.knob::after{
  content:"";
  position:absolute;
  inset: 12px;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, rgba(255,255,255,0.40), rgba(0,0,0,0.20));
  border: 1px solid rgba(0,0,0,0.25);
}
.knob-dot{
  position:absolute;
  height:10px; width:10px;
  border-radius:50%;
  background: rgba(255,255,255,0.85);
  box-shadow: 0 0 10px rgba(255,255,255,0.55);
  top: 26px; left: 28px;
  z-index: 3;
}
.knob-arc{
  position:absolute;
  inset:-14px;
  border-radius:50%;
  border: 6px dashed rgba(0,0,0,0.35);
  clip-path: inset(0 0 0 0 round 50%);
  z-index: 1;
}
.knob-progress{
  position:absolute;
  inset:-14px;
  border-radius:50%;
  border: 6px dashed rgba(255,255,255,0.85);
  clip-path: inset(0 0 0 0 round 50%);
  filter: drop-shadow(0 0 6px rgba(255,255,255,0.35));
  z-index: 2;
}

/* Petit label */
.small-label { font-size: 12px; opacity: 0.7; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

def _clamp(x, lo, hi):
    return max(lo, min(hi, x))

def vbar_widget(
    label: str,
    key: str,
    vmin: float,
    vmax: float,
    step: float,
    help_txt: str,
    color_mode: str,
):
    """
    Barre verticale VISUELLE + input Streamlit (en dessous).
    color_mode:
      - "rev": haut vert / bas rouge
      - "cost": haut rouge / bas vert
    """
    if key not in st.session_state:
        st.session_state[key] = (vmin + vmax) / 2

    val = float(st.session_state[key])
    pct = 0 if vmax == vmin else (val - vmin) / (vmax - vmin)
    pct = _clamp(pct, 0, 1)

    if color_mode == "rev":
        # haut vert, bas rouge (donc fill = gradient bas->haut rouge->vert)
        grad = "linear-gradient(180deg, rgba(34,197,94,0.95), rgba(239,68,68,0.95))"
        # mais comme fill part du bas, on inverse pour que bas rouge -> haut vert
        grad = "linear-gradient(180deg, rgba(239,68,68,0.95), rgba(34,197,94,0.95))"
    else:
        # haut rouge, bas vert
        grad = "linear-gradient(180deg, rgba(34,197,94,0.95), rgba(239,68,68,0.95))"

    st.markdown(f"**{label}**")
    st.markdown(
        f"""
        <div class="vbar-wrap">
          <div class="vbar">
            <div class="vbar-fill" style="height:{pct*100:.1f}%; background:{grad};"></div>
          </div>
          <div class="vbar-metric">
            <div class="big">{val:.2f}%</div>
            <div class="sub">min {vmin:g}% • max {vmax:g}%</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ⚠️ Limitation Streamlit : pas de drag directement dans la barre sans composant custom.
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

def knob_visual(label: str, value: float, vmin: float, vmax: float):
    pct = 0 if vmax == vmin else (value - vmin) / (vmax - vmin)
    pct = _clamp(pct, 0, 1)
    # arc ~ 270° (de -225° à +45°)
    deg = -225 + pct * 270

    # Trick: on simule un "progress" arc en tournant un dashed ring (visuel)
    st.markdown(f"**{label}**")
    st.markdown(
        f"""
        <div class="knob-wrap">
          <div style="position:relative; width:110px; height:110px;">
            <div class="knob-arc"></div>
            <div class="knob-progress" style="transform: rotate({deg}deg);"></div>
            <div class="knob">
              <div class="knob-dot"></div>
            </div>
          </div>
          <div style="display:flex; flex-direction:column; gap:2px;">
            <div style="font-size:22px; font-weight:800; line-height:1;">{value:,.0f}</div>
            <div style="font-size:12px; opacity:0.7;">min {vmin:g} • max {vmax:g}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# --------------------------------------------------
# NAVIGATION
# --------------------------------------------------
page = st.sidebar.radio("Navigation", ["Simulateur", "Comment je modélise une courbe ?"])

# ==================================================
# PAGE 2 : EXPLICATION
# ==================================================
if page == "Comment je modélise une courbe ?":
    st.title("Comment fonctionne le simulateur Waribei ?")
    st.markdown("""
- Historique préchargé : **Jun 2025** et **Dec 2025**
- Par défaut : **Jun 2026** avec tes valeurs target
- Si tu changes la date vers une date “preset”, les valeurs se repositionnent automatiquement.
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
    # LAYOUT PRINCIPAL
    # On veut voir en premier:
    #  - Hypothèses par transaction
    #  - Variables de volume
    # Et on déplace Inputs + Scénarios rapides + Date en bas à droite
    # --------------------------------------------------
    main_left, main_right = st.columns([0.68, 0.32], gap="large")

    # =========================
    # MAIN LEFT : Hypothèses par transaction
    # =========================
    with main_left:
        st.markdown('<div class="wb-card">', unsafe_allow_html=True)
        st.subheader("Hypothèses par transaction")

        c1, c2, c3, c4 = st.columns(4, gap="large")
        with c1:
            vbar_widget(
                "Revenus / trx",
                key="revenu_pct",
                vmin=1.0, vmax=5.0, step=0.01,
                help_txt="Take-rate / commission moyenne.",
                color_mode="rev",   # vert en haut, rouge en bas
            )
        with c2:
            vbar_widget(
                "Coût paiement / trx",
                key="cout_paiement_pct",
                vmin=0.0, vmax=2.0, step=0.01,
                help_txt="Coût des rails de paiement.",
                color_mode="cost",  # rouge en haut, vert en bas
            )
        with c3:
            vbar_widget(
                "Coût liquidité (10j)",
                key="cout_liquidite_10j_pct",
                vmin=0.0, vmax=1.5, step=0.01,
                help_txt="Coût de financement sur 10 jours.",
                color_mode="cost",
            )
        with c4:
            vbar_widget(
                "Défaut 30j / trx",
                key="defaut_30j_pct",
                vmin=0.0, vmax=5.0, step=0.01,
                help_txt="Perte attendue (net) à 30 jours.",
                color_mode="cost",
            )

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("")

        # =========================
        # Variables de volume + opérationnel (on peut les mettre sous le bloc principal)
        # =========================
        st.markdown('<div class="wb-card">', unsafe_allow_html=True)
        st.subheader("Variables de volume")

        vcol1, vcol2 = st.columns([0.58, 0.42], gap="large")

        with vcol1:
            # Loan book : molette VISUELLE + input
            knob_visual("Loan book moyen (k€)", float(st.session_state["loan_book_k"]), 50.0, 1000.0)
            st.number_input(
                label="",
                min_value=50.0,
                max_value=1000.0,
                step=10.0,
                value=float(st.session_state["loan_book_k"]),
                key="loan_book_k",
                label_visibility="collapsed",
            )
            st.caption("Encours moyen.")

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

        st.markdown("</div>", unsafe_allow_html=True)

    # =========================
    # MAIN RIGHT : Outputs + petit panneau Inputs en bas
    # =========================
    with main_right:
        # ------- CALCULS (moteur inchangé)
        revenu_pct = float(st.session_state["revenu_pct"])
        cout_paiement_pct = float(st.session_state["cout_paiement_pct"])
        cout_liquidite_10j_pct = float(st.session_state["cout_liquidite_10j_pct"])
        defaut_30j_pct = float(st.session_state["defaut_30j_pct"])
        cycles_per_month = float(st.session_state["cycles_per_month"])
        loan_book_k = float(st.session_state["loan_book_k"])
        avg_loan_value_eur = float(st.session_state["avg_loan_value_eur"])
        tx_per_client_per_month = float(st.session_state["tx_per_client_per_month"])

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

        # ------- OUTPUTS
        st.subheader("Contribution")

        st.markdown(
            f"""
            <div style="border:2px solid #064C72; padding:16px; border-radius:12px;
                        font-size:28px; font-weight:900; text-align:center;
                        background-color:#FFDBCC; color:#064C72;">
              {contribution_margin_pct:.2f} %
              <div class="small-label">Contribution margin / trx</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("")

        st.markdown(
            f"""
            <div style="border:2px solid #1B5A43; padding:14px; border-radius:12px;
                        font-size:22px; font-weight:900; text-align:center;
                        background-color:#D8ECFE; color:#1B5A43;">
              {contribution_value_k:.2f} k€
              <div class="small-label">Contribution value / mois</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.caption(f"Coût de liquidité annualisé ≈ **{taux_liquidite_annuel_pct:.1f}%**")

        st.markdown("")

        st.subheader("Revenus")
        r1, r2 = st.columns(2)
        with r1:
            st.metric("Revenue / mois", f"{monthly_revenue_eur:,.0f} €")
        with r2:
            st.metric("Revenue / an", f"{annual_revenue_eur:,.0f} €")

        r3, r4 = st.columns(2)
        with r3:
            st.metric("Revenue / prêt", f"{revenue_per_loan_eur:,.0f} €")
        with r4:
            st.metric("Revenue / client / mois", f"{revenue_per_client_month_eur:,.0f} €")

        st.caption(f"Take-rate effectif ≈ {take_rate_effective_pct:.2f}% sur {monthly_volume_eur:,.0f} € / mois.")

        st.markdown("")

        st.subheader("Volumes nécessaires / mois")
        m1, m2 = st.columns(2)
        with m1:
            st.metric("Prêts / mois", f"{nb_loans_per_month:,.0f}")
        with m2:
            st.metric("Clients / mois", f"{nb_clients_per_month:,.0f}")

        st.markdown("---")

        # =========================
        # PANEL BAS DROITE : Inputs + Scénarios rapides + Date
        # =========================
        st.markdown('<div class="wb-card">', unsafe_allow_html=True)
        st.markdown("### Inputs")

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
        st.caption("Choisis un scénario puis ajuste les curseurs.")

        if scenario == "Aujourd'hui":
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

        dcols = st.columns([0.72, 0.28])
        with dcols[1]:
            if st.button("Today"):
                st.session_state["scenario_date"] = DEFAULT_DATE
                apply_preset_for_date(DEFAULT_DATE, force=True)
        with dcols[0]:
            picked = st.date_input("Date", value=st.session_state.get("scenario_date", DEFAULT_DATE))
            st.session_state["scenario_date"] = picked

        apply_preset_for_date(st.session_state["scenario_date"], force=False)

        default_label = st.session_state.get("scenario_name_autofill", "Scenario")
        scenario_name = st.text_input("Label du scénario", value=default_label)

        if st.button("SAVE"):
            scenario_obj = {
                "date": st.session_state["scenario_date"],
                "name": scenario_name,
                "revenu_pct": float(st.session_state["revenu_pct"]),
                "cout_paiement_pct": float(st.session_state["cout_paiement_pct"]),
                "cout_liquidite_10j_pct": float(st.session_state["cout_liquidite_10j_pct"]),
                "defaut_30j_pct": float(st.session_state["defaut_30j_pct"]),
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

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # --------------------------------------------------
    # WATERFALL
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

    st.markdown("### Décomposition par transaction (waterfall)")
    wf_df = make_waterfall_df(
        float(st.session_state["revenu_pct"]),
        float(st.session_state["cout_paiement_pct"]),
        float(st.session_state["cout_liquidite_10j_pct"]),
        float(st.session_state["defaut_30j_pct"]),
        float(st.session_state["revenu_pct"]) - (
            float(st.session_state["cout_paiement_pct"]) +
            float(st.session_state["cout_liquidite_10j_pct"]) +
            float(st.session_state["defaut_30j_pct"])
        )
    )

    color_scale = alt.Scale(domain=["positive", "negative", "total"], range=["#1B5A43", "#F83131", "#064C72"])
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
    # TIME SERIES
    # --------------------------------------------------
    st.markdown("### Évolution dans le temps")

    if st.session_state.scenarios:
        df_scenarios = pd.DataFrame(st.session_state.scenarios).sort_values("date")

        if "contribution_margin_pct" not in df_scenarios.columns:
            df_scenarios["contribution_margin_pct"] = (
                df_scenarios["revenu_pct"]
                - (df_scenarios["cout_paiement_pct"] + df_scenarios["cout_liquidite_10j_pct"] + df_scenarios["defaut_30j_pct"])
            )
        else:
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

        metric_order = ["revenu_pct", "cout_paiement_pct", "cout_liquidite_10j_pct", "defaut_30j_pct", "contribution_margin_pct"]
        color_line = alt.Scale(domain=metric_order, range=["#1B5A43", "#F83131", "#8ECAE6", "#FFC444", "#064C72"])

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
