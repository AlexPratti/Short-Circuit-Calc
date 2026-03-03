import streamlit as st
import pandas as pd
import numpy as np

def main():
    st.set_page_config(page_title="Short-Circuit-Calc Pro", layout="wide")
    st.title("⚡ Gestão, Dimensionamento e Seletividade Industrial")

    # --- TABELA DE CABOS COMERCIAIS ---
    CABOS_COMERCIAIS = [2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300]
    AMPACIDADE = [24, 32, 41, 57, 76, 101, 125, 151, 192, 232, 269, 309, 353, 415, 473]

    def sugerir_cabo(corrente, secao_queda):
        secao_final = max(secao_queda, 2.5)
        for i, cap in enumerate(AMPACIDADE):
            if cap >= corrente and CABOS_COMERCIAIS[i] >= secao_final:
                return CABOS_COMERCIAIS[i], cap
        return 300, 473

    # --- 1. PARÂMETROS DA SUBESTAÇÃO (SIDEBAR) ---
    with st.sidebar:
        st.header("🔌 Parâmetros da SE")
        scc_rede = st.number_input("Scc Concessionária (MVA)", value=20.0)
        p_trafo = st.number_input("Potência Trafo (kVA)", value=225.0)
        v_sec = st.number_input("Tensão (V)", value=380.0)
        z_pct = st.number_input("Impedância Z% (Trafo)", value=5.0)
        dist_se_qgbt = st.number_input("Distância SE ao QGBT (m)", value=15.0)
        st.divider()
        st.header("🛡️ Critérios de Seletividade")
        fator_coord = st.slider("Margem de Seletividade (In_qgbt / In_ccm)", 1.2, 2.5, 1.5)

    # --- 2. CONFIGURAÇÃO DE CCMs ---
    n_ccm = st.number_input("Quantidade de CCMs", min_value=1, max_value=10, value=2)
    dist_ccms = {}
    cols_dist = st.columns(4)
    for i in range(int(n_ccm)):
        with cols_dist[i % 4]:
            dist_ccms[i+1] = st.number_input(f"Dist. QGBT -> CCM {i+1} (m)", value=20.0, key=f"d_{i}")

    # --- 3. GESTÃO DE MOTORES ---
    # Definição estrita das colunas para evitar duplicidade
    colunas_lista = ['Selecionar', 'Equipamento', 'Motor (CV)', 'Quantidade', 'Partida', 'CCM Destino', 'Status']
    
    if 'df_motores' not in st.session_state:
        st.session_state.df_motores = pd.DataFrame(columns=colunas_lista)

    st.header("📋 Cadastro de Motores")
    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1.5, 1])
        with c1:
            nome_eq = st.text_input("Equipamento", placeholder="Ex: Moedor")
        with c2:
            pot = st.selectbox("Motor (CV)", options=[0.5, 1, 2, 3, 5, 7.5, 10, 15, 20, 30, 50, 100], index=None)
        with c3:
            qtd = st.number_input("Qtd Motores", min_value=1, value=1)
        with c4:
            part = st.selectbox("Partida", options=["Direta", "Estrela-Triângulo", "Inversor", "Soft-Starter"])
        with c5:
            dest = st.selectbox("CCM Destino", options=list(range(1, int(n_ccm) + 1)))

        if st.button("➕ Adicionar à Lista", type="primary", use_container_width=True):
            if pot and nome_eq:
                st.session_state.df_motores['Status'] = 'Antigo'
                nova = pd.DataFrame([{
                    'Selecionar': False, 
                    'Equipamento': nome_eq,
                    'Motor (CV)': float(pot), 
                    'Quantidade': int(qtd), 
                    'Partida': part, 
                    'CCM Destino': int(dest), 
                    'Status': 'Novo'
                }])
                st.session_state.df_motores = pd.concat([st.session_state.df_motores, nova], ignore_index=True)
                st.rerun()

    # --- LISTA DE CARGAS (TABELA) ---
    if not st.session_state.df_motores.empty:
        st.header("🏭 Lista de Cargas")
        
        col_btn, _ = st.columns([1, 4])
        with col_btn:
            if st.button("🗑️ Excluir Linhas Selecionadas"):
                st.session_state.df_motores = st.session_state.df_motores[st.session_state.df_motores['Selecionar'] == False]
                st.rerun()

        # Garante que o DataFrame exibido use apenas as colunas corretas e na ordem certa
        df_exibir = st.session_state.df_motores[colunas_lista]

        edited_df = st.data_editor(
            df_exibir.style.apply(lambda r: ['background-color: #0047AB; color: white' if r['Status']=='Novo' else '' for _ in r], axis=1),
            column_config={
                "Selecionar": st.column_config.CheckboxColumn("Excluir?"),
                "Equipamento": st.column_config.TextColumn("Equipamento"),
                "Motor (CV)": st.column_config.NumberColumn("Motor (CV)", format="%.1f"),
                "Status": None # Esconde a coluna de controle
            },
            use_container_width=True, 
            key="edit_v10"
        )
        st.session_state.df_motores = edited_df

        # --- 4. EXECUTAR CÁLCULOS ---
        st.divider()
        if st.button("🚀 EXECUTAR DIMENSIONAMENTO COMPLETO", type="secondary", use_container_width=True):
            total_cv = (st.session_state.df_motores['Motor (CV)'] * st.session_state.df_motores['Quantidade']).sum()
            in_total = (total_cv * 736) / (v_sec * 1.732 * 0.85 * 0.9)
            
            try:
                icc_qgbt = (v_sec / (1.732 * ((z_pct/100)*((v_sec**2)/(p_trafo*1000)))))
            except:
                icc_qgbt = 0
            
            disj_qgbt = in_total * 1.25 
            
            st.success(f"### QGBT GERAL: In = {in_total:.1f} A | Icc = {icc_qgbt/1000:.2f} kA | Disjuntor Geral: {disj_qgbt:.0f} A")

            res_ccm = []
            for i in range(1, int(n_ccm) + 1):
                m_ccm = st.session_state.df_motores[st.session_state.df_motores['CCM Destino'] == i]
                cv_ccm = (m_ccm['Motor (CV)'] * m_ccm['Quantidade']).sum()
                if cv_ccm == 0: continue
                
                in_ccm = (cv_ccm * 736) / (v_sec * 1.732 * 0.85 * 0.9)
                disj_ccm = in_ccm * 1.25
                s_queda = (1.732 * dist_ccms[i] * in_ccm * 0.85) / (56 * (v_sec * 0.03))
                cabo, _ = sugerir_cabo(in_ccm, s_queda)
                coord_ok = "✅ OK" if (disj_qgbt / (disj_ccm if disj_ccm > 0 else 1)) >= fator_coord else "⚠️ Reajustar"

                res_ccm.append({
                    "Painel": f"CCM {i}",
                    "Carga Total (CV)": f"{cv_ccm:.1f}",
                    "Disjuntor CCM": f"{disj_ccm:.0f} A",
                    "Cabo Sugerido": f"{cabo} mm²",
                    "Coordenação": coord_ok,
                    "Icc Local (kA)": f"{(icc_qgbt * 0.85)/1000:.2f}"
                })
            
            st.subheader("📊 Resultados de Dimensionamento")
            st.table(pd.DataFrame(res_ccm))

if __name__ == "__main__":
    main()
