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

    # --- 2. CONFIGURAÇÃO DE INFRAESTRUTURA ---
    n_ccm = st.number_input("Quantidade de CCMs no Projeto", min_value=1, max_value=20, value=1)
    st.divider()

    # --- 3. INICIALIZAÇÃO DO ESTADO ---
    if 'df_motores' not in st.session_state:
        st.session_state.df_motores = pd.DataFrame(columns=['Selecionar', 'Potência (CV)', 'Quantidade', 'Partida', 'CCM Destino', 'Status'])

    # --- 4. FORMULÁRIO DE ENTRADA (NOVO MOTOR) ---
    st.header("📋 Cadastro de Novo Motor")
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            # Opção de 'None' ou 0.0 para garantir que o usuário escolha
            pot_input = st.selectbox("Potência (CV)", options=[0.25, 0.5, 1, 2, 3, 5, 7.5, 10, 15, 20, 25, 30, 40, 50, 75, 100], index=None, placeholder="Selecione...")
        with c2:
            qtd_input = st.number_input("Quantidade", min_value=1, value=1)
        with c3:
            partida_input = st.selectbox("Tipo de Partida", options=["Direta", "Estrela-Triângulo", "Inversor", "Soft-Starter"])
        with c4:
            ccm_input = st.selectbox("CCM Destino", options=list(range(1, int(n_ccm) + 1)))

        if st.button("➕ Adicionar Motor à Lista", type="primary", use_container_width=True):
            if pot_input is not None:
                # Reseta o status das linhas antigas e marca a nova
                if not st.session_state.df_motores.empty:
                    st.session_state.df_motores['Status'] = 'Antigo'
                
                nova_linha = pd.DataFrame([{
                    'Selecionar': False, 
                    'Potência (CV)': pot_input, 
                    'Quantidade': qtd_input, 
                    'Partida': partida_input, 
                    'CCM Destino': ccm_input,
                    'Status': 'Recém Adicionado'
                }])
                st.session_state.df_motores = pd.concat([st.session_state.df_motores, nova_linha], ignore_index=True)
                st.rerun()
            else:
                st.warning("Por favor, selecione a Potência do motor.")

    # --- 5. TABELA DE GESTÃO ---
    st.header("🏭 Lista de Motores Adicionados")
    
    if not st.session_state.df_motores.empty:
        col_excluir, col_limpar = st.columns([1, 1])
        with col_excluir:
            if st.button("🗑️ Excluir Selecionados"):
                st.session_state.df_motores = st.session_state.df_motores[st.session_state.df_motores['Selecionar'] == False]
                st.rerun()
        with col_limpar:
            if st.button("💣 Limpar Lista Completa"):
                st.session_state.df_motores = pd.DataFrame(columns=['Selecionar', 'Potência (CV)', 'Quantidade', 'Partida', 'CCM Destino', 'Status'])
                st.rerun()

        # Função de cor para identificar o que acabou de ser adicionado
        def highlight_new(row):
            color = '#d1e7dd' if row['Status'] == 'Recém Adicionado' else '' # Verde claro para novos
            return [f'background-color: {color}'] * len(row)

        df_styled = st.session_state.df_motores.style.apply(highlight_new, axis=1)

        edited_df = st.data_editor(
            df_styled,
            column_config={
                "Selecionar": st.column_config.CheckboxColumn("Excluir?", default=False),
                "Status": None, # Oculta a coluna de controle
                "CCM Destino": st.column_config.NumberColumn(disabled=True),
                "Potência (CV)": st.column_config.NumberColumn(disabled=True),
                "Quantidade": st.column_config.NumberColumn(disabled=True),
                "Partida": st.column_config.TextColumn(disabled=True),
            },
            use_container_width=True,
            key="tabela_motores"
        )
        # Sincroniza apenas o checkbox de exclusão
        st.session_state.df_motores['Selecionar'] = edited_df['Selecionar']

    # --- 6. CÁLCULOS E RESULTADOS (IGUAL AO ANTERIOR) ---
    st.divider()
    if st.button("🏁 EXECUTAR CÁLCULOS FINAIS", use_container_width=True):
        if st.session_state.df_motores.empty:
            st.error("A lista está vazia!")
        else:
            # (Lógica de cálculo mantida)
            z_base = (v_sec**2) / (p_trafo * 1000)
            z_t = (z_pct/100) * z_base
            z_r = 0 if scc_rede == 0 else (v_sec**2) / (scc_rede * 1e6)
            icc_trafo = (v_sec / (np.sqrt(3) * (z_r + z_t)))
            motores_cc = st.session_state.df_motores[st.session_state.df_motores['Partida'].isin(["Direta", "Estrela-Triângulo"])]
            total_cv_cc = (motores_cc['Potência (CV)'] * motores_cc['Quantidade']).sum()
            icc_motores = (total_cv_cc * 1.55) * 4
            icc_qgbt = icc_trafo + icc_motores

            st.success(f"### Corrente de Curto-Circuito no QGBT: {icc_qgbt/1000:.2f} kA")
            # ... (Restante da tabela de resultados por CCM)
