import streamlit as st
import datetime
import requests

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="App de Serviços Prediais", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- CREDENCIAIS ABSOLUTAS FIXAS (Isoladas do ecossistema do driver) ---
URL_PROJETO_REAL = "https://supabase.co"
CHAVE_PROJETO_REAL = "sb_publishable_zLiararaOIVVcwQm6oR2IQ_Sb0YOnbIqf6XwH7GqBvI3l8fL4Y2Xk8Wq"

# --- CONTROLE DE SESSÃO (STATE) ---
if "user_logged" not in st.session_state:
    st.session_state["user_logged"] = False
if "user_type" not in st.session_state:
    st.session_state["user_type"] = None
if "cliente_dados" not in st.session_state:
    st.session_state["cliente_dados"] = None
if "categoria_ativa" not in st.session_state:
    st.session_state["categoria_ativa"] = None


# --- FUNÇÕES DE BANCO POR HTTP BRUTO (Garante rota absoluta contra desvios) ---
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
            "Content-Type": "application/json"
        }
        # Inserção pura via POST sem cabeçalhos de retorno complexos que confundem o gateway
        resposta = requests.post(url_api, headers=headers, json=dados)
        if 200 <= resposta.status_code < 300:
            return {"sucesso": True, "detalhes": ""}
        else:
            return {"sucesso": False, "detalhes": f"Status {resposta.status_code}"}
    except Exception as e:
        return {"sucesso": False, "detalhes": str(e)}

def buscar_categorias():
    dados = executar_select_direto("app_servicos_detalhes", "?select=categoria")
    if dados and not isinstance(dados, dict):
        categorias = list(set([item['categoria'] for item in dados if 'categoria' in item]))
        if categorias:
            return categorias
    return ["Elétrica", "Hidráulica", "Pintura"]

def buscar_servicos_por_categoria(cat):
    dados = executar_select_direto("app_servicos_detalhes", f"?select=categoria,nome_detalhado,preco&categoria=eq.{cat}")
    if dados and not isinstance(dados, dict):
        return dados
    
    dados_locais = {
        "Elétrica": [{"nome_detalhado": "Instalação de chuveiro elétrico 220 V", "preco": 150.00}],
        "Hidráulica": [{"nome_detalhado": "Conserto de vazamento em torneira", "preco": 80.00}],
        "Pintura": [{"nome_detalhado": "Pintura de parede (m²)", "preco": 45.00}]
    }
    return dados_locais.get(cat, [])

def registrar_ligacao(cliente, profissional, atendeu):
    dados = {
        "cliente_nome": cliente,
        "profissional_nome": profissional,
        "horario": datetime.datetime.now().isoformat(),
        "atendido": atendeu
    }
    executar_insert_direto("app_servicos_logs_ligacoes", dados)

# --- MENU LATERAL (NAVEGAÇÃO) ---
st.sidebar.title("🛠️ Central de Serviços")

if not st.session_state["user_logged"]:
    menu = st.sidebar.radio("Navegação", ["Área do Cliente", "Área Administrativa"])
else:
    if st.session_state["user_type"] == "admin":
        st.sidebar.success("Conectado como: PRATTI")
        menu = st.sidebar.radio("Painel Admin", ["Gerenciar Serviços/Preços", "Cadastrar Profissional", "Ver Logs de Ligações"])
    else:
        dados_cli = st.session_state['cliente_dados']
        # Desempacota com segurança a estrutura se ela vier envelopada em array
        cliente_info_topo = dados_cli[0] if isinstance(dados_cli, list) and len(dados_cli) > 0 else (dados_cli if dados_cli else {})
        st.sidebar.success(f"Cliente: {cliente_info_topo.get('nome_completo', 'Usuário')}")
        menu = st.sidebar.radio("Painel Cliente", ["Buscar Serviços", "Meus Dados"])
    
    if st.sidebar.button("Sair / Logout"):
        st.session_state["user_logged"] = False
        st.session_state["user_type"] = None
        st.session_state["cliente_dados"] = None
        st.session_state["categoria_ativa"] = None
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("📢 Suporte & Reclamações")
st.sidebar.write("Fale com o Administrador:")
st.sidebar.info("📧 contato@pratti.com\n\n📞 (11) 99999-9999")


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
            try:
                supabase.table("app_servicos_detalhes").insert({
                    "categoria": nova_cat.strip().capitalize(),
                    "nome_detalhado": novo_serv.strip(),
                    "preco": novo_preco
                }).execute()
                st.success(f"Botão/Serviço '{nova_cat}' adicionado com sucesso!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar serviço: {e}")
            
    st.subheader("Tabela de Preços Cadastrados")
    try:
        res = supabase.table("app_servicos_detalhes").select("*").execute()
        if res.data:
            st.dataframe(res.data, use_container_width=True)
        else:
            st.info("Nenhum preço cadastrado no banco de dados ainda.")
    except Exception as e:
        st.error(f"Erro ao ler tabela de preços: {e}")

