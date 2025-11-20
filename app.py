import streamlit as st
import pandas as pd
from datetime import date
import plotly.graph_objects as go

st.set_page_config(
    page_title="Waribei – Unit Economics",
    layout="wide"
)

DUREE_PERIODE_LIQUIDITE_JOURS = 10

# ---------- STATE ----------
if "scenarios" not in st.session_state:
    st.session_state.scenarios = []
if "baseline" not in st.session_state:
    st.session_state.baseline = None
if "scenario_date" not in st.session_state:
    st.session_state.scenario_date = date.today()

# ---------- HEADER ----------
top = st.columns([0.7, 0.3])
with top[0]:
    st.title("Unit Economics – Waribei")

with top[1]:
    try:
        st.image("logo_waribei_icon@2x.png", width=100)
    except Exception:
        st.write("Logo Waribei (ajoute logo_waribei_icon@2x.png)")

st.markdown("---")

# ---------- MAIN ZONE ----------
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

    # Calculs
    taux_liquidite_annuel_pct = cout_liquidite_10j_pct * 365 / DUREE_PERIODE_LIQUIDITE_JOURS
    cout_total_pct = cout_paiement_pct + cout_liquidite_10j_pct + defaut_30j_pct
    contribution_margin_pct = revenu_pct - cout_total_pct

    st.caption(f"Coût de liquidité annualisé ≈ **{taux_liquidite_annuel_pct:.1f} %**")

with right:
    st.subheader("Contribution")

    st.markdown("Contribution margin / trx")
    # Gros cadre pour la margin, couleur Waribei
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

    # Date + Today
    date_cols = st.columns([0.7, 0.3])
    with date_cols[0]:
        scenario_date = st.date_input(
            "Date",
            value=st.session_state.scenario_date,
            key="scenario_date"
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
        }
        st.session_state.scenarios.append(scenario)
        if st.session_state.baseline is None:
            st.session_state.baseline = scenario
        st.success(f"Scénario '{scenario_name}' sauvegardé ({st.session_state.scenario_date}).")

st.markdown("---")

# ---------- WATERFALL CHART ----------
st.markdown("### Décomposition par transaction (waterfall)")

waterfall_fig = go.Figure(
    go.Waterfall(
        name="Unit Economics",
        orientation="v",
        x=[
            "Revenu",
            "Coût paiement",
            "Coût liquidité (10j)",
            "Pertes (30j)",
            "Contribution margin",
        ],
        measure=["relative", "relative", "relative", "relative", "total"],
        y=[
            revenu_pct,
            -cout_paiement_pct,
            -cout_liquidite_10j_pct,
            -defaut_30j_pct,
            contribution_margin_pct,
        ],
        text=[f"{v:.2f} %" for v in [
            revenu_pct,
            -cout_paiement_pct,
            -cout_liquidite_10j_pct,
            -defaut_30j_pct,
            contribution_margin_pct,
        ]],
        textposition="outside",
        connector={"line": {"color": "#8ECAE6"}},
        increasing={"marker": {"color": "#1B5A43"}},
        decreasing={"marker": {"color": "#F83131"}},
        totals={"marker": {"color": "#064C72"}},
    )
)

waterfall_fig.update_layout(
    showlegend=False,
    yaxis_title="%",
    margin=dict(l=20, r=20, t=20, b=20),
)
st.plotly_chart(waterfall_fig, use_container_width=True)

# ---------- TIME SERIES ----------
st.markdown("### Évolution dans le temps")

if st.session_state.scenarios:
    df_scenarios = pd.DataFrame(st.session_state.scenarios).sort_values("date")

    line_df = df_scenarios.set_index("date")[
        [
            "revenu_pct",
            "cout_paiement_pct",
            "cout_liquidite_10j_pct",
            "defaut_30j_pct",
            "contribution_margin_pct",
        ]
    ]
    st.line_chart(line_df)

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
