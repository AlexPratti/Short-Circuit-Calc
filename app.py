import streamlit as st
import pandas as pd
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

# --- TABELA NBR 5410 ---
TABELA_ENGENHARIA = {
    1.5: {"I": 17.5, "R": 12.1, "X": 0.112}, 2.5: {"I": 24, "R": 7.41, "X": 0.102},
    4: {"I": 32, "R": 4.61, "X": 0.096}, 6: {"I": 41, "R": 3.08, "X": 0.092},
    10: {"I": 57, "R": 1.83, "X": 0.088}, 16: {"I": 76, "R": 1.15, "X": 0.084},
    25: {"I": 101, "R": 0.727, "X": 0.082}, 35: {"I": 125, "R": 0.524, "X": 0.081},
    50: {"I": 151, "R": 0.387, "X": 0.080}, 70: {"I": 192, "R": 0.268, "X": 0.078},
    95: {"I": 232, "R": 0.193, "X": 0.077}, 120: {"I": 269, "R": 0.153, "X": 0.076},
    150: {"I": 309, "R": 0.124, "X": 0.076}, 185: {"I": 353, "R": 0.0991, "X": 0.075},
    240: {"I": 415, "R": 0.0754, "X": 0.075}
}

def main():
    st.set_page_config(page_title="Short-Circuit-Calc Pro", layout="wide")
    st.title("⚡ Analisador de Curto-Circuito e Seletividade Industrial")

    # --- 1. DADOS DA CONCESSIONÁRIA E TRAFO ---
    with st.sidebar:
        st.header("🔌 Entrada de Energia")
        scc_rede = st.number_input("Scc da Concessionária (MVA) [0 = Barra Infinita]", value=0.0)
        p_trafo = st.number_input("Potência Trafo (kVA)", value=1000.0)
        v_sec = st.number_input("Tensão Secundária (V)", value=380.0)
        z_pct = st.number_input("Impedância Z% (Trafo)", value=5.0)

    # --- 2. GESTÃO DINÂMICA DE MOTORES ---
    st.header("🏭 Cadastro de Motores por Grupo")
    if 'lista_motores' not in st.session_state:
        st.session_state.lista_motores = []

    with st.expander("➕ Adicionar Novo Grupo de Motores", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        pot = c1.selectbox("Potência (CV)", [0.25, 0.5, 1, 2, 3, 5, 7.5, 10, 15, 20, 25, 30, 40, 50, 75, 100])
        qtd = c2.number_input("Quantidade", min_value=1, value=1)
        partida = c3.selectbox("Tipo de Partida", ["Direta", "Estrela-Triângulo", "Soft-Starter", "Inversor"])
        ccm_num = c4.number_input("Destino (CCM #)", min_value=1, max_value=7, value=1)
        
        if st.button("Adicionar à Lista"):
            st.session_state.lista_motores.append({"cv": pot, "qtd": qtd, "partida": partida, "ccm": ccm_num})

    if st.session_state.lista_motores:
        st.table(pd.DataFrame(st.session_state.lista_motores))
        if st.button("Limpar Lista"):
            st.session_state.lista_motores = []; st.rerun()

    # --- 3. CCMs E DISTÂNCIAS ---
    st.header("🏗️ Infraestrutura")
    n_ccm = st.number_input("Quantidade de CCMs Ativos", 1, 7, 1)
    dist_ccms = {i+1: st.number_input(f"Distância QGBT ao CCM {i+1} (m)", value=30.0, key=f"d_{i}") for i in range(n_ccm)}

    if st.button("🏁 EXECUTAR CÁLCULOS"):
        # Cálculo da Impedância da Rede
        z_rede = 0
        if scc_rede > 0:
            z_rede = (v_sec**2) / (scc_rede * 1e6) # Impedância da rede refletida no secundário
        
        # Icc no Trafo considerando a Rede
        i_nom_t = p_trafo / (np.sqrt(3) * (v_sec/1000))
        z_trafo = (z_pct/100) * (v_sec**2 / (p_trafo * 1000))
        icc_trafo = (v_sec / (np.sqrt(3) * (z_rede + z_trafo)))

        # Contribuição de Motores (Somente Direta e Estrela-Tri contribuem significativamente)
        contribuem = ["Direta", "Estrela-Triângulo"]
        total_cv_cc = sum([m['qtd'] * m['cv'] for m in st.session_state.lista_motores if m['partida'] in contribuem])
        icc_motores = (total_cv_cc * 1.55) * 4
        icc_qgbt = icc_trafo + icc_motores

        # Resultados por CCM
        res = []
        for id_c in range(1, n_ccm + 1):
            cv_ccm = sum([m['qtd'] * m['cv'] for m in st.session_state.lista_motores if m['ccm'] == id_c])
            i_nom = cv_ccm * 1.55
            # Escolha de bitola (simplificado para o exemplo)
            bitola = next((b for b, d in TABELA_ENGENHARIA.items() if d["I"] >= i_nom), 240)
            r_c = (TABELA_ENGENHARIA[bitola]["R"]/1000) * dist_ccms[id_c]
            icc_c = (v_sec / ((v_sec/(icc_qgbt*np.sqrt(3))) + r_c)) / np.sqrt(3)
            
            res.append({"Painel": f"CCM {id_c}", "Carga Total": f"{cv_ccm} CV", "Icc Local (kA)": f"{icc_c/1000:.2f}"})

        st.success(f"**Corrente de Curto-Circuito no QGBT: {icc_qgbt/1000:.2f} kA**")
        st.table(pd.DataFrame(res))

if __name__ == "__main__":
    main()
