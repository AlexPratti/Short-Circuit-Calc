import streamlit as st
import pandas as pd
import numpy as np

def main():
    st.set_page_config(page_title="Short-Circuit-Calc Pro", layout="wide")
    st.title("⚡ Gestão de Cargas e Dimensionamento Industrial")

    # --- 1. CONFIGURAÇÕES DA SUBESTAÇÃO (SIDEBAR) ---
    with st.sidebar:
        st.header("🔌 Parâmetros da SE")
        scc_rede = st.number_input("Scc Concessionária (MVA) [0=Infinita]", value=0.0)
        p_trafo = st.number_input("Potência Trafo (kVA)", value=1000.0)
        v_sec = st.number_input("Tensão (V)", value=380.0)
        z_pct = st.number_input("Impedância Z% (Trafo)", value=5.0)
        
        st.divider()
        st.header("📏 Distâncias de Alimentação")
        dist_se_qgbt = st.number_input("Distância SE ao QGBT (m)", value=10.0, min_value=1.0)
        queda_max = st.number_input("Queda de Tensão Máxima Permitida (%)", value=4.0)

    # --- 2. CONFIGURAÇÃO DE INFRAESTRUTURA ---
    n_ccm = st.number_input("Quantidade de CCMs no Projeto", min_value=1, max_value=20, value=1)
    
    # Inputs de distância QGBT -> CCMs
    st.subheader("📍 Distâncias do QGBT aos CCMs")
    dist_ccms = {}
    cols_dist = st.columns(4)
    for i in range(int(n_ccm)):
        with cols_dist[i % 4]:
            dist_ccms[i+1] = st.number_input(f"Distância CCM {i+1} (m)", value=20.0, key=f"dist_{i}")

    st.divider()

    # --- 3. INICIALIZAÇÃO DO ESTADO ---
    if 'df_motores' not in st.session_state:
        st.session_state.df_motores = pd.DataFrame(columns=['Selecionar', 'Potência (CV)', 'Quantidade', 'Partida', 'CCM Destino', 'Status'])

    # --- 4. CADASTRO DE NOVO MOTOR ---
    st.header("📋 Cadastro de Novo Motor")
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            opcoes_pot = [0.25, 0.5, 1, 2, 3, 5, 7.5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 125, 150, 200]
            pot_input = st.selectbox("Potência (CV)", options=opcoes_pot, index=None, placeholder="0.00")
        with c2:
            qtd_input = st.number_input("Quantidade", min_value=1, value=1)
        with c3:
            partida_input = st.selectbox("Tipo de Partida", options=["Direta", "Estrela-Triângulo", "Inversor", "Soft-Starter"])
        with c4:
            ccm_input = st.selectbox("CCM Destino", options=list(range(1, int(n_ccm) + 1)))

        if st.button("➕ Adicionar Motor à Lista", type="primary", use_container_width=True):
            if pot_input is not None:
                if not st.session_state.df_motores.empty:
                    st.session_state.df_motores['Status'] = 'Antigo'
                
                nova_linha = pd.DataFrame([{
                    'Selecionar': False, 'Potência (CV)': float(pot_input), 'Quantidade': int(qtd_input), 
                    'Partida': partida_input, 'CCM Destino': int(ccm_input), 'Status': 'Novo'
                }])
                st.session_state.df_motores = pd.concat([st.session_state.df_motores, nova_linha], ignore_index=True)
                st.rerun()

    # --- 5. TABELA DE GESTÃO (EDITÁVEL) ---
    if not st.session_state.df_motores.empty:
        st.header("🏭 Motores na Lista (Editável)")
        
        col_exc, col_lim = st.columns([1, 1])
        with col_exc:
            if st.button("🗑️ Excluir Selecionados"):
                st.session_state.df_motores = st.session_state.df_motores[st.session_state.df_motores['Selecionar'] == False]
                st.rerun()
        with col_lim:
            if st.button("✨ Limpar Tudo"):
                st.session_state.df_motores = pd.DataFrame(columns=['Selecionar', 'Potência (CV)', 'Quantidade', 'Partida', 'CCM Destino', 'Status'])
                st.rerun()

        def estilo_azul(row):
            return ['background-color: #0047AB; color: white; font-weight: bold' if row['Status'] == 'Novo' else '' for _ in row]

        # Tabela agora permite edição (disabled=False para os campos desejados)
        edited_df = st.data_editor(
            st.session_state.df_motores.style.apply(estilo_azul, axis=1),
            column_config={
                "Selecionar": st.column_config.CheckboxColumn("Excluir?", default=False),
                "Status": None,
                "Potência (CV)": st.column_config.NumberColumn("Potência (CV)", format="%.2f", min_value=0.1),
                "Quantidade": st.column_config.NumberColumn("Qtd", min_value=1),
                "Partida": st.column_config.SelectboxColumn("Partida", options=["Direta", "Estrela-Triângulo", "Inversor", "Soft-Starter"]),
                "CCM Destino": st.column_config.SelectboxColumn("Destino", options=list(range(1, int(n_ccm) + 1))),
            },
            use_container_width=True,
            key="tabela_editavel_v5"
        )
        st.session_state.df_motores = edited_df

        # --- 6. CÁLCULOS E PROTEÇÕES ---
        st.divider()
        if st.button("🚀 EXECUTAR CÁLCULOS E DIMENSIONAMENTO", type="secondary", use_container_width=True):
            # 1. Corrente e Icc no QGBT
            total_cv = (st.session_state.df_motores['Potência (CV)'] * st.session_state.df_motores['Quantidade']).sum()
            in_qgbt = (total_cv * 736) / (v_sec * np.sqrt(3) * 0.85 * 0.9) # Estimativa de In com rendimento/fp
            
            z_base = (v_sec**2) / (p_trafo * 1000)
            z_t = (z_pct/100) * z_base
            z_r = 0 if scc_rede == 0 else (v_sec**2) / (scc_rede * 1e6)
            icc_qgbt = (v_sec / (np.sqrt(3) * (z_r + z_t)))

            st.success(f"### QGBT: In = {in_qgbt:.1f} A | Icc = {icc_qgbt/1000:.2f} kA")
            
            # 2. Resultados por CCM
            res_data = []
            for i in range(1, int(n_ccm) + 1):
                mask = st.session_state.df_motores['CCM Destino'] == i
                cv_ccm = (st.session_state.df_motores[mask]['Potência (CV)'] * st.session_state.df_motores[mask]['Quantidade']).sum()
                if cv_ccm == 0: continue
                
                in_ccm = (cv_ccm * 736) / (v_sec * np.sqrt(3) * 0.85 * 0.9)
                dist = dist_ccms[i]
                
                # Critério de Queda de Tensão (Simplificado: rho_cu = 1/56)
                # Seção = (sqrt(3) * L * I * cosphi) / (V_queda)
                v_queda_limite = v_sec * (queda_max/100)
                secao_queda = (np.sqrt(3) * dist * in_ccm * 0.85) / (56 * v_queda_limite)
                
                # Sugestão de Disjuntor (In * 1.25)
                disjuntor = in_ccm * 1.25
                
                res_data.append({
                    "Painel": f"CCM {i}",
                    "Carga (CV)": f"{cv_ccm:.1f}",
                    "In (A)": f"{in_ccm:.1f}",
                    "Disjuntor Sugerido": f"{disjuntor:.0f} A",
                    "Seção Mín. (ΔV)": f"{max(secao_queda, 2.5):.1f} mm²",
                    "Icc Local (kA)": f"{(icc_qgbt * 0.9)/1000:.2f}"
                })
            
            st.subheader("📊 Memória de Cálculo e Proteções")
            st.table(pd.DataFrame(res_data))
            st.info("⚠️ Nota: O dimensionamento de cabos considera queda de tensão. Verifique a capacidade de condução por agrupamento.")
    else:
        st.info("👆 Adicione motores para iniciar o dimensionamento.")

if __name__ == "__main__":
    main()