elif menu == "Cadastrar Profissional":
    st.title("👨‍🔧 Cadastrar Novo Profissional")
    nome = st.text_input("Nome Completo do Profissional")
    categorias_disponiveis = buscar_categorias()
    serv_principal = st.selectbox("Área de Atuação Principal", categorias_disponiveis)
    localidade = st.text_input("Cidade / Região de Atendimento")
    telefone = st.text_input("Telefone de Contato (WhatsApp)")
    
    if st.button("Cadastrar Profissional"):
        if nome and localidade and telefone:
            try:
                supabase.table("app_servicos_profissionais").insert({
                    "nome": nome,
                    "servico_principal": serv_principal,
                    "localidade": localidade,
                    "telefone": telefone
                }).execute()
                st.success("Profissional cadastrado com sucesso!")
            except Exception as e:
                st.error(f"Erro ao cadastrar profissional: {e}")

elif menu == "Ver Logs de Ligações":
    st.title("📊 Histórico de Ligações Registradas")
    try:
        res = supabase.table("app_servicos_logs_ligacoes").select("*").order("horario", desc=True).execute()
        if res.data:
            st.dataframe(res.data, use_container_width=True)
        else:
            st.info("Nenhum registro de log de ligação disponível.")
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")

# --- TELAS DO SISTEMA: 2. ÁREA DO CLIENTE (LOGIN/CADASTRO) ---
elif menu == "Área do Cliente" and not st.session_state["user_logged"]:
    st.title("📱 Acesso do Cliente")
    aba_login, aba_cadastro = st.tabs(["Já tenho cadastro", "Criar Nova Conta"])
    
    with aba_login:
        tel_login = st.text_input("Digite seu Telefone WhatsApp Cadastrado", key="login_tel")
        if st.button("Entrar"):
            try:
                res = supabase.table("app_servicos_clientes").select("*").eq("whatsapp", tel_login).execute()
                if res.data and len(res.data) > 0:
                    st.session_state["user_logged"] = True
                    st.session_state["user_type"] = "cliente"
                    st.session_state["cliente_dados"] = res.data
                    st.success("Login efetuado com sucesso!")
                    st.rerun()
                else:
                    st.error("Telefone não cadastrado.")
            except Exception as e:
                st.error(f"Erro ao buscar usuário: {e}")
                
    with aba_cadastro:
        nome_c = st.text_input("Nome Completo")
        endereco_c = st.text_input("Endereço Residencial")
        whats_c = st.text_input("WhatsApp (com DDD)")
        
        if st.button("Concluir Cadastro"):
            if nome_c and endereco_c and whats_c:
                try:
                    res_check = supabase.table("app_servicos_clientes").select("*").eq("whatsapp", whats_c).execute()
                    if res_check.data and len(res_check.data) > 0:
                        st.warning("Este telefone já está cadastrado.")
                    else:
                        novo_cli = {"nome_completo": nome_c, "endereco": endereco_c, "whatsapp": whats_c}
                        supabase.table("app_servicos_clientes").insert(novo_cli).execute()
                        st.success("Cadastro efetuado com sucesso! Faça o login na aba ao lado.")
                except Exception as e:
                    st.error(f"Rejeição no banco de dados durante a inserção: {e}")

# --- TELAS DO SISTEMA: 3. PAINEL DO CLIENTE LOGADO ---
elif menu == "Buscar Serviços":
    dados_cli_busca = st.session_state['cliente_dados']
    cliente_info_busca = dados_cli_busca[0] if isinstance(dados_cli_busca, list) and len(dados_cli_busca) > 0 else (dados_cli_busca if dados_cli_busca else {})
    
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

        st.markdown("#### 🧔 Profissionais Disponíveis na sua Área:")
        try:
            res_prof = supabase.table("app_servicos_profissionais").select("*").eq("servico_principal", cat_ativa).execute()
            lista_prof = res_prof.data if res_prof.data else []
        except Exception:
            lista_prof = []
        
        if lista_prof:
            for idx_p, prof_item in enumerate(lista_prof):
                with st.container(border=True):
                    st.write(f"**Nome:** {prof_item['nome']}")
                    st.write(f"📍 **Localidade:** {prof_item['localidade']}")
                    st.write("Para falar com o profissional, use os botões abaixo:")
                    c1, c2 = st.columns(2)
                    
                    if c1.button(f"📞 Ligar para {prof_item['nome']}", key=f"ligar_{idx_p}"):
                        registrar_ligacao(cliente_info_busca.get('nome_completo', 'Cliente'), prof_item["nome"], True)
                        st.success(f"Ligação registrada! Contato: {prof_item['telefone']}")
                        
                    if c2.button(f"❌ Chamei mas não atendeu", key=f"nao_atendeu_{idx_p}"):
                        registrar_ligacao(cliente_info_busca.get('nome_completo', 'Cliente'), prof_item["nome"], False)
                        st.warning(f"Tentativa de contato sem sucesso registrada.")
        else:
            st.info("Nenhum profissional cadastrado para esta categoria ainda.")

elif menu == "Meus Dados":
    dados_cli_perfil = st.session_state['cliente_dados']
    cliente_info_perfil = dados_cli_perfil[0] if isinstance(dados_cli_perfil, list) and len(dados_cli_perfil) > 0 else (dados_cli_perfil if dados_cli_perfil else {})
    
    st.title("👤 Meus Dados de Cadastro")
    st.write(f"**Nome:** {cliente_info_perfil.get('nome_completo', '')}")
    st.write(f"**Endereço de Atendimento:** {cliente_info_perfil.get('endereco', '')}")
    st.write(f"**WhatsApp:** {cliente_info_perfil.get('whatsapp', '')}")
