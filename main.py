import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="CFD Advanced Model", layout="wide")

st.title("⚡ Analisi CFD: Parametri Tecnici ed Economici")
st.markdown("""
Modello basato su **potenza installata**, **efficienza (CF)** e **costi unitari (€/W)**.
""")

# --- LOGICA DI CALCOLO ---
def calculate_cfd(power_mw, capex_watt, oem_watt, cf, strike_mwh, discount_rate, 
                  const_years, inflation, op_life, is_indexed, has_risk):
    
    # Conversione in unità base
    power_w = power_mw * 1_000_000
    total_capex = power_w * capex_watt
    annual_energy_mwh = power_mw * 8760 * (cf / 100)
    annual_oem = power_w * oem_watt
    
    effective_rate = discount_rate + (0.03 if has_risk else 0)
    years = np.arange(0, const_years + op_life + 1)
    
    cash_flows = []
    for y in years:
        if y == 0:
            cf_val = 0
        elif 1 <= y <= const_years:
            # CAPEX distribuito negli anni di costruzione
            cf_val = -(total_capex / const_years) / 1_000_000  # Espresso in M€
        else:
            # Ricavo: Strike Price (€/MWh) * Produzione (MWh)
            # Indicizzazione applicata allo Strike Price
            current_strike = strike_mwh * ((1 + inflation)**y) if is_indexed else strike_mwh
            revenue = (current_strike * annual_energy_mwh) / 1_000_000 # M€
            
            # O&M: indicizzato all'inflazione
            current_oem = (annual_oem * ((1 + inflation)**y)) / 1_000_000 # M€
            
            cf_val = revenue - current_oem
        cash_flows.append(cf_val)
    
    df = pd.DataFrame({'Anno': years, 'CF_Nominale': cash_flows})
    df['CF_Attualizzato'] = df['CF_Nominale'] / ((1 + effective_rate)**df['Anno'])
    df['VAN_Cumulativo'] = df['CF_Attualizzato'].cumsum()
    
    return df, effective_rate, total_capex / 1_000_000

# --- UI PARAMETRI ---
chart_placeholder = st.empty()
st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🏗️ Dimensionamento")
    power_mw = st.number_input("Potenza Impianto (MW)", value=10.0, step=1.0)
    cf = st.slider("Capacity Factor (%)", 10, 60, 20)
    const_years = st.slider("Anni Costruzione", 1, 5, 2)

with col2:
    st.subheader("💰 Costi Unitari")
    capex_watt = st.slider("CAPEX (€/Watt)", 0.5, 3.0, 0.8, step=0.1)
    oem_watt = st.slider("O&M Annuo (€/Watt)", 0.01, 0.10, 0.02, step=0.005)
    discount_rate = st.slider("WACC Base (%)", 0.0, 15.0, 6.0) / 100

with col3:
    st.subheader("📈 Mercato e Rischio")
    strike_mwh = st.slider("Strike Price (€/MWh)", 30, 150, 65)
    inflation = st.slider("Inflazione (%)", 0.0, 10.0, 2.0) / 100
    is_indexed = st.checkbox("CFD Indicizzato", value=True)
    has_risk = st.checkbox("Rischio Regolatorio (+3%)")

# Calcoli
df_res, rate_eff, total_capex_m = calculate_cfd(
    power_mw, capex_watt, oem_watt, cf, strike_mwh, 
    discount_rate, const_years, inflation, 20, is_indexed, has_risk
)

# --- VISUALIZZAZIONE ---
with chart_placeholder:
    # Metriche
    m1, m2, m3 = st.columns(3)
    m1.metric("Investimento Totale", f"{total_capex_m:.2f} M€")
    m2.metric("VAN Progetto", f"{df_res['CF_Attualizzato'].sum():.2f} M€")
    payback = df_res[df_res['VAN_Cumulativo'] > 0]['Anno'].min()
    m3.metric("Payback Period", f"{payback if pd.notnull(payback) else 'Mai'} anni")

    # Grafico
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_res['Anno'], y=df_res['CF_Attualizzato'], name='Cash Flow Attualizzato (M€)'))
    fig.add_trace(go.Scatter(x=df_res['Anno'], y=df_res['VAN_Cumulativo'], name='VAN Cumulativo', line=dict(color='red', width=3)))
    fig.update_layout(height=450, template="plotly_white", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
