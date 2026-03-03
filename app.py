import streamlit as st
import pandas as pd
import numpy as np

def main():
    st.set_page_config(page_title="Short-Circuit-Calc Pro", layout="wide")
    st.title("⚡ Gestão de Cargas e Curto-Circuito Industrial")

    # --- 1. CONFIGURAÇÕES DA SUBESTAÇÃO ---
    with st.sidebar:
        st.header("🔌 Parâmetros da SE")
        scc_rede = st.number_input("Scc Concessionária (MVA) [0=Infinita]", value=0.0)
        p_trafo = st.number_input("Potência Trafo (kVA)", value=1000.0)
        v_sec = st.number_input("Tensão (V)", value=380.0)
        z_pct = st.number_input("Impedância Z% (Trafo)", value=5.0)

    # --- 2. CONFIGURAÇÃO DE INFRAESTRUTURA ---
    n_ccm = st.number_input("Quantidade de CCMs no Projeto", min_value=1, max_value=20, value=1)
    st.divider()

    # --- 3. INICIALIZAÇÃO DO ESTADO ---
    if 'df_motores' not in st.session_state:
        # Criamos o DF inicial com a coluna 'Selecionar' para exclusão
        st.session_state.df_motores = pd.DataFrame([
            {'Selecionar': False, 'Potência (CV)': 10.0, 'Quantidade': 1, 'Partida': 'Direta', 'CCM Destino': 1, 'Novo': False}
        ])

    # --- 4. GESTÃO DE MOTORES (BOTÕES) ---
    st.header("🏭 Tabela de Cargas (Motores)")
    
    col_btn1, col_btn2, col_btn3, _ = st.columns([1, 1.2, 1.2, 2])
    
    with col_btn1:
        if st.button("➕ Adicionar Linha"):
            # Marcamos as linhas antigas como 'Novo: False' e a nova como 'True'
            st.session_state.df_motores['Novo'] = False
            nova_linha = pd.DataFrame([{'Selecionar': False, 'Potência (CV)': 10.0, 'Quantidade': 1, 'Partida': 'Direta', 'CCM Destino': 1, 'Novo': True}])
            st.session_state.df_motores = pd.concat([st.session_state.df_motores, nova_linha], ignore_index=True)
            st.rerun()

    with col_btn2:
        if st.button("🗑️ Excluir Selecionados", type="secondary"):
            # Filtra apenas as linhas que não estão marcadas para seleção
            st.session_state.df_motores = st.session_state.df_motores[st.session_state.df_motores['Selecionar'] == False]
            st.rerun()

    with col_btn3:
        if st.button("💣 Limpar Lista Completa", type="primary"):
            st.session_state.df_motores = pd.DataFrame(columns=['Selecionar', 'Potência (CV)', 'Quantidade', 'Partida', 'CCM Destino', 'Novo'])
            st.rerun()

    # --- 5. TABELA COLORIDA E EDITÁVEL ---
    # Função para colorir linhas novas
    def colorir_novos(row):
        return ['background-color: #e8f4f8' if row['Novo'] else '' for _ in row]

    # Aplicando estilo
    df_estilizado = st.session_state.df_motores.style.apply(colorir_novos, axis=1)

    edited_df = st.data_editor(
        df_estilizado,
        column_config={
            "Selecionar": st.column_config.CheckboxColumn("Excluir?", default=False),
            "Potência (CV)": st.column_config.SelectboxColumn(options=[0.25, 0.5, 1, 2, 3, 5, 7.5, 10, 15, 20, 25, 30, 40, 50, 75, 100]),
            "Partida": st.column_config.SelectboxColumn(options=["Direta", "Estrela-Triângulo", "Inversor", "Soft-Starter"]),
            "CCM Destino": st.column_config.SelectboxColumn(options=list(range(1, int(n_ccm) + 1))),
            "Novo": None # Esconde a coluna técnica de controle de cor
        },
        disabled=["Novo"],
        use_container_width=True,
        key="editor_motores"
    )
    # Sincroniza as edições (incluindo os checkboxes) de volta para o state
    st.session_state.df_motores = edited_df

    # --- 6. DISTÂNCIAS ---
    st.subheader("📍 Distâncias ao QGBT")
    dist_ccms = {}
    cols_dist = st.columns(4)
    for i in range(int(n_ccm)):
        with cols_dist[i % 4]:
            dist_ccms[i+1] = st.number_input(f"Distância CCM {i+1} (m)", value=20.0, key=f"dist_{i}")

    # --- 7. CÁLCULOS ---
    if st.button("🏁 EXECUTAR CÁLCULOS"):
        if st.session_state.df_motores.empty:
            st.warning("Adicione motores para calcular.")
        else:
            # Cálculo Icc QGBT
            z_base = (v_sec**2) / (p_trafo * 1000)
            z_t = (z_pct/100) * z_base
            z_r = 0 if scc_rede == 0 else (v_sec**2) / (scc_rede * 1e6)
            icc_trafo = (v_sec / (np.sqrt(3) * (z_r + z_t)))

            motores_cc = st.session_state.df_motores[st.session_state.df_motores['Partida'].isin(["Direta", "Estrela-Triângulo"])]
            total_cv_cc = (motores_cc['Potência (CV)'] * motores_cc['Quantidade']).sum()
            icc_motores = (total_cv_cc * 1.55) * 4
            icc_qgbt = icc_trafo + icc_motores

            st.success(f"### Icc Total no QGBT: {icc_qgbt/1000:.2f} kA")

            res_data = []
            for i in range(1, int(n_ccm) + 1):
                mask = st.session_state.df_motores['CCM Destino'] == i
                cv_ccm = (st.session_state.df_motores[mask]['Potência (CV)'] * st.session_state.df_motores[mask]['Quantidade']).sum()
                z_cabo = 0.0003 * dist_ccms[i]
                icc_local = (v_sec / (np.sqrt(3) * ((v_sec/(icc_qgbt*np.sqrt(3))) + z_cabo)))
                
                res_data.append({
                    "Painel": f"CCM {i}",
                    "Carga (CV)": f"{cv_ccm:.1f}",
                    "Icc Estimada (kA)": f"{icc_local/1000:.2f}"
                })
            st.table(pd.DataFrame(res_data))

if __name__ == "__main__":
    main()
