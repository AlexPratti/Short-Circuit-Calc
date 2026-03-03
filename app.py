import streamlit as st
import pandas as pd
import numpy as np

def main():
    st.set_page_config(page_title="Short-Circuit-Calc Pro", layout="wide")
    st.title("⚡ Gestão de Cargas e Curto-Circuito Industrial")

    # --- 1. CONFIGURAÇÕES DA SUBESTAÇÃO (SIDEBAR) ---
    with st.sidebar:
        st.header("🔌 Parâmetros da SE")
        scc_rede = st.number_input("Scc Concessionária (MVA) [0=Infinita]", value=0.0)
        p_trafo = st.number_input("Potência Trafo (kVA)", value=1000.0)
        v_sec = st.number_input("Tensão (V)", value=380.0)
        z_pct = st.number_input("Impedância Z% (Trafo)", value=5.0)

    # --- 2. CONFIGURAÇÃO DE PAINÉIS (CCMs) ---
    st.header("🏗️ Configuração de Infraestrutura")
    col_ccm = st.columns([1, 3])
    with col_ccm[0]:
        # CAMPO DE ENTRADA PARA QUANTIDADE DE CCMs
        n_ccm = st.number_input("Quantidade de CCMs no Projeto", min_value=1, max_value=20, value=1)
    
    st.divider()

    # --- 3. GESTÃO EDITÁVEL DE MOTORES ---
    st.header("🏭 Tabela de Cargas (Motores)")
    st.info(f"💡 Configure seus motores abaixo. O campo 'CCM Destino' permite selecionar do CCM 1 ao CCM {n_ccm}.")

    if 'df_motores' not in st.session_state:
        st.session_state.df_motores = pd.DataFrame(columns=['Potência (CV)', 'Quantidade', 'Partida', 'CCM Destino'])

    c1, c2 = st.columns(2)
    if c1.button("➕ Adicionar Linha de Motor"):
        nova_linha = pd.DataFrame([{'Potência (CV)': 10.0, 'Quantidade': 1, 'Partida': 'Direta', 'CCM Destino': 1}])
        st.session_state.df_motores = pd.concat([st.session_state.df_motores, nova_linha], ignore_index=True)
        st.rerun()

    if c2.button("🗑️ Limpar Lista Completa"):
        st.session_state.df_motores = pd.DataFrame(columns=['Potência (CV)', 'Quantidade', 'Partida', 'CCM Destino'])
        st.rerun()

    # TABELA COM FILTROS DINÂMICOS
    edited_df = st.data_editor(
        st.session_state.df_motores,
        num_rows="dynamic",
        column_config={
            "Potência (CV)": st.column_config.SelectboxColumn(
                "Potência (CV)", 
                options=[0.25, 0.5, 1, 2, 3, 5, 7.5, 10, 15, 20, 25, 30, 40, 50, 75, 100], 
                required=True
            ),
            "Partida": st.column_config.SelectboxColumn(
                "Tipo de Partida", 
                options=["Direta", "Estrela-Triângulo", "Inversor", "Soft-Starter"], 
                required=True
            ),
            "CCM Destino": st.column_config.SelectboxColumn(
                "CCM Destino", 
                options=list(range(1, int(n_ccm) + 1)), # Limitado pela quantidade de CCMs inserida
                required=True
            ),
            "Quantidade": st.column_config.NumberColumn("Quantidade", min_value=1, step=1)
        },
        use_container_width=True,
        key="editor_motores"
    )
    st.session_state.df_motores = edited_df

    # --- 4. DISTÂNCIAS ---
    st.subheader("📍 Distâncias dos Painéis ao QGBT")
    dist_ccms = {}
    cols_dist = st.columns(4)
    for i in range(int(n_ccm)):
        with cols_dist[i % 4]:
            dist_ccms[i+1] = st.number_input(f"Distância CCM {i+1} (m)", value=20.0, key=f"dist_{i}")

    # --- 5. CÁLCULOS ---
    if st.button("🏁 EXECUTAR CÁLCULOS E GERAR MEMORIAL"):
        if st.session_state.df_motores.empty:
            st.error("Adicione motores à lista para calcular.")
            return

        # Icc do Sistema (Trafo + Rede)
        z_base = (v_sec**2) / (p_trafo * 1000)
        z_t = (z_pct/100) * z_base
        z_r = 0 if scc_rede == 0 else (v_sec**2) / (scc_rede * 1e6)
        icc_trafo = (v_sec / (np.sqrt(3) * (z_r + z_t)))

        # Contribuição dos Motores
        motores_cc = st.session_state.df_motores[st.session_state.df_motores['Partida'].isin(["Direta", "Estrela-Triângulo"])]
        total_cv_cc = (motores_cc['Potência (CV)'] * motores_cc['Quantidade']).sum()
        icc_motores = (total_cv_cc * 1.55) * 4
        
        icc_qgbt = icc_trafo + icc_motores

        st.success(f"### Corrente de Curto-Circuito no QGBT: {icc_qgbt/1000:.2f} kA")

        res_data = []
        for i in range(1, int(n_ccm) + 1):
            mask = st.session_state.df_motores['CCM Destino'] == i
            cv_ccm = (st.session_state.df_motores[mask]['Potência (CV)'] * st.session_state.df_motores[mask]['Quantidade']).sum()
            
            # Atenuação por cabo (estimativa média)
            r_cabo = 0.0002 * dist_ccms[i]
            icc_local = (v_sec / ((v_sec/(icc_qgbt*np.sqrt(3))) + r_cabo)) / np.sqrt(3)
            
            res_data.append({
                "Painel": f"CCM {i}",
                "Carga (CV)": f"{cv_ccm:.1f} CV",
                "Corrente Nom (A)": f"{cv_ccm * 1.55:.1f} A",
                "Icc Local (kA)": f"{icc_local/1000:.2f} kA"
            })
        
        st.table(pd.DataFrame(res_data))

if __name__ == "__main__":
    main()
