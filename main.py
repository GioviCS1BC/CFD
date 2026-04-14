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

# --- LOGICA DI CALCOLO AVANZATA ---
def run_simulation(capex, const_years, discount_rate, inflation, strike_price, op_life, is_indexed, has_risk):
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
            # Fase di Costruzione
            annual_investment = capex / const_years
            cf = -annual_investment
        else:
            # Fase Operativa
            # Ricavo: indicizzato o fisso
            rev = strike_price * ((1 + inflation)**y) if is_indexed else strike_price
            # OPEX: stimato al 20% dello strike, sempre inflazionato
            opex = (strike_price * 0.20) * ((1 + inflation)**y)
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
st.subheader("⚙️ Parametri dell'Investimento")
c1, c2, c3 = st.columns(3)

with c1:
    capex_val = st.slider("Investimento (CAPEX) M€", 10, 500, 100, step=10)
    const_time = st.slider("Anni Autorizzazione/Costruzione", 1, 10, 3)
    strike_val = st.slider("Ricavo Annuo (Strike Price) M€", 5, 100, 25)

with c2:
    wacc_base = st.slider("Tasso di Sconto Base (WACC) %", 0.0, 15.0, 7.0) / 100
    infl_val = st.slider("Tasso Inflazione %", 0.0, 10.0, 2.0) / 100
    op_time = st.slider("Anni di Operatività", 10, 30, 20)

with c3:
    st.write("**Clausole e Rischi**")
    indexed = st.checkbox("CFD Indicizzato all'inflazione", value=True)
    risk = st.checkbox("Applica Fattore di Rischio (+3% WACC)", value=False)
    st.info("Il rischio simula incertezza normativa o tecnologica.")

# Esecuzione
df_res, rate_used, capex_real = run_simulation(capex_val, const_time, wacc_base, infl_val, strike_val, op_time, indexed, risk)

# Calcolo VAN in valore assoluto e percentuale rispetto al CAPEX nominale
npv_absolute = df_res['CF_Attualizzato'].sum()
npv_percentage = (npv_absolute / capex_val) * 100

# --- RENDERING RISULTATI ---
with metrics_spot:
    m1, m2, m3 = st.columns(3)
    # Visualizzazione VAN in percentuale
    m1.metric("VAN del Progetto", f"{npv_percentage:.2f} %", 
              delta="Redditizio" if npv_absolute > 0 else "In Perdita", delta_color="normal")
    m2.metric("CAPEX Reale (Capitalizzato)", f"{capex_real:.2f} M€", 
              help="Costo effettivo del debito al momento dell'accensione.")
    
    pb_row = df_res[df_res['VAN_Cumulativo'] > 0]
    pb_val = pb_row['Anno'].min() if not pb_row.empty else "Mai"
    m3.metric("Tempo di Rientro (Anni)", f"{pb_val}")

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
        title=f"Analisi DCF (Tasso applicato: {rate_used*100:.1f}%)",
        xaxis_title="Anni",
        yaxis_title="M€",
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

# --- SPIEGAZIONE E DISCLAIMER ---
st.divider()
exp, disc = st.columns([2, 1])

with exp:
    with st.expander("📚 Analisi del Valore e del Tempo"):
        st.write(f"""
        Il **VAN del Progetto** espresso in percentuale ({npv_percentage:.2f}%) indica il rendimento netto attualizzato 
        rispetto all'esborso nominale di {capex_val} M€. 
        
        **L'effetto del tempo:** Spendere {capex_val} M€ in {const_time} anni non equivale a spenderli oggi. 
        Durante la costruzione, i capitali impiegati non rendono e accumulano 'passività' (costo del denaro). 
        Per questo il **CAPEX Reale** (il debito accumulato all'accensione) è superiore a quello nominale.
        """)

with disc:
    # Disclaimer cliccabile
    with st.expander("⚠️ Disclaimer & Contatti"):
        st.write("""
        I risultati sono stime basate su modelli finanziari semplificati (DCF). 
        Per approfondimenti o consulenze:
        """)
        st.markdown(f"📧 [giovanni@unbelclima.it](mailto:giovanni@unbelclima.it)")
