import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Configurazione della pagina
st.set_page_config(page_title="CFD Investment Simulator", layout="wide")

st.title("Simulatore Economico CFD: L'Impatto del Tempo e del Rischio")
st.markdown("""
Questo simulatore analizza la redditività di un investimento energetico  
considerando che **il tempo è un costo**.
""")

# --- FUNZIONE CALCOLO TIR (IRR) ---
def calcola_tir(cash_flows):
    # Metodo di bisezione semplice per trovare il tasso che azzera il VAN
    lower = -0.99
    upper = 2.0
    for _ in range(100):
        rate = (lower + upper) / 2
        npv = sum([cf / ((1 + rate)**i) for i, cf in enumerate(cash_flows)])
        if npv > 0:
            lower = rate
        else:
            upper = rate
    return rate

# --- LOGICA DI CALCOLO AVANZATA ---
def run_simulation(capex, const_years, discount_rate, inflation, annual_revenue, annual_opex_base, op_life, is_indexed, has_risk):
    # Il rischio aumenta il costo del capitale (WACC)
    effective_rate = discount_rate + (0.03 if has_risk else 0)
    
    total_years = const_years + op_life
    years = np.arange(0, total_years + 1)
    
    df = pd.DataFrame({'Anno': years})
    
    # 1. Flussi di Cassa Nominali
    cash_flows = []
    
    for y in years:
        if y == 0:
            cf = 0
        elif 1 <= y <= const_years:
            # Fase di Costruzione: si spalma il CAPEX
            annual_investment = capex / const_years
            cf = -annual_investment
        else:
            # Fase Operativa
            # Ricavo: indicizzato o fisso
            rev = annual_revenue * ((1 + inflation)**y) if is_indexed else annual_revenue
            # OPEX: basato sul costo €/MWh, inflazionato ogni anno
            opex = annual_opex_base * ((1 + inflation)**y)
            cf = rev - opex
        cash_flows.append(cf)
    
    df['CF_Nominale'] = cash_flows
    
    # 2. Attualizzazione (Discounting al Tempo 0)
    df['CF_Attualizzato'] = df['CF_Nominale'] / ((1 + effective_rate)**df['Anno'])
    
    # 3. Calcolo del VAN Cumulativo
    df['VAN_Cumulativo'] = df['CF_Attualizzato'].cumsum()
    
    # 4. Calcolo CAPEX "Capitalizzato" (IDC - Interest During Construction)
    capex_cap = sum([(capex/const_years) * ((1 + effective_rate)**(const_years - y)) for y in range(1, const_years + 1)])
    
    return df, effective_rate, capex_cap

# --- INTERFACCIA GRAFICA ---
chart_spot = st.empty()
metrics_spot = st.empty()

st.divider()

# --- INPUT PARAMETERS ---
st.subheader("⚙️ Parametri Tecnici e Finanziari")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("**🛠️ Dati Impianto e Costi**")
    potenza_mw = st.slider("Potenza Impianto (MW)", 1, 3000, 1000, step=10)
    costo_watt = st.slider("CAPEX: Costo al Watt (€/W)", 0.1, 10.0, 5.0, step=0.1)
    om_mwh = st.slider("OPEX: Costo O&M (€/MWh)", 1.0, 100.0, 25.0, step=1.0)
    const_time = st.slider("Anni Autorizzazione/Costruzione", 1, 15, 8)

with c2:
    st.markdown("**⚡ Produzione e Mercato**")
    capacity_factor = st.slider("Capacity Factor (%)", 5, 100, 90) / 100
    strike_mwh = st.slider("Strike Price (€/MWh)", 20, 300, 80, step=5)
    op_time = st.slider("Anni di Operatività", 10, 80, 60)

with c3:
    st.markdown("**📉 Finanza e Rischio**")
    wacc_base = st.slider("Tasso di Sconto Base (WACC) %", 0.0, 15.0, 6.0, step=0.5) / 100
    infl_val = st.slider("Tasso Inflazione %", 0.0, 10.0, 2.0, step=0.5) / 100
    
    st.write("**Clausole Contrattuali**")
    indexed = st.checkbox("CFD Indicizzato all'inflazione", value=True)
    risk = st.checkbox("Applica Fattore di Rischio (+3% WACC)", value=False)

