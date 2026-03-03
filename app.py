import streamlit as st
import pandas as pd
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

# --- TABELA TÉCNICA NBR 5410 (Cobre, PVC, 380V) ---
TABELA_ENGENHARIA = {
    1.5:  {"I": 17.5, "R": 12.1,   "X": 0.112},
    2.5:  {"I": 24,   "R": 7.41,   "X": 0.102},
    4:    {"I": 32,   "R": 4.61,   "X": 0.096},
    6:    {"I": 41,   "R": 3.08,   "X": 0.092},
    10:   {"I": 57,   "R": 1.83,   "X": 0.088},
    16:   {"I": 76,   "R": 1.15,   "X": 0.084},
    25:   {"I": 101,  "R": 0.727,  "X": 0.082},
    35:   {"I": 125,  "R": 0.524,  "X": 0.081},
    50:   {"I": 151,  "R": 0.387,  "X": 0.080},
    70:   {"I": 192,  "R": 0.268,  "X": 0.078},
    95:   {"I": 232,  "R": 0.193,  "X": 0.077},
    120:  {"I": 269,  "R": 0.153,  "X": 0.076},
    150:  {"I": 309,  "R": 0.124,  "X": 0.076},
    185:  {"I": 353,  "R": 0.0991, "X": 0.075},
    240:  {"I": 415,  "R": 0.0754, "X": 0.075}
}

def sugerir_disjuntor(i_nom, icc_local):
    frames = [16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 400, 630, 800, 1000, 1250, 1600]
    in_escolhido = next((f for f in frames if f >= i_nom * 1.25), 1600)
    icu_opcoes = [10, 18, 25, 36, 50, 65, 70, 85, 100]
    icu_sugerido = next((ic for ic in icu_opcoes if ic > (icc_local/1000)), 100)
    ir = round(i_nom * 1.1, 1)
    im = round(in_escolhido * 8, 0)
    return f"{in_escolhido}A (Icu: {icu_sugerido}kA)", f"Ir: {ir}A / Im: {im}A"

def calcular_bitola(corrente, dist, v_sec):
    for bitola, d in TABELA_ENGENHARIA.items():
        if d["I"] >= corrente:
            queda = (np.sqrt(3) * corrente * (d["R"]/1000 * 0.85 + d["X"]/1000 * 0.52) * dist)
            queda_pct = (queda / v_sec) * 100
            if queda_pct <= 4.0:
                return bitola, queda_pct
    return 240, 99.0

def gerar_pdf(dados_se, df):
    buf = BytesIO()
    p = canvas.Canvas(buf, pagesize=letter)
    p.setFont("Helvetica-Bold", 16); p.drawString(50, 750, "Memorial de Cálculo: Subestação Industrial")
    p.setFont("Helvetica", 11); p.drawString(50, 730, f"Trafo: {dados_se['p']}kVA | Icc QGBT: {dados_se['icc']:.2f}kA")
    y = 690
    for _, r in df.iterrows():
        p.drawString(50, y, f"{r['Local']} - {r['Carga']} | {r['Bitola']} | {r['Icc Local']} kA | Prot: {r['Disjuntor']}")
        y -= 20
    p.showPage(); p.save(); buf.seek(0)
    return buf

def main():
    st.set_page_config(page_title="Engenharia SE", layout="wide")
    st.title("⚡ Dimensionamento de Subestação e Curto-Circuito")

    with st.sidebar:
        st.header("🔌 Dados da SE")
        p_trafo = st.number_input("Potência Trafo (kVA)", 100.0, 5000.0, 1000.0)
        v_sec = st.number_input("Tensão (V)", 220.0, 440.0, 380.0)
        z_pct = st.number_input("Z% (Impedância)", 1.0, 10.0, 5.0)

    st.header("🏭 CCMs e Motores")
    n_ccm = st.number_input("Quantidade de CCMs", 1, 7, 1)
    
    motores = []
    cvs = [0.25, 0.5, 1, 2, 3, 5, 7.5, 10, 15, 20, 25, 30, 40, 50, 75, 100]
    cols = st.columns(4)
    for i, cv in enumerate(cvs):
        with cols[i % 4]:
            if st.checkbox(f"{cv} CV", key=f"m_{cv}"):
                q = st.number_input("Qtd", 1, 100, 1, key=f"q_{cv}")
                p = st.selectbox("Partida", ["Direta", "Inversor"], key=f"p_{cv}")
                c = st.number_input("CCM destino", 1, n_ccm, 1, key=f"c_{cv}")
                motores.append({"cv": cv, "qtd": q, "partida": p, "ccm": c})

    dist_ccm = {i+1: st.number_input(f"Distância CCM {i+1} (m)", 1.0, 500.0, 30.0) for i in range(n_ccm)}

    if st.button("🚀 CALCULAR SISTEMA"):
        # Icc no Trafo + Motores
        i_nom_t = p_trafo / (np.sqrt(3) * (v_sec/1000))
        icc_t = i_nom_t / (z_pct/100)
        contrib_m = sum([m['qtd']*m['cv']*1.55*4 for m in motores if m['partida'] == "Direta"])
        icc_qgbt = icc_t + contrib_m

        res = []
        for id_c in range(1, n_ccm + 1):
            cv_total = sum([m['qtd']*m['cv'] for m in motores if m['ccm'] == id_c])
            i_nom = cv_total * 1.55
            bitola, q_v = calcular_bitola(i_nom, dist_ccm[id_c], v_sec)
            r_c = (TABELA_ENGENHARIA[bitola]["R"]/1000) * dist_ccm[id_c]
            icc_c = (v_sec / ((v_sec/(icc_qgbt*np.sqrt(3))) + r_c)) / np.sqrt(3)
            dj, aj = sugerir_disjuntor(i_nom, icc_c)

            res.append({"Local": f"CCM {id_c}", "Carga": f"{cv_total} CV", "Bitola": f"{bitola} mm²", 
                        "Queda V%": f"{q_v:.2f}%", "Icc Local": f"{icc_c/1000:.2f}", "Disjuntor": dj, "Ajustes": aj})

        df = pd.DataFrame(res)
        st.table(df)
        st.warning(f"**Icc no QGBT: {icc_qgbt/1000:.2f} kA**")
        
        pdf = gerar_pdf({"p": p_trafo, "v_sec": v_sec, "icc": icc_qgbt/1000}, df)
        st.download_button("📥 Baixar PDF", pdf, "memorial_se.pdf", "application/pdf")

if __name__ == "__main__":
    main()
