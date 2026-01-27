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

HISTORY_DATES = [date(2025, 6, 1), date(2025, 12, 1), date(2026, 6, 1)]

# --------------------------------------------------
# SCÉNARIOS RAPIDES (hard-coded)
# --------------------------------------------------
SCENARIOS_PRESETS = {
    "Custom": None,

    "Base scénario — Aujourd’hui": {
        "revenu_pct": 3.80,
        "cout_paiement_pct": 1.60,
        "cout_liquidite_10j_pct": 0.40,
        "defaut_30j_pct": 1.00,
        "loan_book_k": 800.0,
        "cycles_per_month": 2.9,
        # optionnel: si tu veux aussi pré-remplir
        "scenario_name_autofill": "Base scénario — Aujourd’hui",
    },

    "Scénario 1 — Optimisation légère": {
        "revenu_pct": 3.80,
        "cout_paiement_pct": 1.20,
        "cout_liquidite_10j_pct": 0.40,
        "defaut_30j_pct": 1.00,
        "loan_book_k": 530.0,
        "cycles_per_month": 2.9,
        "scenario_name_autofill": "Scénario 1 — Optimisation légère",
    },

    "Scénario 2 — Open Banking": {
        "revenu_pct": 3.80,
        "cout_paiement_pct": 0.50,
        "cout_liquidite_10j_pct": 0.40,
        "defaut_30j_pct": 0.62,
        "loan_book_k": 280.0,
        "cycles_per_month": 3.0,
        "scenario_name_autofill": "Scénario 2 — Open Banking",
    },

    "Scénario 3 — Tenure 15j + OB": {
        "revenu_pct": 4.00,
        "cout_paiement_pct": 0.50,
        # NOTE: tu as mis 0.50% ici (vs 0.40% dans les autres) -> je respecte ton tableau.
        # Si tu veux modéliser le 15j proprement, il faudrait ajuster via DUREE_PERIODE_LIQUIDITE_JOURS.
        "cout_liquidite_10j_pct": 0.50,
        "defaut_30j_pct": 0.65,
        "loan_book_k": 290.0,
        "cycles_per_month": 2.7,
        "scenario_name_autofill": "Scénario 3 — Tenure 15j + OB",
    },

    "Scénario Seed": {
        "revenu_pct": 3.77,
        "cout_paiement_pct": 1.38,
        "cout_liquidite_10j_pct": 0.34,
        "defaut_30j_pct": 1.26,
        # ton tableau n’a pas donné loan_book/cycles pour Seed -> je laisse volontairement inchangé
        "loan_book_k": 294.0,
        "cycles_per_month": 3.3,
        "scenario_name_autofill": "Scénario Seed",
    },
}


def apply_scenario_preset(name: str):
    """Applique un scénario hard-coded (trx + volume si présent). Doit être appelé AVANT la création des widgets."""
    preset = SCENARIOS_PRESETS.get(name)
    if not preset:
        return

    # On n'applique que des clés connues (évite d'écraser des trucs inattendus)
    allowed = {
        "revenu_pct",
        "cout_paiement_pct",
        "cout_liquidite_10j_pct",
        "defaut_30j_pct",
        "loan_book_k",
        "cycles_per_month",
        "scenario_name_autofill",
    }

    for k, v in preset.items():
        if k not in allowed:
            continue
        st.session_state[k] = v


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
    ("loan_book_k", 300.0),
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


# Seed historique (uniquement les dates demandées)
if "seeded_history" not in st.session_state:
    st.session_state.seeded_history = False

if not st.session_state.seeded_history:
    for d in HISTORY_DATES:
        p = PRESETS_BY_DATE[d]
        # on stocke aussi contribution_margin_pct pour simplifier la courbe
        cm = p["revenu_pct"] - (p["cout_paiement_pct"] + p["cout_liquidite_10j_pct"] + p["defaut_30j_pct"])
        st.session_state.scenarios.append(
            {
                "date": d,
                "name": p["name"],
                "contribution_margin_pct": cm,
            }
        )
    st.session_state.seeded_history = True

apply_preset_for_date(st.session_state.scenario_date, force=False)

