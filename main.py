import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Configurazione Pagina
st.set_page_config(page_title="CFD Simulator 1GW", layout="wide")

# Costante: Potenza normalizzata a 1 GW
POWER_MW = 1000 

st.title("🏗️ Simulatore Economico Energia")
st.markdown(f"""
Questo modello analizza la redditività di un impianto da **{POWER_MW/1000} GW** ({POWER_MW} MW). 
Ideale per simulare la redditività degli investimenti in infrastrutture energetiche.
""")

# --- LOGICA DI CALCOLO ---
def run_simulation(capex_w, oem_w, cf, strike_mwh, wacc_base, const_yrs, op_yrs, infl, is_idx, is_risk):
    # Parametri derivati
    total_capex_meuro = (POWER_MW * 1000) * capex_w / 1_000_000
    annual_energy_mwh = POWER_MW * 8760 * (cf / 100)
    annual_oem_meuro = (POWER_MW * 1000) * oem_w / 1_000_000
    
    # WACC effettivo
    wacc = wacc_base + (0.03 if is_risk else 0)
    
    years = np.arange(0, const_yrs + op_yrs + 1)
    data = []
    
    for y in years:
        if y == 0:
            nom_cf = 0
        elif 1 <= y <= const_yrs:
            # Esborso CAPEX (negativo)
            nom_cf = -(total_capex_meuro / const_yrs)
        else:
            # Ricavi (Strike Price)
            price = strike_mwh * ((1 + infl)**y) if is_idx else strike_mwh
            rev = (price * annual_energy_mwh) / 1_000_000
            # Costi (O&M sempre indicizzato)
            costs = annual_oem_meuro * ((1 + infl)**y)
            nom_cf = rev - costs
            
        # Attualizzazione
        disc_cf = nom_cf / ((1 + wacc)**y)
        data.append({"Anno": y, "Nominale": nom_cf, "Attualizzato": disc_cf})
        
    df = pd.DataFrame(data)
    df['VAN_Cumulativo'] = df['Attualizzato'].cumsum()
    return df, wacc, total_capex_meuro

# --- LAYOUT: GRAFICO IN ALTO ---
chart_area = st.empty()
metrics_area = st.empty()

st.divider()

# --- LAYOUT: SLIDERS IN BASSO ---
st.subheader("⚙️ Parametri di Configurazione (Impianto da 1 GW)")
col1, col2, col3 = st.columns(3)

with col1:
    st.write("**💰 Investimento e Costi**")
    capex_watt = st.slider("CAPEX (€/Watt)", 0.5, 15.0, 8.0, step=0.5, help="Nucleare: 8-12€/W. Eolico: 2-4€/W. Solare: 0.8€/W.")
    oem_watt = st.slider("O&M Annuo (€/Watt)", 0.01, 0.40, 0.06, step=0.01)
    const_years = st.slider("Anni Costruzione/Autorizzazione", 1, 20, 10)

with col2:
    st.write("**📈 Performance e Mercato**")
    capacity_factor = st.slider("Capacity Factor (%)", 10, 100, 90, help="Nucleare: 90%. Eolico Offshore: 45%. Solare: 18%.")
    strike_price = st.slider("Strike Price CFD (€/MWh)", 30, 250, 90)
    op_life = st.slider("Vita Operativa (Anni)", 10, 80, 60)

with col3:
    st.write("**⚠️ Rischi e Finanza**")
    wacc_base = st.slider("Tasso Sconto (WACC) Base (%)", 0.0, 15.0, 5.0) / 100
    inflation = st.slider("Inflazione (%)", 0.0, 10.0, 2.0) / 100
    is_indexed = st.checkbox("CFD Indicizzato all'inflazione", value=True)
    has_risk = st.checkbox("Applica Premio al Rischio (+3%)")

# Esecuzione
df_res, wacc_eff, total_capex = run_simulation(
    capex_watt, oem_watt, capacity_factor, strike_price, 
    wacc_base, const_years, op_life, inflation, is_indexed, has_risk
)

# --- AGGIORNAMENTO GRAFICO E METRICHE ---
npv_final = df_res['Attualizzato'].sum()

with metrics_area:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("CAPEX Totale", f"{total_capex:,.0f} M€")
    m2.metric("VAN (NPV)", f"{npv_final:,.2f} M€", delta=None)
    m3.metric("WACC Applicato", f"{wacc_eff*100:.1f} %")
    pb_year = df_res[df_res['VAN_Cumulativo'] > 0]['Anno'].min()
    m4.metric("Payback Period", f"{pb_year if pd.notnull(pb_year) else 'Mai'} anni")

with chart_area:
    fig = go.Figure()
    # Barre flussi annuali
    fig.add_trace(go.Bar(x=df_res['Anno'], y=df_res['Attualizzato'], name='Cash Flow Annuale (Attualizzato)', marker_color='#3366CC'))
    # Linea VAN
    fig.add_trace(go.Scatter(x=df_res['Anno'], y=df_res['VAN_Cumulativo'], name='VAN Cumulativo', line=dict(color='#FF4B4B', width=4)))
    
    fig.update_layout(
        height=500,
        margin=dict(t=20),
        hovermode="x unified",
        template="plotly_white",
        yaxis_title="Milioni di Euro (M€)",
        xaxis_title="Anni dall'inizio autorizzazioni",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

# Nota tecnica
st.caption(f"Nota: In questo modello da 1 GW, ogni variazione di 1€/MWh nello Strike Price sposta il ricavo annuo di circa { (POWER_MW * 8760 * 0.9 / 1e6):.1f} M€ (assumendo CF 90%).")
