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
    effective_rate = discount_rate + (0.04 if has_risk else 0)
    
    total_years = const_years + op_life
    years = np.arange(0, total_years + 1)
    
    df = pd.DataFrame({'Anno': years})
    
    # 1. Flussi di Cassa Nominali
    cash_flows = []
    accumulated_investment = 0
    
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
            # OPEX: stimato al 25% dello strike, sempre inflazionato
            opex = (strike_price * 0.25) * ((1 + inflation)**y)
            cf = rev - opex
        cash_flows.append(cf)
    
    df['CF_Nominale'] = cash_flows
    
    # 2. Attualizzazione (Discounting al Tempo 0)
    df['CF_Attualizzato'] = df['CF_Nominale'] / ((1 + effective_rate)**df['Anno'])
    
    # 3. Calcolo del VAN Cumulativo
    df['VAN_Cumulativo'] = df['CF_Attualizzato'].cumsum()
    
    # 4. Calcolo CAPEX "Capitalizzato" (IDC - Interest During Construction)
    # Mostra quanto pesano i soldi spesi durante la costruzione portati al "tempo di accensione"
    capex_cap = sum([(capex/const_years) * ((1 + effective_rate)**(const_years - y)) for y in range(1, const_years + 1)])
    
    return df, effective_rate, capex_cap

# --- INTERFACCIA GRAFICA ---
# Placeholder per i risultati (verranno riempiti dopo che i parametri sono letti sotto)
chart_spot = st.empty()
metrics_spot = st.empty()

st.divider()

# --- INPUT PARAMETERS (Sotto il grafico) ---
st.subheader("⚙️ Parametri dell'Investimento")
c1, c2, c3 = st.columns(3)

with c1:
    capex_val = st.slider("Investimento Nominale (M€)", 100, 5000, 1000, step=100)
    const_time = st.slider("Anni di Costruzione/Autorizzazione", 1, 15, 7)
    op_time = st.slider("Vita Operativa (Anni)", 10, 60, 30)

with c2:
    wacc_base = st.slider("Tasso di Sconto Base (WACC) %", 1.0, 15.0, 5.0) / 100
    infl_val = st.slider("Tasso Inflazione %", 0.0, 10.0, 2.0) / 100
    strike_val = st.slider("Ricavo Annuo Target (M€)", 50, 1000, 250)

with c3:
    st.write("**Clausole e Rischi**")
    indexed = st.checkbox("CFD Indicizzato (Protezione Inflazione)", value=True)
    risk = st.checkbox("Aggiungi Premio al Rischio (+4% WACC)", value=False)
    st.info("Il rischio simula incertezza normativa o tecnologica.")

# Esecuzione
df_res, rate_used, capex_real = run_simulation(capex_val, const_time, wacc_base, infl_val, strike_val, op_time, indexed, risk)
npv_final = df_res['CF_Attualizzato'].sum()

# --- RENDERING RISULTATI ---
with metrics_spot:
    m1, m2, m3 = st.columns(3)
    m1.metric("VAN del Progetto", f"{npv_final:.2f} M€", 
              delta="Redditizio" if npv_final > 0 else "In Perdita", delta_color="normal")
    m2.metric("CAPEX Reale (Capitalizzato)", f"{capex_real:.2f} M€", 
              help="Questo è il costo effettivo del debito al momento dell'accensione, includendo gli interessi durante la costruzione.")
    
    # Calcolo Payback Attualizzato
    pb_row = df_res[df_res['VAN_Cumulativo'] > 0]
    pb_val = pb_row['Anno'].min() if not pb_row.empty else "Mai"
    m3.metric("Tempo di Rientro (Anni)", f"{pb_val}")

with chart_spot:
    fig = go.Figure()
    
    # Bar Chart per flussi annuali
    fig.add_trace(go.Bar(
        x=df_res['Anno'], y=df_res['CF_Attualizzato'],
        name="Cash Flow Attualizzato",
        marker_color=np.where(df_res['CF_Attualizzato'] < 0, '#EF553B', '#00CC96')
    ))
    
    # Linea VAN Cumulativo
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

# --- SPIEGAZIONE DIDATTICA ---
with st.expander("📚 Perché il CAPEX Reale è più alto di quello Nominale?"):
    st.write(f"""
    Come evidenziato nella tua analisi, spendere **{capex_val} M€** in **{const_time} anni** non equivale a spenderli oggi.
    
    Durante la costruzione, ogni euro investito genera una 'passività' (interessi passivi o costo opportunità). 
    Al termine del cantiere (anno {const_time}), il valore del debito accumulato è di **{capex_real:.2f} M€**.
    
    **Le tre leve del grafico:**
    1. **Tasso di Sconto:** Più è alto, più il 'peso' del debito accumulato schiaccia il progetto.
    2. **Tempo di Costruzione:** Più è lungo, più la linea rossa scende prima di iniziare a risalire.
    3. **Indicizzazione:** Se disattivata, vedrai che i profitti futuri (barre verdi) si rimpiccioliscono col tempo a causa dell'inflazione che mangia i margini.
    """)
