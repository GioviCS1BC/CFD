import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="CFD Energy Simulator", layout="wide")

st.title("⚛️ Simulatore Energetico: Dal Fotovoltaico al Nucleare")
st.markdown("""
Regola i parametri per confrontare diverse tecnologie. Il modello calcola l'impatto di 
**CAPEX elevati**, **lunghi tempi di costruzione** e **alta disponibilità (CF)**.
""")

# --- LOGICA DI CALCOLO ---
def calculate_cfd(power_mw, capex_watt, oem_watt, cf, strike_mwh, discount_rate, 
                  const_years, inflation, op_life, is_indexed, has_risk):
    
    # Conversione unità
    power_w = power_mw * 1_000_000
    total_capex = power_w * capex_watt
    annual_energy_mwh = power_mw * 8760 * (cf / 100)
    annual_oem = power_w * oem_watt
    
    # Tasso di sconto (WACC) con eventuale premio al rischio
    effective_rate = discount_rate + (0.03 if has_risk else 0)
    
    # Orizzonte temporale totale
    years = np.arange(0, const_years + op_life + 1)
    
    cash_flows = []
    for y in years:
        if y == 0:
            cf_val = 0
        elif 1 <= y <= const_years:
            # CAPEX distribuito equamente durante la costruzione (espresso in M€)
            cf_val = -(total_capex / const_years) / 1_000_000
        else:
            # Ricavo: Strike Price indicizzato o meno
            current_strike = strike_mwh * ((1 + inflation)**y) if is_indexed else strike_mwh
            revenue = (current_strike * annual_energy_mwh) / 1_000_000
            
            # O&M: indicizzato all'inflazione (espresso in M€)
            current_oem = (annual_oem * ((1 + inflation)**y)) / 1_000_000
            
            cf_val = revenue - current_oem
        cash_flows.append(cf_val)
    
    df = pd.DataFrame({'Anno': years, 'CF_Nominale': cash_flows})
    df['CF_Attualizzato'] = df['CF_Nominale'] / ((1 + effective_rate)**df['Anno'])
    df['VAN_Cumulativo'] = df['CF_Attualizzato'].cumsum()
    
    return df, effective_rate, total_capex / 1_000_000

# --- INTERFACCIA PARAMETRI ---
chart_placeholder = st.empty()
st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🏗️ Scala del Progetto")
    # Aumentato a 3000 MW per simulare grandi centrali nucleari
    power_mw = st.number_input("Potenza Impianto (MW)", value=1000.0, step=100.0)
    # Fondoscala CF al 100%
    cf = st.slider("Capacity Factor (%)", 10, 100, 90)
    # Tempi di costruzione fino a 20 anni (tipico nucleare)
    const_years = st.slider("Anni Costruzione/Autorizzazione", 1, 20, 10)

with col2:
    st.subheader("💰 Costi Unitari")
    # Fondoscala CAPEX a 15€/Watt (Nucleare ~8-12€/W)
    capex_watt = st.slider("CAPEX (€/Watt)", 0.5, 15.0, 10.0, step=0.5)
    # O&M Nucleare è più alto, fondoscala aumentato
    oem_watt = st.slider("O&M Annuo (€/Watt)", 0.01, 0.30, 0.05, step=0.01)
    discount_rate = st.slider("WACC Base (%)", 0.0, 15.0, 5.0) / 100

with col3:
    st.subheader("📊 Contratto & Vita")
    strike_mwh = st.slider("Strike Price CFD (€/MWh)", 30, 200, 80)
    # Vita operativa fino a 80 anni (nuovi reattori nucleari)
    op_life = st.slider("Vita Operativa (Anni)", 10, 80, 60)
    is_indexed = st.checkbox("CFD Indicizzato all'inflazione", value=True)
    has_risk = st.checkbox("Applica Rischio Paese/Tecnologico (+3%)")
    inflation = st.slider("Tasso Inflazione %", 0.0, 10.0, 2.0) / 100

# Esecuzione calcoli
df_res, rate_eff, total_capex_m = calculate_cfd(
    power_mw, capex_watt, oem_watt, cf, strike_mwh, 
    discount_rate, const_years, inflation, op_life, is_indexed, has_risk
)

# --- VISUALIZZAZIONE RISULTATI ---
with chart_placeholder:
    # Metriche principali
    m1, m2, m3 = st.columns(3)
    m1.metric("Investimento Totale (CAPEX)", f"{total_capex_m:,.0f} M€")
    van_totale = df_res['CF_Attualizzato'].sum()
    m2.metric("VAN (NPV) Progetto", f"{van_totale:,.2f} M€")
    
    payback_row = df_res[df_res['VAN_Cumulativo'] > 0]
    payback = payback_row['Anno'].min() if not payback_row.empty else "Mai"
    m3.metric("Rientro (Payback Period)", f"{payback} anni")

    # Grafico Interattivo
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_res['Anno'], 
        y=df_res['CF_Attualizzato'], 
        name='Cash Flow Attualizzato (M€)',
        marker_color='royalblue'
    ))
    fig.add_trace(go.Scatter(
        x=df_res['Anno'], 
        y=df_res['VAN_Cumulativo'], 
        name='VAN Cumulativo', 
        line=dict(color='crimson', width=4)
    ))
    
    fig.update_layout(
        height=500,
        title=f"Analisi Finanziaria Progetto da {power_mw} MW",
        xaxis_title="Anni",
        yaxis_title="Valore (Milioni di Euro)",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    st.plotly_chart(fig, use_container_width=True)

# Spiegazione per il caso Nucleare
if capex_watt >= 7:
    st.info("""
    **Focus Nucleare:** In questo scenario, l'investimento iniziale è enorme (miliardi di euro) e i flussi di cassa 
    positivi iniziano molto tardi. Noterai che il **Tasso di Sconto (WACC)** è il parametro più sensibile: 
    anche un aumento dell'1% del WACC può rendere il progetto non bancabile perché i profitti arrivano troppo lontano nel tempo.
    """)