# --------------------------------------------------
# GLOBAL CSS
# --------------------------------------------------
st.markdown(
    """
<style>
div.block-container { padding-top: 1.2rem; }
h1, h2, h3 { letter-spacing: -0.02em; }

.wb-card {
  border: 1px solid rgba(0,0,0,0.10);
  border-radius: 14px;
  padding: 14px 14px 12px 14px;
  background: rgba(255,255,255,0.70);
}

/* Vertical bar */
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
.vbar-metric { display:flex; flex-direction:column; gap:2px; }
.vbar-metric .big { font-size: 22px; font-weight: 800; line-height: 1; }
.vbar-metric .sub { font-size: 12px; opacity: 0.7; }

/* Simple knob like sketch */
.knob-wrap { display:flex; align-items:center; gap:12px; }
.knob-shell { width: 110px; height: 110px; position: relative; }
.knob-ring {
  width: 90px; height: 90px;
  border-radius: 50%;
  border: 3px solid rgba(0,0,0,0.55);
  position:absolute; left:10px; top:10px;
  background: rgba(255,255,255,0.15);
}
.knob-ticks {
  position:absolute; inset:0;
  border-radius: 50%;
  border: 6px dotted rgba(0,0,0,0.25);
  clip-path: inset(0 0 0 0 round 50%);
  opacity: 0.9;
}
.knob-needle {
  position:absolute;
  width: 6px; height: 44px;
  background: rgba(6,76,114,0.95);
  left: 52px; top: 14px;
  transform-origin: 50% 85%;
  border-radius: 4px;
  box-shadow: 0 0 0 1px rgba(0,0,0,0.08);
}
.small-label { font-size: 12px; opacity: 0.7; margin-top: 4px; }
</style>
""",
    unsafe_allow_html=True,
)


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def vbar_widget(label: str, key: str, vmin: float, vmax: float, step: float, help_txt: str, color_mode: str):
    """
    Barre verticale VISUELLE + slider Streamlit.
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
        # bottom red -> top green
        grad = "linear-gradient(180deg, rgba(34,197,94,0.95), rgba(239,68,68,0.95))"
    else:
        # bottom green -> top red
        grad = "linear-gradient(180deg, rgba(239,68,68,0.95), rgba(34,197,94,0.95))"

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


def knob_simple_visual(label: str, value: float, vmin: float, vmax: float, value_fmt: str = "{:,.0f}"):
    pct = 0 if vmax == vmin else (value - vmin) / (vmax - vmin)
    pct = _clamp(pct, 0, 1)
    deg = -135 + pct * 270  # -135° à +135°

    st.markdown(f"**{label}**")
    st.markdown(
        f"""
        <div class="knob-wrap">
          <div class="knob-shell">
            <div class="knob-ticks"></div>
            <div class="knob-ring"></div>
            <div class="knob-needle" style="transform: rotate({deg:.1f}deg);"></div>
          </div>
          <div style="display:flex; flex-direction:column; gap:2px;">
            <div style="font-size:22px; font-weight:800; line-height:1;">{value_fmt.format(value)}</div>
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
# PAGE 2
# ==================================================
if page == "Comment je modélise une courbe ?":
    st.title("Comment fonctionne le simulateur Waribei ?")
    st.markdown(
        """
- Historique: **Jun 2025**, **Dec 2025**, **Jun 2026**
- Courbe "Évolution dans le temps" : uniquement **contribution_margin_pct**
"""
    )

