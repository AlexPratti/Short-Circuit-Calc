import streamlit as st
import datetime
import requests
import urllib.parse

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="App de Serviços Prediais",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CREDENCIAIS ABSOLUTAS FIXAS (Tratamento automático de sufixo) ---
URL_BRUTA = st.secrets["URL_SUPABASE"].strip().rstrip('/')
if "/rest/v1" in URL_BRUTA:
    URL_PROJETO_REAL = URL_BRUTA.split("/rest/v1")[0]
else:
    URL_PROJETO_REAL = URL_BRUTA
CHAVE_PROJETO_REAL = st.secrets["KEY_SUPABASE"].strip()

# --- CONTROLE DE SESSÃO (STATE) ---
if "user_logged" not in st.session_state:
    st.session_state["user_logged"] = False
if "user_type" not in st.session_state:
    st.session_state["user_type"] = None
if "cliente_dados" not in st.session_state:
    st.session_state["cliente_dados"] = None
if "categoria_ativa" not in st.session_state:
    st.session_state["categoria_ativa"] = None

# --- FUNÇÕES DE BANCO POR HTTP BRUTO ---
def executar_select_direto(tabela, parametros=""):
    try:
        url_api = f"{URL_PROJETO_REAL}/rest/v1/{tabela}{parametros}"
        headers = {
            "apikey": CHAVE_PROJETO_REAL,
            "Authorization": f"Bearer {CHAVE_PROJETO_REAL}",
            "Content-Type": "application/json"
        }
        resposta = requests.get(url_api, headers=headers)
        if resposta.status_code == 200:
            return resposta.json()
    except Exception:
        pass
    return None

