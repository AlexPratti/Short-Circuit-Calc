import streamlit as st
import pandas as pd
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

# --- TABELA NBR 5410 (Simplificada para o exemplo) ---
TABELA_ENGENHARIA = {
    1.5: 17.5, 2.5: 24, 4: 32, 6: 41, 10: 57, 16: 76, 25: 101, 
    35: 125, 50: 151, 70: 192, 95: 232, 120: 269, 150: 309, 185: 353, 240: 415
}

def main():
    st.set_page_config(page_title="Short-Circuit-Calc Pro", layout="wide")
    st.title("⚡ Gerenciamento de Cargas e Curto-Circuito Industrial")

    # --- 1. DADOS DA CONCESSIONÁRIA E TRAFO ---
    with st.sidebar:
        st.header("🔌 Entrada de Energia")
        scc_rede = st.number_input("Scc da Concessionária (MVA) [0 = Barra Infinita]", value=0.0, help="Potência de curto-circuito no ponto de entrega.")
        p_trafo = st.number_input("Potência Trafo (kVA)", value=1000.0)
        v_sec = st.number_input("Tensão Secundária (V)", value=380.0)
        z_pct = st.number_input("Impedância Z% (Trafo)", value=5.0)

    # --- 2. GESTÃO EDITÁVEL DE MOTORES ---
    st.header("🏭 Cadastro e Edição de Motores")
    st.info("💡 Você pode editar os valores diretamente na tabela abaixo. Para excluir, selecione a linha e pressione 'Delete' ou use o ícone de lixeira.")

    # Inicializa o DataFrame no estado da sessão se não existir
    if 'df_motores' not in st.session_state:
        st.session_state.df_motores = pd.DataFrame(columns=['Potência (CV)', 'Quantidade', 'Partida', 'CCM Destino'])

    # Botões de ação rápida
    col_btn1, col_btn2 = st.columns([1, 5])
    if col_btn1.button("➕ Adicionar Linha"):
        nova_linha = pd.DataFrame([{'Potência (CV)': 10.0, 'Quantidade': 1, 'Partida': 'Direta', 'CCM Destino': 1}])
        st.session_state.df_motores = pd.concat([st.session_state.df_motores, nova_linha], ignore_index=True)
        st.rerun()

    if col_btn2.button("🗑️ Limpar Lista Completa"):
        st.session_state.df_motores = pd.DataFrame(columns=['Potência (CV)', 'Quantidade', 'Partida', 'CCM Destino'])
        st.rerun()

    # Tabela Editável
    edited_df = st.data_editor(
        st.session_state.df_motores,
        num_rows="dynamic", # Permite adicionar/remover linhas pela interface do componente
        column_config={
            "Potência (CV)": st.column_config.SelectboxColumn("Potência (CV)", options=[0.25, 0.5, 1, 2, 3, 5, 7.5, 10, 15, 20, 25, 30, 40, 50, 75, 100], required=True),
            "Quantidade": st.column_config.NumberColumn("Quantidade", min_value=1, step=1, required=True),
            "Partida": st.column_config.SelectboxColumn("Partida", options=["Direta", "Estrela-Triângulo", "Soft-Starter", "Inversor"], required=True),
            "CCM Destino": st.column_config.NumberColumn("CCM #", min_value=1, max_value=7, step=1, required=True),
        },
        hide_index=False,
        use_container_width=True,
        key="editor_motores"
    )

    # Atualiza o estado global com as edições feitas na tabela
    st.session_state.df_motores = edited_df

    # --- 3. CCMs E DISTÂNCIAS ---
    st.divider()
    st.header("🏗️ Infraestrutura de Cabos")
    n_ccm = st.number_input("Quantidade de CCMs Ativos", 1, 7, 1)
    dist_ccms = {i+1: st.number_input(f"Distância QGBT ao CCM {i+1} (m)", value=30.0, key=f"dist_{i}") for i in range(n_ccm)}

    # --- 4. CÁLCULOS ---
    if st.button("🏁 EXECUTAR CÁLCULOS TÉCNICOS"):
        if st.session_state.df_motores.empty:
            st.warning("⚠️ Adicione ao menos um motor para realizar o cálculo.")
        else:
            # Cálculo Icc Rede + Trafo
            z_base = (v_sec**2) / (p_trafo * 1000)
            z_trafo_ohm = (z_pct/100) * z_base
            z_rede_ohm = 0 if scc_rede == 0 else (v_sec**2) / (scc_rede * 1e6)
            
            icc_trafo = (v_sec / (np.sqrt(3) * (z_rede_ohm + z_trafo_ohm)))

            # Contribuição Motores
            contribuem = ["Direta", "Estrela-Triângulo"]
            mask = st.session_state.df_motores['Partida'].isin(contribuem)
            total_cv_cc = (st.session_state.df_motores[mask]['Potência (CV)'] * st.session_state.df_motores[mask]['Quantidade']).sum()
            icc_motores = (total_cv_cc * 1.55) * 4
            
            icc_qgbt = icc_trafo + icc_motores

            # Tabela de Resultados
            res = []
            for id_c in range(1, n_ccm + 1):
                mask_ccm = st.session_state.df_motores['CCM Destino'] == id_c
                cv_ccm = (st.session_state.df_motores[mask_ccm]['Potência (CV)'] * st.session_state.df_motores[mask_ccm]['Quantidade']).sum()
                i_nom = cv_ccm * 1.55
                
                # Cálculo simplificado de atenuação
                r_estimado = 0.0002 * dist_ccms[id_c] # 0.2mOhm por metro (estimativa rápida)
                icc_c = (v_sec / ((v_sec/(icc_qgbt*np.sqrt(3))) + r_estimado)) / np.sqrt(3)
                
                res.append({
                    "Painel": f"CCM {id_c}",
                    "Carga Total": f"{cv_ccm:.1f} CV",
                    "I Nominal (A)": f"{i_nom:.1f} A",
                    "Icc Estimada (kA)": f"{icc_c/1000:.2f} kA"
                })

            st.success(f"### Corrente de Curto-Circuito no QGBT: {icc_qgbt/1000:.2f} kA")
            st.table(pd.DataFrame(res))

if __name__ == "__main__":
    main()
