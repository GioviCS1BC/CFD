import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Configurazione Pagina
st.set_page_config(page_title="CFD Simulator 1GW", layout="wide")

# Costante: 1 GW = 1.000 MW = 1.000.000.000 Watt
POWER_GW = 1
POWER_MW = 1000 
POWER_W = 1_000_000_000

st.title("Simulatore Finanziario Energia")
st.markdown(f"""
Analisi di redditività per un impianto da **1 GW**. """)

# --- LOGICA DI CALCOLO CORRETTA ---
def run_simulation(capex_w, oem_w, cf, strike_mwh, wacc_base, const_yrs, op_yrs, infl, is_idx, is_risk):
    # CORREZIONE UNITÀ DI MISURA:
    # CAPEX Totale (M€) = (Potenza in Watt * €/Watt) / 1.000.000
    total_capex_meuro = (POWER_W * capex_w) / 1_000_000
    
    # Produzione Annua (MWh) = MW * ore_anno * Capacity Factor
    annual_energy_mwh = POWER_MW * 8760 * (cf / 100)
    
    # O&M Annuo (M€) = (Potenza in Watt * €/Watt_anno) / 1.000.000
    annual_oem_meuro = (POWER_W * oem_w) / 1_000_000
    
    # WACC effettivo
    wacc = wacc_base + (0.03 if is_risk else 0)
    
    years = np.arange(0, const_yrs + op_yrs + 1)
    data = []
    
    for y in years:
        # Distribuiamo il CAPEX dall'anno 0 fino alla fine della costruzione
        if 0 <= y < const_yrs:
            # Esborso CAPEX (negativo)
            nom_cf = -(total_capex_meuro / const_yrs)
            # In fase di costruzione non ci sono ricavi né O&M
        elif y == const_yrs:
            # Anno di transizione: ultimo esborso CAPEX e inizio produzione (semplificato)
            nom_cf = -(total_capex_meuro / const_yrs)
        else:
            # FASE OPERATIVA
            # Ricavi indicizzati
            price = strike_mwh * ((1 + infl)**y) if is_idx else strike_mwh
            rev = (price * annual_energy_mwh) / 1_000_000
            # Costi O&M indicizzati
            costs = annual_oem_meuro * ((1 + infl)**y)
            nom_cf = rev - costs
            
        # Attualizzazione: PV = FV / (1 + r)^n
        disc_cf = nom_cf / ((1 + wacc)**y)
        data.append({"Anno": y, "Nominale": nom_cf, "Attualizzato": disc_cf})
        
    df = pd.DataFrame(data)
    df['VAN_Cumulativo'] = df['Attualizzato'].cumsum()
    return df, wacc, total_capex_meuro

# --- UI ---
chart_area = st.empty()
metrics_area = st.empty()

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.write("**💰 Investimento (CAPEX)**")
    # 10 €/W su 1 GW deve dare 10.000 M€
    capex_watt = st.slider("Costo di Costruzione (€/Watt)", 0.5, 15.0, 10.0, step=0.1)
    oem_watt = st.slider("O&M Annuo (€/Watt)", 0.01, 0.40, 0.06, step=0.01)
    const_years = st.slider("Anni di Costruzione", 1, 20, 10)

with col2:
    st.write("**📈 Performance**")
    capacity_factor = st.slider("Capacity Factor (%)", 10, 100, 90)
    strike_price = st.slider("Strike Price CFD (€/MWh)", 30, 250, 100)
    op_life = st.slider("Anni di Esercizio", 10, 50, 30)

with col3:
    st.write("**⚠️ Finanza**")
    wacc_base = st.slider("WACC Base (%)", 0.0, 15.0, 5.0) / 100
    inflation = st.slider("Inflazione (%)", 0.0, 10.0, 2.0) / 100
    is_indexed = st.checkbox("CFD Indicizzato", value=True)
    has_risk = st.checkbox("Rischio Progetto (+3% WACC)")

# Calcolo
df_res, wacc_eff, total_capex = run_simulation(
    capex_watt, oem_watt, capacity_factor, strike_price, 
    wacc_base, const_years, op_life, inflation, is_indexed, has_risk
)

# --- VISUALIZZAZIONE ---
npv_final = df_res['Attualizzato'].sum()

with metrics_area:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("CAPEX Totale", f"{total_capex/1000:.2f} Miliardi €")
    m2.metric("NPV (VAN)", f"{npv_final:,.2f} M€")
    m3.metric("WACC Effettivo", f"{wacc_eff*100:.1f}%")
    # Trova il primo anno in cui il VAN diventa positivo
    pb_idx = df_res[df_res['VAN_Cumulativo'] > 0]['Anno'].min()
    m4.metric("Payback Period", f"{pb_idx if pd.notnull(pb_idx) else 'Mai'} anni")

with chart_area:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_res['Anno'], y=df_res['Attualizzato'], name='Cash Flow Netto Attualizzato', marker_color='#3366CC'))
    fig.add_trace(go.Scatter(x=df_res['Anno'], y=df_res['VAN_Cumulativo'], name='VAN Cumulativo', line=dict(color='#FF4B4B', width=4)))
    fig.update_layout(height=500, template="plotly_white", hovermode="x unified",
                      yaxis_title="M€", xaxis_title="Anni",
                      legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, use_container_width=True)

st.info(f"Con un CAPEX di {capex_watt} €/W, l'investimento per 1 GW è di **{total_capex:,.0f} milioni di euro**. ")
