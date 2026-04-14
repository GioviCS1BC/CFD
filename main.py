import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Configurazione pagina
st.set_page_config(page_title="Analisi CFD e Rischio", layout="wide")

st.title("📉 Analisi CFD: Impatto Inflazione e Rischio")
st.markdown("""
Visualizza come il valore del tuo investimento cambia in base ai tempi di autorizzazione, all'inflazione e al profilo di rischio.
""")

# --- LOGICA DI CALCOLO ---
def calculate_cfd(discount_rate, const_years, capes, inflation, strike_price, op_life, is_indexed, has_risk):
    # Se c'è rischio, aumentiamo il tasso di sconto (premio al rischio del 3%)
    effective_rate = discount_rate + (0.03 if has_risk else 0)
    
    years = np.arange(0, const_years + op_life + 1)
    df = pd.DataFrame({'Anno': years})
    
    capex_per_year = capex / const_years if const_years > 0 else capex
    
    cash_flows = []
    for year in years:
        if year == 0:
            cf = 0
        elif 1 <= year <= const_years:
            cf = -capex_per_year
        else:
            # Ricavo: indicizzato o fisso
            if is_indexed:
                revenue = strike_price * ((1 + inflation)**year)
            else:
                revenue = strike_price
            
            # OPEX (costi operativi) - assunti al 20% dello strike iniziale, indicizzati
            opex = (strike_price * 0.2) * ((1 + inflation)**year)
            cf = revenue - opex
            
        cash_flows.append(cf)
    
    df['CF_Nominale'] = cash_flows
    # Attualizzazione con il tasso effettivo (base + eventuale rischio)
    df['CF_Attualizzato'] = df['CF_Nominale'] / ((1 + effective_rate)**df['Anno'])
    df['VAN_Cumulativo'] = df['CF_Attualizzato'].cumsum()
    
    return df, effective_rate

# --- CONTENITORE GRAFICO ---
chart_placeholder = st.empty()
metric_placeholder = st.empty()

st.divider()

# --- PARAMETRI (Sotto il grafico) ---
st.subheader("⚙️ Parametri del Modello")
col1, col2, col3 = st.columns(3)

with col1:
    capex = st.slider("Investimento (CAPEX) M€", 10, 500, 100)
    const_years = st.slider("Anni Autorizzazione/Costruzione", 1, 10, 3)
    strike_price = st.slider("Ricavo Annuo (Strike Price) M€", 5, 100, 25)

with col2:
    discount_rate = st.slider("Tasso di Sconto Base (WACC) %", 0.0, 15.0, 7.0) / 100
    inflation = st.slider("Tasso Inflazione %", 0.0, 10.0, 2.0) / 100
    op_life = st.slider("Anni di Operatività", 10, 30, 20)

with col3:
    st.markdown("**Opzioni Contrattuali**")
    is_indexed = st.checkbox("CFD Indicizzato all'inflazione", value=True)
    
    st.markdown("**⚠️ Profilo di Rischio**")
    has_risk = st.checkbox("Applica Fattore di Rischio (+3% WACC)")
    if has_risk:
        st.warning("Il tasso di sconto è aumentato per riflettere il rischio.")

# Esecuzione calcolo
df_res, rate_effettivo = calculate_cfd(discount_rate, const_years, capex, inflation, strike_price, op_life, is_indexed, has_risk)
npv_finale = df_res['CF_Attualizzato'].sum()

# --- AGGIORNAMENTO METRICHE ---
with metric_placeholder:
    m1, m2, m3 = st.columns(3)
    m1.metric("VAN (Valore Attuale Netto)", f"{npv_finale:.2f} M€")
    m2.metric("Tasso di Sconto Applicato", f"{rate_effettivo*100:.1f} %")
    payback = df_res[df_res['VAN_Cumulativo'] > 0]['Anno'].min()
    m3.metric("Rientro (Payback Period)", f"{payback if pd.notnull(payback) else 'Mai'} Anni")

# --- AGGIORNAMENTO GRAFICO ---
with chart_placeholder:
    fig = go.Figure()
    
    # Bar Chart per i flussi annuali
    fig.add_trace(go.Bar(
        x=df_res['Anno'], 
        y=df_res['CF_Attualizzato'],
        name='Flusso Attualizzato',
        marker_color='rgba(55, 128, 191, 0.7)'
    ))
    
    # Line Chart per il VAN cumulativo
    fig.add_trace(go.Scatter(
        x=df_res['Anno'], 
        y=df_res['VAN_Cumulativo'],
        name='VAN Cumulativo',
        line=dict(color='firebrick', width=4)
    ))

    fig.update_layout(
        height=500,
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        template="plotly_white",
        yaxis_title="Milioni di Euro (M€)",
        xaxis_title="Anni"
    )
    st.plotly_chart(fig, use_container_width=True)

# Spiegazione per l'utente
st.info(f"""
**Cosa succede se attivi il rischio?** L'attivazione del fattore di rischio simula una situazione in cui il mercato o le banche percepiscono il progetto come meno sicuro. 
Matematicamente, il denominatore della formula di attualizzazione $(1 + r)^n$ aumenta, rendendo i profitti degli anni futuri (quelli dopo il {const_years}° anno) molto meno pesanti nel calcolo di oggi.
""")