# --- CALCOLI INTERMEDI ---
# CAPEX Nominale in M€
capex_val = potenza_mw * costo_watt

# Produzione, Ricavo Annuo e Opex Annuo Base
produzione_annua_mwh = potenza_mw * 8760 * capacity_factor
ricavo_annuo_meuro = (produzione_annua_mwh * strike_mwh) / 1_000_000
opex_annuo_meuro = (produzione_annua_mwh * om_mwh) / 1_000_000

# Esecuzione della simulazione
df_res, rate_used, capex_real = run_simulation(capex_val, const_time, wacc_base, infl_val, ricavo_annuo_meuro, opex_annuo_meuro, op_time, indexed, risk)

# Calcolo KPI Finanziari
npv_absolute = df_res['CF_Attualizzato'].sum()
npv_percentage = (npv_absolute / capex_val) * 100
tir_valore = calcola_tir(df_res['CF_Nominale'].tolist()) * 100

# --- RENDERING RISULTATI ---
with metrics_spot:
    st.caption(f"📊 **Dati Derivati:** Inv. Nominale: **{capex_val:,.1f} M€** | Produzione: **{produzione_annua_mwh:,.0f} MWh/anno** | Ricavo Base: **{ricavo_annuo_meuro:,.2f} M€/anno** | O&M Base: **{opex_annuo_meuro:,.2f} M€/anno**")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("VAN del Progetto", f"{npv_percentage:.2f} %", 
              delta="Redditizio" if npv_absolute > 0 else "In Perdita", delta_color="normal")
    m2.metric("TIR (Rendimento Annuo)", f"{tir_valore:.2f} %",
              help="Tasso Interno di Rendimento. Se è maggiore del WACC, il progetto crea valore.")
    m3.metric("CAPEX Reale (Capitalizzato)", f"{capex_real:.2f} M€", 
              help="Costo effettivo del debito al momento dell'accensione.")
    
    pb_row = df_res[df_res['VAN_Cumulativo'] > 0]
    pb_val = pb_row['Anno'].min() if not pb_row.empty else "Mai"
    m4.metric("Tempo di Rientro (Anni)", f"{pb_val}")

with chart_spot:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_res['Anno'], y=df_res['CF_Attualizzato'],
        name="Cash Flow Attualizzato",
        marker_color=np.where(df_res['CF_Attualizzato'] < 0, '#EF553B', '#00CC96')
    ))
    fig.add_trace(go.Scatter(
        x=df_res['Anno'], y=df_res['VAN_Cumulativo'],
        name="VAN Cumulativo",
        line=dict(color='white', width=3)
    ))
    fig.update_layout(
        height=500,
        template="plotly_dark",
        title=f"Analisi DCF (WACC applicato: {rate_used*100:.1f}%)",
        xaxis_title="Anni",
        yaxis_title="M€",
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

# --- SPIEGAZIONE E DISCLAIMER ---
st.divider()
exp, disc = st.columns([2, 1])

with exp:
    with st.expander("📚 Analisi del Valore e del Tempo (VAN vs TIR)"):
        st.write(f"""
        **Il VAN non è un rendimento annuo.** Un VAN del {npv_percentage:.2f}% significa che il progetto ha coperto tutti i costi, 
        ha remunerato il capitale esattamente al {rate_used*100:.1f}% (WACC) e ha generato una ricchezza netta aggiuntiva.
        
        Per valutare il ritorno economico dell'investimento, guarda il **TIR ({tir_valore:.2f}%)**. Questo è il rendimento reale annuo del capitale investito. 
        In progetti infrastrutturali a lungo termine, un TIR superiore al costo del capitale (WACC) rende l'opera cantierabile.
        
        **L'effetto dell'orizzonte temporale:** I flussi di cassa oltre il 30° anno sono bassissimi nel grafico perché l'attualizzazione 
        "schiaccia" il valore futuro del denaro: 1 Euro incassato tra 50 anni vale pochissimi centesimi oggi.
        """)

with disc:
    with st.expander("⚠️ Disclaimer & Contatti"):
        st.write("""
        I risultati sono stime basate su modelli finanziari semplificati (DCF). 
        Per approfondimenti o consulenze:
        """)
        st.markdown(f"📧 [giovanni@unbelclima.it](mailto:giovanni@unbelclima.it)")
