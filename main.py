import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Configurazione Pagina
st.set_page_config(page_title="CFD Simulator 1GW", layout="wide")

# Costante: 1 GW = 1.000.000.000 Watt
POWER_W = 1_000_000_000
POWER_MW = 1000

st.title("⚛️ Simulatore Finanziario 1 GW: Efficienza del Capitale")

# --- LOGICA DI CALCOLO ---
def run_simulation(capex_w, oem_w, cf, strike_mwh, wacc_base, const_yrs, op_yrs, infl, is_idx, is_risk):
    total_capex_meuro = (POWER_W * capex_w) / 1_000_000
    annual_energy_mwh = POWER_MW * 8760 * (cf / 100)
    annual_oem_meuro = (POWER_W * oem_w) / 1_000_000
    wacc = wacc_base + (0.03 if is_risk else 0)
    
    years = np.arange(0, const_yrs + op_yrs + 1)
    data = []
    
    for y in years:
        if 0 <= y <= const_yrs:
            # Esborso CAPEX distribuito
            nom_cf = -(total_capex_meuro / (const_yrs + 1)) 
        else:
            # Fase operativa
            price = strike_mwh * ((1 + infl)**y) if is_idx else strike_mwh
            rev = (price * annual_energy_mwh) / 1_000_000
            costs = annual_oem_meuro * ((1 + infl)**y)
            nom_cf = rev - costs
            
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
    st.write("**💰 Investimento**")
    capex_watt = st.slider("CAPEX (€/Watt)", 0.5, 15.0, 10.0, step=0.1)
    oem_watt = st.slider("O&M Annuo (€/Watt)", 0.01, 0.40, 0.06, step=0.01)
    const_years = st.slider("Anni Costruzione", 1, 20, 10)
with col2:
    st.write("**📈 Performance**")
    capacity_factor = st.slider("Capacity Factor (%)", 10, 100, 90)
    strike_price = st.slider("Strike Price CFD (€/MWh)", 30, 250, 100)
    op_life = st.slider("Vita Operativa (Anni)", 10, 80, 60)
with col3:
    st.write("**⚠️ Finanza**")
    wacc_base = st.slider("WACC Base (%)", 0.0, 15.0, 5.0) / 100
    inflation = st.slider("Inflazione (%)", 0.0, 10.0, 2.0) / 100
    is_indexed = st.checkbox("CFD Indicizzato", value=True)
    has_risk = st.checkbox("Rischio Progetto (+3%)")

# Esecuzione
df_res, wacc_eff, total_capex = run_simulation(
    capex_watt, oem_watt, capacity_factor, strike_price, 
    wacc_base, const_years, op_life, inflation, is_indexed, has_risk
)

# Calcolo Metriche
npv_final = df_res['Attualizzato'].sum()
# Calcolo VAN % CAPEX
van_capex_ratio = (npv_final / total_capex) * 100

with metrics_area:
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("CAPEX Totale", f"{total_capex/1000:.1f} Mld€")
    m2.metric("VAN (NPV)", f"{npv_final:,.0f} M€")
    
    # Colore della metrica basato sul valore
    color = "normal" if van_capex_ratio >= 0 else "inverse"
    m3.metric("VAN / CAPEX (%)", f"{van_capex_ratio:.1f}%", help="Valore creato rispetto all'investimento iniziale")
    
    m4.metric("WACC Effettivo", f"{wacc_eff*100:.1f}%")
    pb_idx = df_res[df_res['VAN_Cumulativo'] > 0]['Anno'].min()
    m5.metric("Payback", f"{pb_idx if pd.notnull(pb_idx) else 'Mai'} anni")

with chart_area:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_res['Anno'], y=df_res['Attualizzato'], name='Cash Flow Attualizzato', marker_color='#3366CC'))
    fig.add_trace(go.Scatter(x=df_res['Anno'], y=df_res['VAN_Cumulativo'], name='VAN Cumulativo', line=dict(color='#FF4B4B', width=4)))
    fig.update_layout(height=450, template="plotly_white", margin=dict(t=20), yaxis_title="M€")
    st.plotly_chart(fig, use_container_width=True)

# Spiegazione Tecnica
st.markdown(f"""
### Interpretazione della Redditività
Il rapporto **VAN / CAPEX** ($\dfrac{{NPV}}{{CAPEX}}$) indica l'efficienza del capitale investito:
* **Sotto lo 0%**: Il progetto non recupera nemmeno il costo del capitale (WACC). È un investimento che distrugge valore.
* **0% - 20%**: Progetto marginale o a basso rendimento (comune in infrastrutture pubbliche molto sicure).
* **Sopra il 50%**: Progetto estremamente profittevole.
""")