# ==================================================
# PAGE 1
# ==================================================
else:
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
    # APPLY PENDING SCENARIO (avant widgets)
    # --------------------------------------------------
    if "pending_scenario" in st.session_state and st.session_state.pending_scenario:
        apply_scenario_preset(st.session_state.pending_scenario)
        # important : on consomme l'action pour éviter de ré-appliquer à chaque rerun
        st.session_state.pending_scenario = None

    
    main_left, main_right = st.columns([0.68, 0.32], gap="large")

    # =========================
    # LEFT: Hypothèses par transaction + Volume + Opérationnel
    # =========================
    with main_left:
        # ---- Hypothèses par transaction
        st.markdown('<div class="wb-card">', unsafe_allow_html=True)
        st.subheader("Hypothèses par transaction")

        c1, c2, c3, c4 = st.columns(4, gap="large")
        with c1:
            vbar_widget("Revenus / trx", "revenu_pct", 1.0, 5.0, 0.01, "Take-rate / commission moyenne.", "rev")
        with c2:
            vbar_widget("Coût paiement / trx", "cout_paiement_pct", 0.0, 2.0, 0.01, "Coût des rails de paiement.", "cost")
        with c3:
            vbar_widget("Coût liquidité (10j)", "cout_liquidite_10j_pct", 0.0, 1.5, 0.01, "Coût de financement sur 10 jours.", "cost")
        with c4:
            vbar_widget("Défaut 30j / trx", "defaut_30j_pct", 0.0, 5.0, 0.01, "Perte attendue (net) à 30 jours.", "cost")

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("")

        # ---- Variables de volume
        st.markdown('<div class="wb-card">', unsafe_allow_html=True)
        st.subheader("Variables de volume")

        vcol1, vcol2 = st.columns([0.58, 0.42], gap="large")
        with vcol1:
            knob_simple_visual("Loan book moyen (k€)", float(st.session_state["loan_book_k"]), 50.0, 1000.0)
            # ✅ Slider en dessous de la molette
            st.slider(
                label="",
                min_value=50.0,
                max_value=1000.0,
                value=float(st.session_state["loan_book_k"]),
                step=10.0,
                key="loan_book_k",
                label_visibility="collapsed",
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

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("")

        # ---- Hypothèses opérationnelles
        st.markdown('<div class="wb-card">', unsafe_allow_html=True)
        st.subheader("Hypothèses opérationnelles")

        o1, o2 = st.columns(2, gap="large")

        with o1:
            knob_simple_visual("Valeur moyenne par prêt (€)", float(st.session_state["avg_loan_value_eur"]), 150.0, 1000.0)
            # ✅ Slider en dessous de la molette
            st.slider(
                label="",
                min_value=150.0,
                max_value=1000.0,
                value=float(st.session_state["avg_loan_value_eur"]),
                step=50.0,
                key="avg_loan_value_eur",
                label_visibility="collapsed",
            )

        with o2:
            st.markdown("**Transactions / client / mois**")
            st.caption("1 → 12")
            # ✅ Slider horizontal (comme cycles)
            st.slider(
                label="",
                min_value=1.0,
                max_value=12.0,
                value=float(st.session_state["tx_per_client_per_month"]),
                step=0.5,
                key="tx_per_client_per_month",
                label_visibility="collapsed",
            )

        st.markdown("</div>", unsafe_allow_html=True)

    # =========================
    # RIGHT: Outputs + panel Inputs en bas
    # =========================
    with main_right:
        # --- CALCULS
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

        # --- OUTPUTS
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
        # Panel bas droite: Inputs + scénarios rapides + date
        # =========================
        st.markdown('<div class="wb-card">', unsafe_allow_html=True)
        st.markdown("### Inputs")

        scenario = st.selectbox(
            "Scénarios rapides",
            list(SCENARIOS_PRESETS.keys()),
        )
        st.caption("Choisis un scénario puis ajuste les curseurs.")
        
        if "pending_scenario" not in st.session_state:
            st.session_state.pending_scenario = None
        
        if scenario != "Custom":
            st.session_state.pending_scenario = scenario
            st.rerun()



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
            # On met à jour (ou crée) le point Jun 2026 pour la courbe contribution_margin_pct
            d = st.session_state["scenario_date"]
            cm_now = contribution_margin_pct

            # on remplace si date déjà présente, sinon on ajoute
            replaced = False
            for i, s in enumerate(st.session_state.scenarios):
                if s.get("date") == d:
                    st.session_state.scenarios[i] = {"date": d, "name": scenario_name, "contribution_margin_pct": cm_now}
                    replaced = True
                    break
            if not replaced:
                st.session_state.scenarios.append({"date": d, "name": scenario_name, "contribution_margin_pct": cm_now})

            st.success(f"Scénario '{scenario_name}' sauvegardé ({d}).")

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # --------------------------------------------------
    # WATERFALL (inchangé)
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
        revenu_pct,
        cout_paiement_pct,
        cout_liquidite_10j_pct,
        defaut_30j_pct,
        contribution_margin_pct,
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
    # TIME SERIES: seulement contribution_margin_pct (3 dates)
    # --------------------------------------------------
    st.markdown("### Évolution dans le temps (Contribution margin uniquement)")

    df_hist = pd.DataFrame(st.session_state.scenarios)

    # Garde uniquement les 3 dates demandées (si Jun 2026 a été modifié via SAVE, il sera mis à jour)
    df_hist = df_hist[df_hist["date"].isin(HISTORY_DATES)].sort_values("date")

    # Sécurité: si doublons, on garde la dernière occurrence
    df_hist = df_hist.drop_duplicates(subset=["date"], keep="last")

    line_chart = (
        alt.Chart(df_hist)
        .mark_line(point=True)
        .encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("contribution_margin_pct:Q", title="%"),
            tooltip=[alt.Tooltip("date:T", title="Date"), alt.Tooltip("contribution_margin_pct:Q", title="Contribution (%)", format=".2f")],
        )
        .properties(height=260)
    )
    st.altair_chart(line_chart, use_container_width=True)

    st.dataframe(df_hist, use_container_width=True)
