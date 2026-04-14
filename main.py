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
    effective_rate = discount_rate + (0.03 if has_risk else 0)
    total_years = const_years + op_life
    years = np.arange(0, total_years + 1)
    df = pd.DataFrame({'Anno': years})
    
    cash_flows = []
    for y in years:
        if y == 0:
            cf = 0
        elif 1 <= y <= const_years:
            cf = -(capex / const_years)
        else:
            rev = annual_revenue * ((1 + inflation)**y) if is_indexed else annual_revenue
            opex = annual_opex_base * ((1 + inflation)**y)
            cf = rev - opex
        cash_flows.append(cf)
    
    df['CF_Nominale'] = cash_flows
    df['CF_Attualizzato'] = df['CF_Nominale'] / ((1 + effective_rate)**df['Anno'])
    df['VAN_Cumulativo'] = df['CF_Attualizzato'].cumsum()
    
    capex_cap = sum([(capex/const_years) * ((1 + effective_rate)**(const_years - y)) for y in range(1, const_years + 1)])
    return df, effective_rate, capex_cap

# --- DEFINIZIONE PRESET TECNOLOGIE ---
presets = {
    "Manuale": None,
    "Fotovoltaico": {"mw": 100, "costo_w": 0.8, "om": 10.0, "const": 1, "cf": 18, "strike": 60, "life": 25, "wacc": 5.0},
    "Eolico a terra": {"mw": 100, "costo_w": 1.3, "om": 15.0, "const": 2, "cf": 25, "strike": 70, "life": 25, "wacc": 5.0},
    "Nucleare (Large)": {"mw": 1600, "costo_w": 7.0, "om": 15.0, "const": 10, "cf": 90, "strike": 90, "life": 60, "wacc": 7.0},
    "SMR (Small Modular Reactor)": {"mw": 300, "costo_w": 5.5, "om": 18.0, "const": 4, "cf": 90, "strike": 100, "life": 60, "wacc": 7.0}
}

# --- INTERFACCIA GRAFICA ---
chart_spot = st.empty()
metrics_spot = st.empty()

st.divider()

# --- INPUT PARAMETERS ---
st.subheader("⚙️ Selezione Tecnologia e Parametri")

scelta_tech = st.selectbox("Seleziona una Tecnologia (carica preset)", list(presets.keys()))
p = presets[scelta_tech]

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("**🛠️ Dati Impianto e Costi**")
    # Aggiunto int() e float() per garantire coerenza nei tipi di dato degli slider
    potenza_mw = st.slider("Potenza Impianto (MW)", 1, 3500, int(p["mw"]) if p else 1000, step=10)
    costo_watt = st.slider("CAPEX: Costo al Watt (€/W)", 0.1, 12.0, float(p["costo_w"]) if p else 5.0, step=0.1)
    om_mwh = st.slider("OPEX: Costo O&M (€/MWh)", 1.0, 100.0, float(p["om"]) if p else 15.0, step=1.0)
    const_time = st.slider("Anni Autorizzazione/Costruzione", 1, 20, int(p["const"]) if p else 8)

with c2:
    st.markdown("**⚡ Produzione e Mercato**")
    capacity_factor = st.slider("Capacity Factor (%)", 5, 100, int(p["cf"]) if p else 90) / 100
    strike_mwh = st.slider("Strike Price (€/MWh)", 20, 300, int(p["strike"]) if p else 80, step=5)
    op_time = st.slider("Anni di Operatività", 10, 80, int(p["life"]) if p else 60)

with c3:
    st.markdown("**📉 Finanza e Rischio**")
    wacc_base = st.slider("Tasso di Sconto Base (WACC) %", 0.0, 15.0, float(p["wacc"]) if p else 6.0, step=0.5) / 100
    infl_val = st.slider("Tasso Inflazione %", 0.0, 10.0, 2.0, step=0.5) / 100
    
    st.write("**Clausole Contrattuali**")
    indexed = st.checkbox("CFD Indicizzato all'inflazione", value=True)
    risk = st.checkbox("Applica Fattore di Rischio (+3% WACC)", value=False)

# --- CALCOLI ---
capex_val = potenza_mw * costo_watt
produzione_annua_mwh = potenza_mw * 8760 * capacity_factor
ricavo_annuo_meuro = (produzione_annua_mwh * strike_mwh) / 1_000_000
opex_annuo_meuro = (produzione_annua_mwh * om_mwh) / 1_000_000

df_res, rate_used, capex_real = run_simulation(capex_val, const_time, wacc_base, infl_val, ricavo_annuo_meuro, opex_annuo_meuro, op_time, indexed, risk)

npv_absolute = df_res['CF_Attualizzato'].sum()
npv_percentage = (npv_absolute / capex_val) * 100
tir_valore = calcola_tir(df_res['CF_Nominale'].tolist()) * 100

# --- RENDERING RISULTATI ---
with metrics_spot:
    st.caption(f"📊 **Dati Derivati:** Inv. Nominale: **{capex_val:,.1f} M€** | Produzione: **{produzione_annua_mwh:,.0f} MWh/anno**")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("VAN del Progetto", f"{npv_percentage:.2f} %", delta="Redditizio" if npv_absolute > 0 else "In Perdita", delta_color="normal")
    m2.metric("TIR (Rendimento Annuo)", f"{tir_valore:.2f} %")
    m3.metric("CAPEX Reale (Capitalizzato)", f"{capex_real:.2f} M€")
    
    pb_row = df_res[df_res['VAN_Cumulativo'] > 0]
    pb_val = pb_row['Anno'].min() if not pb_row.empty else "Mai"
    m4.metric("Tempo di Rientro (Anni)", f"{pb_val}")

with chart_spot:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_res['Anno'], y=df_res['CF_Attualizzato'], name="Cash Flow Attualizzato", marker_color=np.where(df_res['CF_Attualizzato'] < 0, '#EF553B', '#00CC96')))
    fig.add_trace(go.Scatter(x=df_res['Anno'], y=df_res['VAN_Cumulativo'], name="VAN Cumulativo", line=dict(color='white', width=3)))
    fig.update_layout(height=500, template="plotly_dark", title=f"Analisi DCF ({scelta_tech}) - WACC: {rate_used*100:.1f}%", xaxis_title="Anni", yaxis_title="M€", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

# --- SPIEGAZIONE E DISCLAIMER ---
st.divider()
exp, disc = st.columns([2, 1])

with exp:
    with st.expander("📚 Analisi del Valore e del Tempo"):
        st.write(f"""
        Il **VAN del Progetto** ({npv_percentage:.2f}%) mostra quanto valore crei oltre il recupero del capitale e del WACC. 
        Confronta il **Fotovoltaico** (rientro veloce, basso impatto del tempo) con il **Nucleare** (rientro lento, enorme impatto degli interessi di costruzione).
        """)

with disc:
    with st.expander("⚠️ Disclaimer & Contatti"):
        st.write("I risultati sono stime basate su modelli semplificati.")
        st.markdown(f"📧 [giovanni@unbelclima.it](mailto:giovanni@unbelclima.it)")