def executar_insert_direto(tabela, dados):
    try:
        url_api = f"{URL_PROJETO_REAL}/rest/v1/{tabela}"
        headers = {
            "apikey": CHAVE_PROJETO_REAL,
            "Authorization": f"Bearer {CHAVE_PROJETO_REAL}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        resposta = requests.post(url_api, headers=headers, json=dados)
        if 200 <= resposta.status_code < 300:
            return {"sucesso": True, "detalhes": ""}
        else:
            return {"sucesso": False, "detalhes": f"Status {resposta.status_code} - {resposta.text}"}
    except Exception as e:
        return {"sucesso": False, "detalhes": str(e)}

def executar_update_direto(tabela, parametros, dados):
    try:
        url_api = f"{URL_PROJETO_REAL}/rest/v1/{tabela}{parametros}"
        headers = {
            "apikey": CHAVE_PROJETO_REAL,
            "Authorization": f"Bearer {CHAVE_PROJETO_REAL}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        resposta = requests.patch(url_api, headers=headers, json=dados)
        if 200 <= resposta.status_code < 300:
            return {"sucesso": True, "detalhes": ""}
        else:
            return {"sucesso": False, "detalhes": f"Status {resposta.status_code} - {resposta.text}"}
    except Exception as e:
        return {"sucesso": False, "detalhes": str(e)}

def buscar_categorias():
    dados = executar_select_direto("app_servicos_detalhes", "?select=categoria&ativo=eq.true")
    if dados and not isinstance(dados, dict):
        categorias = list(set([item['categoria'] for item in dados if 'categoria' in item]))
        if categorias:
            return sorted(categorias)
    return []

def buscar_servicos_por_categoria(cat):
    dados = executar_select_direto("app_servicos_detalhes", f"?select=categoria,nome_detalhado,preco&categoria=eq.{cat}&ativo=eq.true")
    if dados and not isinstance(dados, dict):
        return dados
    dados_locais = {
        "Elétrica": [{"nome_detalhado": "Instalação de chuveiro elétrico 220 V", "preco": 150.00}],
        "Hidráulica": [{"nome_detalhado": "Conserto de vazamento em torneira", "preco": 80.00}],
        "Pintura": [{"nome_detalhado": "Pintura de parede (m²)", "preco": 45.00}]
    }
    return dados_locais.get(cat, [])

def buscar_avaliacoes_profissional(nome_prof):
    dados =幻想excutar_select_direto("app_servicos_logs_ligacoes", f"?select=cliente_nome,horario,motivo_feedback,nota_estrelas&profissional_nome=eq.{nome_prof}&order=horario.desc")
    if dados and not isinstance(dados, dict):
        return dados
    return []

# --- MENU LATERAL (NAVEGAÇÃO) ---
st.sidebar.title("🛠️ Central de Serviços")
if not st.session_state["user_logged"]:
    menu = st.sidebar.radio("Navegação", ["Área do Cliente", "Área Administrativa"])
else:
    if st.session_state["user_type"] == "admin":
        st.sidebar.success("Conectado como: PRATTI")
        menu = st.sidebar.radio("Painel Admin", ["Gerenciar Serviços/Preços", "Cadastrar Profissional", "Gerenciar Clientes", "Ver Logs de Ligações"])
    else:
        dados_cli = st.session_state['cliente_dados']
        cliente_info_topo = dados_cli if isinstance(dados_cli, dict) else (dados_cli if isinstance(dados_cli, list) else {})
        st.sidebar.success(f"Cliente: {cliente_info_topo.get('nome_completo', 'Usuário')}")
        menu = st.sidebar.radio("Painel Cliente", ["Buscar Serviços", "Ver Avaliações", "Meus Dados"])

if st.sidebar.button("Sair / Logout"):
    st.session_state["user_logged"] = False
    st.session_state["user_type"] = None
    st.session_state["cliente_dados"] = None
    st.session_state["categoria_ativa"] = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("📢 Suporte & Reclamações")
st.sidebar.write("Fale com o Administrador:")

# Configurações de segurança puxando dos Secrets
tel_admin_seguro = st.secrets["TELEFONE_ADMIN"].strip()
email_admin_seguro = st.secrets["EMAIL_ADMIN"].strip()

# --- AJUSTE DE FORMATAÇÃO DO TELEFONE COM DDD DE 3 DÍGITOS ---
if len(tel_admin_seguro) == 12:  # Caso o número comece com zero (ex: 027999060525)
    tel_formatado = f"({tel_admin_seguro[:3]}) {tel_admin_seguro[3:8]}-{tel_admin_seguro[8:]}"
elif len(tel_admin_seguro) == 11:  # Padrão tradicional com 2 dígitos no DDD
    tel_formatado = f"({tel_admin_seguro[:2]}) {tel_admin_seguro[2:7]}-{tel_admin_seguro[7:]}"
else:
    tel_formatado = tel_admin_seguro

mensagem_admin = "Olá, preciso de suporte no aplicativo de Serviços Prediais."
msg_admin_codificada = urllib.parse.quote(mensagem_admin)
link_whats_admin = f"whatsapp://send?phone={tel_admin_seguro}&text={msg_admin_codificada}"

# Botão corrigido para Celular (Sem target=_blank)
link_html_admin = f'<a href="{link_whats_admin}" style="text-decoration: none;"><button style="width: 100%; background-color: #25D366; color: white; border: none; padding: 0.5rem; border-radius: 4px; cursor: pointer; font-weight: bold; text-align: center; margin-bottom: 10px;">💬 Suporte via WhatsApp</button></a>'
st.sidebar.markdown(link_html_admin, unsafe_allow_html=True)

st.sidebar.info(f"📧 {email_admin_seguro}\n\n📞 {tel_formatado}")




# --- TELAS DO SISTEMA: 1. ÁREA ADMINISTRATIVA ---
if menu == "Área Administrativa" and not st.session_state["user_logged"]:
    st.title("🔒 Login Administrativo")
    login_user = st.text_input("Usuário")
    login_pass = st.text_input("Senha", type="password")
    
    if st.button("Acessar"):
        if login_user.strip() == st.secrets["ADMIN_USER"].strip() and login_pass == st.secrets["ADMIN_PASS"].strip():
            st.session_state["user_logged"] = True
            st.session_state["user_type"] = "admin"
            st.success("Login administrativo realizado com sucesso!")
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")

elif menu == "Gerenciar Serviços/Preços":
    st.title("⚙️ Gerenciar Categorias e Preços")
    st.subheader("Adicionar Novo Tipo de Serviço / Botão")
    nova_cat = st.text_input("Categoria Principal (Ex: Elétrica, Hidráulica, Mecânica)")
    novo_serv = st.text_input("Serviço Detalhado (Ex: Instalação de chuveiro elétrico 220 V)")
    novo_preco = st.number_input("Preço Sugerido (R$)", min_value=0.0, step=10.0)
    
    if st.button("Salvar Serviço"):
        if nova_cat and novo_serv:
            retorno = executar_insert_direto("app_servicos_detalhes", {
                "categoria": nova_cat.strip().capitalize(),
                "nome_detalhado": novo_serv.strip(),
                "preco": novo_preco,
                "ativo": True
            })
            if retorno["sucesso"]:
                st.success(f"Botão/Serviço '{nova_cat}' adicionado com sucesso!")
                st.rerun()
            else:
                st.error("Erro interno ao tentar salvar dados no banco.")

    st.subheader("Tabela de Preços Cadastrados")
    # Busca apenas os serviços ativos para exibição e gerenciamento
    dados_tabela = executar_select_direto("app_servicos_detalhes", "?select=id,categoria,nome_detalhado,preco&ativo=eq.true")
    if dados_tabela and not isinstance(dados_tabela, dict):
        st.dataframe(dados_tabela, use_container_width=True)
        
        st.markdown("---")
        st.subheader("❌ Desativar Serviço (Exclusão Lógica)")
        lista_opcoes_servicos = [f"{item['id']} - {item['categoria']}: {item['nome_detalhado']}" for item in dados_tabela]
        servico_para_excluir = st.selectbox("Selecione o serviço para desativar do app:", lista_opcoes_servicos)
        if st.button("Desativar Serviço Selecionado"):
            id_servico = servico_para_excluir.split(" - ")[0]
            # Exclusão Lógica alterando ativo para false
            ret_del = executar_update_direto("app_servicos_detalhes", f"?id=eq.{id_servico}", {"ativo": False})
            if ret_del["sucesso"]:
                st.success("Serviço desativado com sucesso!")
                st.rerun()
            else:
                st.error("Erro ao desativar do banco de dados.")
    else:
        st.info("Nenhum preço listado ou banco de dados aguardando novos registros ativos.")

elif menu == "Cadastrar Profissional":
    st.title("👨‍🔧 Cadastrar Novo Profissional")
    nome = st.text_input("Nome Completo do Profissional")
    categorias_disponiveis = buscar_categorias()
    serv_principal = st.selectbox("Área de Atuação Principal", categorias_disponiveis)
    localidade = st.text_input("Cidade / Região de Atendimento")
    telefone = st.text_input("Telefone de Contato (WhatsApp)")
    
    if st.button("Cadastrar Profissional"):
        if nome and localidade and telefone:
            # --- MELHORIA: BLOQUEIO DE CADASTROS DUPLICADOS POR WHATSAPP ---
            res_check = executar_select_direto("app_servicos_profissionais", f"?select=telefone&telefone=eq.{telefone.strip()}&ativo=eq.true")
            if res_check and isinstance(res_check, list) and len(res_check) > 0:
                st.warning("Este número de WhatsApp já pertence a um profissional ativo cadastrado.")
            else:
                retorno = executar_insert_direto("app_servicos_profissionais", {
                    "nome": nome.strip(),
                    "servico_principal": serv_principal,
                    "localidade": localidade.strip(),
                    "telefone": telefone.strip(),
                    "ativo": True
                })
                if retorno["sucesso"]:
                    st.success("Profissional cadastrado com sucesso!")
                    st.rerun()
                else:
                    st.error("Falha ao salvar profissional no banco de dados.")

    st.markdown("---")
    st.subheader("❌ Desativar Profissional (Exclusão Lógica)")
    dados_prof = executar_select_direto("app_servicos_profissionais", "?select=id,nome,servico_principal&ativo=eq.true")
    if dados_prof and not isinstance(dados_prof, dict):
        lista_opcoes_prof = [f"{p['id']} - {p['nome']} ({p['servico_principal']})" for p in dados_prof]
        prof_para_excluir = st.selectbox("Selecione o profissional para remover do app:", lista_opcoes_prof)
        if st.button("Desativar Profissional Selecionado"):
            id_prof = prof_para_excluir.split(" - ")[0]
            # Exclusão Lógica
            ret_del = executar_update_direto("app_servicos_profissionais", f"?id=eq.{id_prof}", {"ativo": False})
            if ret_del["sucesso"]:
                st.success("Profissional desativado com sucesso!")
                st.rerun()
            else:
                st.error("Erro ao desativar profissional.")

elif menu == "Gerenciar Clientes":
    st.title("👥 Gerenciar Clientes Cadastrados")
    dados_clientes = executar_select_direto("app_servicos_clientes", "?select=id,nome_completo,whatsapp&ativo=eq.true")
    if dados_clientes and not isinstance(dados_clientes, dict):
        st.dataframe(dados_clientes, use_container_width=True)
        st.markdown("---")
        st.subheader("❌ Desativar Cliente (Exclusão Lógica)")
        lista_opcoes_cli = [f"{c['id']} - {c['nome_completo']} ({c['whatsapp']})" for c in dados_clientes]
        cli_para_excluir = st.selectbox("Selecione o cliente para suspender acesso:", lista_opcoes_cli)
        if st.button("Desativar Cliente Selecionado"):
            id_cli = cli_para_excluir.split(" - ")[0]
            # Exclusão Lógica
            ret_del = executar_update_direto("app_servicos_clientes", f"?id=eq.{id_cli}", {"ativo": False})
            if ret_del["sucesso"]:
                st.success("Acesso do cliente desativado com sucesso!")
                st.rerun()
            else:
                st.error("Erro ao desativar cliente.")
    else:
        st.info("Nenhum cliente ativo cadastrado no sistema até o momento.")

elif menu == "Ver Logs de Ligações":
    st.title("📊 Histórico de Ligações e Avaliações")
    dados_logs = executar_select_direto("app_servicos_logs_ligacoes", "?select=cliente_nome,profissional_nome,horario,nota_estrelas,motivo_feedback&order=horario.desc")
    if dados_logs and not isinstance(dados_logs, dict):
        st.dataframe(dados_logs, use_container_width=True)
    else:
        st.info("Nenhum registro de log ou avaliação disponível.")

# --- TELAS DO SISTEMA: 2. ÁREA DO CLIENTE (LOGIN/CADASTRO) ---
elif menu == "Área do Cliente" and not st.session_state["user_logged"]:
    st.title("📱 Acesso do Cliente")
    aba_login, aba_cadastro = st.tabs(["Já tenho cadastro", "Criar Nova Conta"])
    
    with aba_login:
        tel_login = st.text_input("Digite seu Telefone WhatsApp Cadastrado", key="login_tel")
        if st.button("Entrar"):
            # Verifica apenas clientes ativos
            dados_cli = executar_select_direto("app_servicos_clientes", f"?select=nome_completo,endereco,whatsapp&whatsapp=eq.{tel_login.strip()}&ativo=eq.true")
            if dados_cli and isinstance(dados_cli, list) and len(dados_cli) > 0:
                st.session_state["user_logged"] = True
                st.session_state["user_type"] = "cliente"
                st.session_state["cliente_dados"] = dados_cli[0]
                st.success("Login efetuado com sucesso!")
                st.rerun()
            else:
                st.error("Telefone não encontrado ou conta inativa nas tabelas do sistema.")

    with aba_cadastro:
        nome_c = st.text_input("Nome Completo")
        endereco_c = st.text_input("Endereço Residencial")
        whats_c = st.text_input("WhatsApp (com DDD)")
        
        if st.button("Concluir Cadastro"):
            if nome_c and endereco_c and whats_c:
                res_check = executar_select_direto("app_servicos_clientes", f"?select=whatsapp&whatsapp=eq.{whats_c.strip()}&ativo=eq.true")
                if res_check and isinstance(res_check, list) and len(res_check) > 0:
                    st.warning("Este telefone já está ativamente cadastrado.")
                else:
                    novo_cli = {"nome_completo": nome_c.strip(), "endereco": endereco_c.strip(), "whatsapp": whats_c.strip(), "ativo": True}
                    retorno = executar_insert_direto("app_servicos_clientes", novo_cli)
                    if retorno["sucesso"]:
                        st.success("Cadastro efetuado com sucesso! Faça o login na aba ao lado.")
                    else:
                        st.error(f"Erro ao salvar cadastro: {retorno['detalhes']}")

# --- TELAS DO SISTEMA: 3. PAINEL DO CLIENTE LOGADO ---
elif menu == "Buscar Serviços":
    cliente_info_busca = st.session_state['cliente_dados'] if st.session_state['cliente_dados'] else {}
    st.title(f"Olá, {cliente_info_busca.get('nome_completo', 'Cliente')}! Do que precisa hoje?")
    categorias = buscar_categorias()
    st.subheader("Selecione a categoria do serviço:")
    
    colunas = st.columns(len(categorias) if len(categorias) > 0 else 1)
    for idx, cat in enumerate(categorias):
        if colunas[idx].button(f"🔹 {cat}", use_container_width=True):
            st.session_state["categoria_ativa"] = cat

    if st.session_state["categoria_ativa"]:
        cat_ativa = st.session_state["categoria_ativa"]
        st.markdown(f"### 🛠️ Serviços disponíveis para: **{cat_ativa}**")
        servicos_detalhados = buscar_servicos_por_categoria(cat_ativa)
        
        if servicos_detalhados:
            col_esq, col_dir = st.columns(2)
            with col_esq:
                st.markdown("**Tabela de Preços Oficiais:**")
                for s in servicos_detalhados:
                    st.write(f"• **{s['nome_detalhado']}**: R$ {s['preco']:.2f}")
            with col_dir:
                st.markdown("**Solicitar Atendimento:**")
                opcao_servico = st.selectbox("Qual serviço específico deseja?", [s['nome_detalhado'] for s in servicos_detalhados])
        else:
            st.info("Nenhum preço detalhado fixado para esta categoria ainda.")
            opcao_servico = cat_ativa

        st.markdown("---")
        st.markdown("#### 🧔 Profissionais Disponíveis na sua Área:")
        
        lista_prof = executar_select_direto("app_servicos_profissionais", f"?select=nome,localidade,telefone&servico_principal=eq.{cat_ativa}&ativo=eq.true")
        
        if not lista_prof or isinstance(lista_prof, dict):
            lista_prof = [{"nome": "Carlos Silva", "localidade": "Centro", "telefone": "11999999999"}]
            
        # Filtro adicional por localidade/região
        localidades_disponiveis = sorted(list(set([p['localidade'] for p in lista_prof if 'localidade' in p])))
        localidade_selecionada = st.selectbox("📍 Filtrar lista por Localidade/Região de atendimento:", ["Todas as Regiões"] + localidades_disponiveis)
        
        if localidade_selecionada != "Todas as Regiões":
            lista_prof = [p for p in lista_prof if p['localidade'] == localidade_selecionada]
            
        if not lista_prof:
            st.warning("Nenhum profissional desta categoria atende a região selecionada no momento.")
            
        for idx_p, prof_item in enumerate(lista_prof):
            with st.container(border=True):
                # Reputação matemática baseada nas estrelas coletadas
                feedbacks_p = buscar_avaliacoes_profissional(prof_item["nome"])
                notas_validas = [f["nota_estrelas"] for f in feedbacks_p if f.get("nota_estrelas") is not None]
                
                if notas_validas:
                    media_notas = sum(notas_validas) / len(notas_validas)
                    label_reputacao = f"⭐ {media_notas:.1f} ({len(notas_validas)} avaliações)"
                else:
                    label_reputacao = "⭐ Sem avaliações"
                    
                st.write(f"**Nome:** {prof_item['nome']} | **Reputação:** {label_reputacao}")
                st.write(f"📍 **Localidade:** {prof_item['localidade']}")
                st.write(f"📞 **WhatsApp:** {prof_item['telefone']}")
                
                tel_limpo = "".join(filter(str.isdigit, prof_item['telefone']))
                mensagem_texto = f"Olá {prof_item['nome']}, peguei seu contato no App de Serviços Prediais. Gostaria de um orçamento para o serviço de {opcao_servico}."
                msg_codificada = urllib.parse.quote(mensagem_texto)
                
                # Protocolo corrigido para Deep Link do app nos celulares (sem target=_blank)
                link_whatsapp = f"whatsapp://send?phone={tel_limpo}&text={msg_codificada}"
                
                c1, c2 = st.columns(2)
                
                link_html_whats = f'<a href="{link_whatsapp}" style="text-decoration: none;"><button style="width: 100%; background-color: #25D366; color: white; border: none; padding: 0.5rem; border-radius: 4px; cursor: pointer; font-weight: bold; text-align: center; height: 38px;">💬 Chamar no WhatsApp</button></a>'
                c1.markdown(link_html_whats, unsafe_allow_html=True)
                
                with c2.expander("⭐ Avaliar este Contato"):
                    nota_escolhida = st.slider("Dê uma nota para o atendimento:", min_value=1, max_value=5, value=5, key=f"nota_{idx_p}")
                    
                    motivo_selecionado = st.selectbox(
                        "O que aconteceu?",
                        ["Selecione uma opção...", "Conversei e agendei o serviço", "Não retornou o contato", "Não faz este serviço específico", "Preço diferente do aplicativo", "Outro motivo"],
                        key=f"motivo_{idx_p}"
                    )
                    detalhe_adicional = st.text_input("Comentário adicional (opcional)", key=f"coment_{idx_p}")
                    
                    if st.button("Enviar Avaliação", key=f"btn_aval_{idx_p}"):
                        if motivo_selecionado != "Selecione uma opção...":
                            dados_log_atualizado = {
                                "cliente_nome": cliente_info_busca.get('nome_completo', 'Cliente'),
                                "profissional_nome": prof_item["nome"],
                                "horario": datetime.datetime.now().isoformat(),
                                "atendido": True if "agendei" in motivo_selecionado else False,
                                "nota_estrelas": nota_escolhida,
                                "motivo_feedback": f"{motivo_selecionado} - {detalhe_adicional}".strip(" - ")
                            }
                            executar_insert_direto("app_servicos_logs_ligacoes", dados_log_atualizado)
                            st.success("Avaliação registrada com sucesso! A média foi atualizada.")
                            st.rerun()
                        else:
                            st.error("Por favor, selecione uma opção antes de enviar.")

elif menu == "Ver Avaliações":
    st.title("⭐ Avaliações dos Profissionais")
    st.write("Consulte os feedbacks deixados por outros clientes do aplicativo.")
    
    dados_profissionais = executar_select_direto("app_servicos_profissionais", "?select=nome,servico_principal&ativo=eq.true")
    if dados_profissionais and not isinstance(dados_profissionais, dict):
        nomes_prof = list(set([p['nome'] for p in dados_profissionais]))
        prof_escolhido = st.selectbox("Escolha um profissional para visualizar o histórico:", nomes_prof)
        
        if prof_escolhido:
            feedbacks = buscar_avaliacoes_profissional(prof_escolhido)
            if feedbacks:
                notas_f = [f["nota_estrelas"] for f in feedbacks if f.get("nota_estrelas") is not None]
                if notas_f:
                    st.subheader(f"Média Geral deste Profissional: ⭐ {sum(notas_f)/len(notas_f):.1f}")
                
                for f in feedbacks:
                    with st.chat_message("user"):
                        exibicao_estrelas = "⭐" * int(f.get('nota_estrelas', 5))
                        st.write(f"**Cliente:** {f.get('cliente_nome', 'Anônimo')} | **Avaliação:** {exibicao_estrelas}")
                        st.write(f"💬 {f.get('motivo_feedback', 'Sem observações adicionais')}")
                        st.caption(f"Enviado em: {f.get('horario', '')[:10]}")
            else:
                st.info("Este profissional ainda não possui feedbacks registrados.")
    else:
        st.info("Nenhum profissional ativo cadastrado para exibir avaliações.")

elif menu == "Meus Dados":
    cliente_info_perfil = st.session_state['cliente_dados'] if st.session_state['cliente_dados'] else {}
    st.title("👤 Meus Dados de Cadastro")
    st.write(f"**Nome:** {cliente_info_perfil.get('nome_completo', '')}")
    st.write(f"**Endereço de Atendimento:** {cliente_info_perfil.get('endereco', '')}")
    st.write(f"**WhatsApp:** {cliente_info_perfil.get('whatsapp', '')}")
