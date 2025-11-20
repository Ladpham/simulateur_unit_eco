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
# SESSION STATE
# --------------------------------------------------
if "scenarios" not in st.session_state:
    st.session_state.scenarios = []
if "baseline" not in st.session_state:
    st.session_state.baseline = None
if "scenario_date" not in st.session_state:
    st.session_state.scenario_date = date.today()

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
left, right = st.columns([0.6, 0.4])

with left:
    st.subheader("Hypothèses par transaction")

    # Row 1: Revenu / trx
    row1 = st.columns([0.6, 0.4])
    with row1[0]:
        st.markdown("**Revenus / transaction**")
    with row1[1]:
        revenu_pct = st.number_input(
            "",
            min_value=0.0,
            max_value=100.0,
            value=3.8,
            step=0.1,
            key="revenu_pct",
            label_visibility="collapsed",
        )

    # Row 2: Coût de paiement
    row2 = st.columns([0.6, 0.4])
    with row2[0]:
        st.markdown("Coût de paiement / trx")
    with row2[1]:
        cout_paiement_pct = st.number_input(
            " ",
            min_value=0.0,
            max_value=100.0,
            value=1.8,
            step=0.1,
            key="cout_paiement_pct",
            label_visibility="collapsed",
        )

    # Row 3: Coût de liquidité (10j)
    row3 = st.columns([0.6, 0.4])
    with row3[0]:
        st.markdown("Coût de liquidité (10j)")
    with row3[1]:
        cout_liquidite_10j_pct = st.number_input(
            "  ",
            min_value=0.0,
            max_value=100.0,
            value=0.55,
            step=0.05,
            key="cout_liquidite_10j_pct",
            label_visibility="collapsed",
            help="Affiché aussi en taux annuel."
        )

    # Row 4: Taux de défaut 30j
    row4 = st.columns([0.6, 0.4])
    with row4[0]:
        st.markdown("Taux de défaut 30j / trx")
    with row4[1]:
        defaut_30j_pct = st.number_input(
            "   ",
            min_value=0.0,
            max_value=100.0,
            value=1.7,
            step=0.1,
            key="defaut_30j_pct",
            label_visibility="collapsed",
        )

    # ---------- VARIABLES DE VOLUME ----------
    st.markdown("")
    st.subheader("Variables de volume")

    row5 = st.columns([0.6, 0.4])
    with row5[0]:
        st.markdown("Cycles de liquidité / mois")
    with row5[1]:
        cycles_per_month = st.number_input(
            "    ",
            min_value=0.0,
            max_value=100.0,
            value=2.9,
            step=0.1,
            key="cycles_per_month",
            label_visibility="collapsed",
        )

    row6 = st.columns([0.6, 0.4])
    with row6[0]:
        st.markdown("Loan book moyen (k€)")
    with row6[1]:
        loan_book_k = st.number_input(
            "     ",
            min_value=0.0,
            max_value=100000.0,
            value=100.0,
            step=10.0,
            key="loan_book_k",
            label_visibility="collapsed",
        )

    # ---------- CALCULS ----------
    taux_liquidite_annuel_pct = cout_liquidite_10j_pct * 365 / DUREE_PERIODE_LIQUIDITE_JOURS
    cout_total_pct = cout_paiement_pct + cout_liquidite_10j_pct + defaut_30j_pct
    contribution_margin_pct = revenu_pct - cout_total_pct

    # Contribution profit par mois en k€
    contribution_value_k = loan_book_k * cycles_per_month * contribution_margin_pct / 100

    st.caption(f"Coût de liquidité annualisé ≈ **{taux_liquidite_annuel_pct:.1f} %**")

with right:
    st.subheader("Contribution")

    # ---------- Contribution margin ----------
    st.markdown("Contribution margin / trx")
    st.markdown(
        f"""
        <div style="
            border:2px solid #064C72;
            padding:16px;
            border-radius:8px;
            font-size:26px;
            font-weight:bold;
            text-align:center;
            background-color:#FFDBCC;
            color:#064C72;">
            {contribution_margin_pct:.2f} %
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("")

    # ---------- Contribution value ----------
    st.markdown("Contribution value / mois")
    st.markdown(
        f"""
        <div style="
            border:2px solid #1B5A43;
            padding:14px;
            border-radius:8px;
            font-size:22px;
            font-weight:bold;
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

    # Date + Today
    date_cols = st.columns([0.7, 0.3])
    with date_cols[0]:
        st.session_state.scenario_date = st.date_input(
            "Date",
            value=st.session_state.scenario_date,
            key="scenario_date_input"
        )
    with date_cols[1]:
        if st.button("Today"):
            st.session_state.scenario_date = date.today()

    scenario_name = st.text_input("Label du scénario", value="Today")

    if st.button("SAVE"):
        scenario = {
            "date": st.session_state.scenario_date,
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
        }
        st.session_state.scenarios.append(scenario)
        if st.session_state.baseline is None:
            st.session_state.baseline = scenario
        st.success(f"Scénario '{scenario_name}' sauvegardé ({st.session_state.scenario_date}).")

st.markdown("---")

# --------------------------------------------------
# WATERFALL DATA PREP (Revenu -> coûts -> Margin)
# --------------------------------------------------
def make_waterfall_df(revenue, pay_cost, liq_cost, default_cost, margin):
    steps = [
        "Revenu",
        "Coût paiement",
        "Coût liquidité (10j)",
        "Défaut 30j",
        "Contribution"
    ]
    values = [
        revenue,
        -pay_cost,
        -liq_cost,
        -default_cost,
        margin
    ]

    start = []
    end = []
    running = 0.0
    for v in values[:-1]:
        start.append(running)
        running += v
        end.append(running)

    # Dernier step = total: de 0 à margin
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

    return pd.DataFrame(
        {
            "step": steps,
            "value": values,
            "start": start,
            "end": end,
            "type": types,
        }
    )

# --------------------------------------------------
# WATERFALL CHART (Altair, no zoom)
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

labels = (
    alt.Chart(wf_df)
    .mark_text(dy=-6, color="#333", fontSize=11)
    .encode(
        x=alt.X("step:N", sort=list(wf_df["step"])),
        y="end:Q",
        text=alt.Text("value:Q", format=".2f"),
    )
)

st.altair_chart(
    (waterfall_chart + labels).properties(height=260),
    use_container_width=True,
)

# --------------------------------------------------
# TIME SERIES CHART (Altair, no zoom)
# --------------------------------------------------
st.markdown("### Évolution dans le temps")

if st.session_state.scenarios:
    df_scenarios = pd.DataFrame(st.session_state.scenarios).sort_values("date")

    # On garde les métriques de unit economics pour la courbe
    line_df = df_scenarios[
        [
            "date",
            "revenu_pct",
            "cout_paiement_pct",
            "cout_liquidite_10j_pct",
            "defaut_30j_pct",
            "contribution_margin_pct",
        ]
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

    # Scénarios list + delete
    st.markdown("#### Scénarios enregistrés")
    st.dataframe(df_scenarios, use_container_width=True)

    labels = [
        f"{row.date} – {row.name}"
        for _, row in df_scenarios.reset_index(drop=True).iterrows()
    ]
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
