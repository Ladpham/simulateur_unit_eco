import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(
    page_title="Waribei – Unit Economics",
    layout="wide"
)

# ---------- STATE ----------
if "scenarios" not in st.session_state:
    st.session_state.scenarios = []  # liste de scénarios
if "baseline" not in st.session_state:
    st.session_state.baseline = None

DUREE_PERIODE_LIQUIDITE_JOURS = 10

# ---------- HEADER ----------
top = st.columns([0.7, 0.3])
with top[0]:
    st.title("Unit Economics – Waribei")

with top[1]:
    try:
        st.image("waribei_logo.png", width=140)
    except Exception:
        st.write("Logo Waribei (ajouter waribei_logo.png)")

st.markdown("---")

# ---------- ZONE PRINCIPALE (comme ton croquis) ----------
left, right = st.columns([0.6, 0.4])

with left:
    st.subheader("Hypothèses par transaction")

    c1, c2 = st.columns([0.6, 0.4])

    with c1:
        st.markdown("**Revenus / transaction**")
        st.markdown("Coût de paiement / trx")
        st.markdown("Coût de liquidité (10j)")
        st.markdown("Taux de défaut 30j / trx")

    with c2:
        revenu_pct = st.number_input(
            " ",
            min_value=0.0,
            max_value=100.0,
            value=3.8,
            step=0.1,
            key="revenu_pct",
        )
        cout_paiement_pct = st.number_input(
            "  ",
            min_value=0.0,
            max_value=100.0,
            value=1.8,
            step=0.1,
            key="cout_paiement_pct",
        )
        cout_liquidite_10j_pct = st.number_input(
            "   ",
            min_value=0.0,
            max_value=100.0,
            value=0.55,
            step=0.05,
            key="cout_liquidite_10j_pct",
            help="Affiché aussi en taux annuel"
        )
        defaut_30j_pct = st.number_input(
            "    ",
            min_value=0.0,
            max_value=100.0,
            value=1.7,
            step=0.1,
            key="defaut_30j_pct",
        )

    # Calculs
    taux_liquidite_annuel_pct = cout_liquidite_10j_pct * 365 / DUREE_PERIODE_LIQUIDITE_JOURS
    cout_total_pct = cout_paiement_pct + cout_liquidite_10j_pct + defaut_30j_pct
    contribution_margin_pct = revenu_pct - cout_total_pct

    st.markdown("")
    st.caption(f"Coût de liquidité annualisé ≈ **{taux_liquidite_annuel_pct:.1f} %**")

with right:
    st.subheader("Contribution")

    st.markdown("**Contribution margin / trx**")
    st.markdown(
        f"<div style='border:1px solid #ddd;padding:12px;border-radius:6px;"
        f"font-size:24px;font-weight:bold;text-align:center;'>"
        f"{contribution_margin_pct:.2f} %</div>",
        unsafe_allow_html=True
    )

    st.markdown("")

    date_col, today_col = st.columns([0.7, 0.3])
    with date_col:
        scenario_date = st.date_input("Date", value=date.today())
    with today_col:
        if st.button("Today"):
            scenario_date = date.today()

    scenario_name = st.text_input("Label du scénario", value="Today")

    if st.button("SAVE"):
        scenario = {
            "date": scenario_date,
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
        st.success(f"Scénario '{scenario_name}' sauvegardé ({scenario_date}).")

st.markdown("---")

# ---------- GRAPHIQUE BARRES (comme ton rectangle du bas gauche) ----------
st.markdown("### Décomposition par transaction")

bar_df = pd.DataFrame(
    {
        "Poste": [
            "Revenu",
            "Coût paiement",
            "Coût liquidité (10j)",
            "Pertes (30j)",
            "Contribution margin",
        ],
        "Pourcentage": [
            revenu_pct,
            -cout_paiement_pct,
            -cout_liquidite_10j_pct,
            -defaut_30j_pct,
            contribution_margin_pct,
        ],
    }
).set_index("Poste")

st.bar_chart(bar_df)

# ---------- COURBE DANS LE TEMPS (comme ta courbe en bas à droite) ----------
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

    # gestion suppression scénarios
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
