import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client, Client



    


# --- 1. CONEXÃO COM O BANCO DE DADOS (SUPABASE) ---
URL_SUPABASE = "https://lfgqxphittdatzknwkqw.supabase.co" 
KEY_SUPABASE = "sb_publishable_zLiarara0IVVcwQm6oR2IQ_Sb0YOWTe" 

try:
    supabase: Client = create_client(URL_SUPABASE, KEY_SUPABASE)
except Exception as e:
    st.error(f"Erro ao conectar ao Supabase: {e}")

def main():
    st.set_page_config(page_title="Short-Circuit-Calc Pro", layout="wide")
    st.title("⚡ Gestão, Dimensionamento e Seletividade Industrial")

    # --- TABELA DE CABOS ---
    CABOS_COMERCIAIS = [2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300]
    AMPACIDADE = [24, 32, 41, 57, 76, 101, 125, 151, 192, 232, 269, 309, 353, 415, 473]

    def sugerir_cabo(corrente, secao_queda):
        secao_final = max(secao_queda, 2.5)
        for i, cap in enumerate(AMPACIDADE):
            if cap >= corrente and CABOS_COMERCIAIS[i] >= secao_final:
                return CABOS_COMERCIAIS[i], cap
        return 300, 473

    # --- 2. PARÂMETROS DA SE ---
    with st.sidebar:
        st.header("🔌 Parâmetros da SE")
        p_trafo = st.number_input("Potência Trafo (kVA)", value=225.0)
        v_sec = st.number_input("Tensão (V)", value=380.0)
        z_pct = st.number_input("Impedância Z% (Trafo)", value=5.0)
        dist_se_qgbt = st.number_input("Distância SE ao QGBT (m)", value=15.0)

        # --- HIPERLINK COM OUTROS APPs
        st.title("Outros Cálculos")
        st.link_button("Energia Incidente", "https://calculo-arc-flash-hb8eujmejx23kk2skfn9nr.streamlit.app/", use_container_width=True)
        st.link_button("Banco de Capacitores", "https://c-lculobancocapacitores-tne9epqsrh64gtwaakzyax.streamlit.app/", use_container_width=True)

    # --- 3. CONFIGURAÇÃO DE CCMs ---
    n_ccm = st.number_input("Quantidade de CCMs", min_value=1, value=2)
    dist_ccms = {i+1: st.number_input(f"Dist. CCM {i+1} (m)", value=20.0, key=f"d_{i}") for i in range(int(n_ccm))}

    # --- 4. GESTÃO DE MOTORES ---
    if 'df_motores' not in st.session_state:
        st.session_state.df_motores = pd.DataFrame(columns=['Selecionar', 'Equipamento', 'Motor (CV)', 'Quantidade', 'Partida', 'CCM Destino', 'Status'])

    st.header("📋 Cadastro de Motores")
    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1.5, 1])
        with c1: nome_eq = st.text_input("Equipamento")
        with c2: pot = st.selectbox("Motor (CV)", options=[0.5, 1, 2, 3, 5, 7.5, 10, 15, 20, 30, 50, 100], index=None)
        with c3: qtd = st.number_input("Qtd", min_value=1, value=1)
        with c4: part = st.selectbox("Partida", options=["Direta", "Estrela-Triângulo", "Inversor", "Soft-Starter"])
        with c5: dest = st.selectbox("CCM", options=list(range(1, int(n_ccm) + 1)))

        if st.button("➕ Adicionar à Lista", type="primary", use_container_width=True):
            if pot and nome_eq:
                nova = pd.DataFrame([{'Selecionar': False, 'Equipamento': nome_eq, 'Motor (CV)': float(pot), 'Quantidade': int(qtd), 'Partida': part, 'CCM Destino': int(dest), 'Status': 'Novo'}])
                st.session_state.df_motores = pd.concat([st.session_state.df_motores, nova], ignore_index=True)
                st.rerun()

    # --- LISTA DE CARGAS ---
    if not st.session_state.df_motores.empty:
        st.header("🏭 Lista de Cargas")
        edited_df = st.data_editor(st.session_state.df_motores, use_container_width=True, key="editor_v15")
        st.session_state.df_motores = edited_df

        # --- 5. EXECUTAR CÁLCULOS ---
        st.divider()
        if st.button("🚀 EXECUTAR DIMENSIONAMENTO COMPLETO", type="secondary", use_container_width=True):
            icc_qgbt = v_sec / (1.732 * ((z_pct/100)*((v_sec**2)/(p_trafo*1000))))
            res_ccm = []
            for i in range(1, int(n_ccm) + 1):
                m_ccm = st.session_state.df_motores[st.session_state.df_motores['CCM Destino'] == i]
                cv_ccm = (m_ccm['Motor (CV)'] * m_ccm['Quantidade']).sum()
                if cv_ccm == 0: continue
                in_ccm = (cv_ccm * 736) / (v_sec * 1.732 * 0.85 * 0.9)
                s_queda = (1.732 * dist_ccms[i] * in_ccm * 0.85) / (56 * (v_sec * 0.03))
                cabo, _ = sugerir_cabo(in_ccm, s_queda)
                res_ccm.append({
                    "Painel": f"CCM {i}",
                    "Carga (CV)": f"{cv_ccm:.1f}",
                    "Cabo": f"{cabo} mm²",
                    "Icc Local (kA)": round((icc_qgbt * 0.85)/1000, 4)
                })
            st.session_state.resultados_finais = res_ccm

    # --- ÁREA DE RESULTADOS E EXPORTAÇÃO ---
    if 'resultados_finais' in st.session_state:
        st.subheader("📊 Resultados")
        st.table(pd.DataFrame(st.session_state.resultados_finais))

        st.divider()
        st.subheader("📤 Exportar para Energia Incidente")
        
        # O uso de colunas ajuda a manter o selectbox visível
        c_sel, c_btn = st.columns([3, 2])
        
        opcoes = [r["Painel"] for r in st.session_state.resultados_finais]
        
        with c_sel:
            # Menu de seleção
            escolha = st.selectbox("Selecione o Painel:", options=opcoes, key="menu_export_final")
        
        with c_btn:
            st.write(" ") # Espaçamento lateral
            st.write(" ") 
            if st.button("💾 Salvar no Supabase", use_container_width=True):
                dados = next(item for item in st.session_state.resultados_finais if item["Painel"] == escolha)
                try:
                    supabase.table("calculos_curto").insert({
                        "tag_painel": dados["Painel"],
                        "icc_ka": float(dados["Icc Local (kA)"]),
                        "v_sec": float(v_sec)
                    }).execute()
                    st.success(f"✅ {escolha} salvo no banco!")
                except Exception as e:
                    st.error(f"Erro: {e}")

if __name__ == "__main__":
    main()
