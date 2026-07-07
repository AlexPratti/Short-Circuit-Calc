import streamlit as st
import datetime
from supabase import create_client, Client

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="App de Serviços Prediais", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- CONEXÃO COM O SUPABASE ---
@st.cache_resource
def init_supabase() -> Client:
    # Utilizando exatamente as chaves do seu Secrets
    url = st.secrets["URL_SUPABASE"]
    key = st.secrets["KEY_SUPABASE"]
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception as e:
    st.error("Erro ao conectar ao Supabase. Verifique suas Secrets.")
    st.stop()
# --- CONTROLE DE SESSÃO (STATE) ---
if "user_logged" not in st.session_state:
    st.session_state["user_logged"] = False
if "user_type" not in st.session_state:
    st.session_state["user_type"] = None  # 'admin' ou 'cliente'
if "cliente_dados" not in st.session_state:
    st.session_state["cliente_dados"] = None
# --- LÓGICA DAS FUNÇÕES DO BANCO ---
def buscar_categorias():
    res = supabase.table("app_servicos_detalhes").select("categoria").execute()
    return list(set([item['categoria'] for item in res.data])) if res.data else ["Elétrica", "Hidráulica", "Pintura"]

def buscar_servicos_por_categoria(cat):
    res = supabase.table("app_servicos_detalhes").select("*").eq("categoria", cat).execute()
    return res.data

def registrar_ligacao(cliente, profissional, atendeu):
    dados = {
        "cliente_nome": cliente,
        "profissional_nome": profesional,
        "horario": datetime.datetime.now().isoformat(),
        "atendido": atendeu
    }
    supabase.table("app_servicos_logs_ligacoes").insert(dados).execute()
# --- MENU LATERAL (NAVEGAÇÃO) ---
st.sidebar.title("🛠️ Central de Serviços")

if not st.session_state["user_logged"]:
    menu = st.sidebar.radio("Navegação", ["Área do Cliente", "Área Administrativa"])
else:
    if st.session_state["user_type"] == "admin":
        st.sidebar.success("Conectado como: PRATTI")
        menu = st.sidebar.radio("Painel Admin", ["Gerenciar Serviços/Preços", "Cadastrar Profissional", "Ver Logs de Ligações"])
    else:
        st.sidebar.success(f"Cliente: {st.session_state['cliente_dados']['nome_completo']}")
        menu = st.sidebar.radio("Painel Cliente", ["Buscar Serviços", "Meus Dados"])
    
    if st.sidebar.button("Sair / Logout"):
        st.session_state["user_logged"] = False
        st.session_state["user_type"] = None
        st.session_state["cliente_dados"] = None
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
        # Validação cruzando com as credenciais do seu Secrets
        if login_user.strip().upper() == st.secrets["ADMIN_USER"] and login_pass == st.secrets["ADMIN_PASS"]:
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
            supabase.table("app_servicos_detalhes").insert({
                "categoria": nova_cat.strip().capitalize(),
                "nome_detalhado": novo_serv.strip(),
                "preco": novo_preco
            }).execute()
            st.success(f"Botão/Serviço '{nova_cat}' atualizado com sucesso!")
            st.rerun()
            
    st.subheader("Tabela de Preços Cadastrados")
    res = supabase.table("app_servicos_detalhes").select("*").execute()
    if res.data:
        st.dataframe(res.data, use_container_width=True)

elif menu == "Cadastrar Profissional":
    st.title("👨‍🔧 Cadastrar Novo Profissional")
    nome = st.text_input("Nome Completo do Profissional")
    categorias_disponiveis = buscar_categorias()
    serv_principal = st.selectbox("Área de Atuação Principal", categorias_disponiveis)
    localidade = st.text_input("Cidade / Região de Atendimento")
    telefone = st.text_input("Telefone de Contato (WhatsApp)")
    
    if st.button("Cadastrar Profissional"):
        if nome and localidade and telefone:
            supabase.table("app_servicos_profissionais").insert({
                "nome": nome,
                "servico_principal": serv_principal,
                "localidade": localidade,
                "telefone": telefone
            }).execute()
            st.success("Profissional cadastrado com sucesso!")

elif menu == "Ver Logs de Ligações":
    st.title("📊 Histórico de Ligações Registradas")
    res = supabase.table("app_servicos_logs_ligacoes").select("*").order("horario", desc=True).execute()
    if res.data:
        st.dataframe(res.data, use_container_width=True)
    else:
        st.info("Nenhuma ligação registrada até o momento.")
# --- TELAS DO SISTEMA: 2. ÁREA DO CLIENTE (LOGIN/CADASTRO) ---
elif menu == "Área do Cliente" and not st.session_state["user_logged"]:
    st.title("📱 Acesso do Cliente")
    aba_login, aba_cadastro = st.tabs(["Já tenho cadastro", "Criar Nova Conta"])
    
    with aba_login:
        tel_login = st.text_input("Digite seu Telefone WhatsApp Cadastrado", key="login_tel")
        if st.button("Entrar"):
            res = supabase.table("app_servicos_clientes").select("*").eq("whatsapp", tel_login).execute()
            if res.data:
                st.session_state["user_logged"] = True
                st.session_state["user_type"] = "cliente"
                st.session_state["cliente_dados"] = res.data[0] # Pega o primeiro registro encontrado
                st.success(f"Bem-vindo de volta, {res.data[0]['nome_completo']}!")
                st.rerun()
            else:
                st.error("Telefone não encontrado. Cadastre-se na aba ao lado.")
                
    with aba_cadastro:
        nome_c = st.text_input("Nome Completo")
        endereco_c = st.text_input("Endereço Residencial")
        whats_c = st.text_input("WhatsApp (com DDD)")
        
        if st.button("Concluir Cadastro"):
            if nome_c and endereco_c and whats_c:
                res_check = supabase.table("app_servicos_clientes").select("*").eq("whatsapp", whats_c).execute()
                if res_check.data:
                    st.warning("Este telefone já está cadastrado.")
                else:
                    novo_cli = {"nome_completo": nome_c, "endereco": endereco_c, "whatsapp": whats_c}
                    supabase.table("app_servicos_clientes").insert(novo_cli).execute()
                    st.success("Cadastro efetuado! Faça o login na aba ao lado.")
# --- TELAS DO SISTEMA: 3. PAINEL DO CLIENTE LOGADO (BUSCA DINÂMICA) ---
elif menu == "Buscar Serviços":
    st.title(f"Olá, {st.session_state['cliente_dados']['nome_completo']}! Do que precisa hoje?")
    categorias = buscar_categorias()
    st.subheader("Selecione a categoria do serviço:")
    
    colunas = st.columns(len(categorias) if len(categorias) > 0 else 1)
    for idx, cat in enumerate(categorias):
        if colunas[idx].button(f"🔹 {cat}", use_container_width=True):
            st.session_state["categoria_ativa"] = cat

    if "categoria_ativa" in st.session_state:
        cat_ativa = st.session_state["categoria_ativa"]
        st.markdown(f"### 🛠️ Serviços disponíveis para: **{cat_ativa}**")
        servicos_detalhados = buscar_servicos_por_categoria(cat_ativa)
        
        if servicos_detalhados:
            col_esq, col_dir = st.columns()
            with col_esq:
                st.markdown("**Tabela de Preços Oficiais (Definidos por PRATTI):**")
                for s in servicos_detalhados:
                    st.write(f"• **{s['nome_detalhado']}**: R$ {s['preco']:.2f}")
            with col_dir:
                st.markdown("**Solicitar Atendimento:**")
                opcao_servico = st.selectbox("Qual serviço específico deseja?", [s['nome_detalhado'] for s in servicos_detalhados])
        else:
            st.info("Nenhum preço detalhado fixado para esta categoria ainda.")
            opcao_servico = cat_ativa

        st.markdown("#### 🧔 Profissionais Disponíveis na sua Área:")
        res_prof = supabase.table("app_servicos_profissionais").select("*").eq("servico_principal", cat_ativa).execute()
        
        if res_prof.data:
            for prof in res_prof.data:
                with st.container(border=True):
                    st.write(f"**Nome:** {prof['nome']}")
                    st.write(f"📍 **Localidade:** {prof['localidade']}")
                    st.write("Para falar com o profissional, use os botões abaixo:")
                    c1, c2 = st.columns(2)
                    
                    if c1.button(f"📞 Ligar para {prof['nome']}", key=f"ligar_{prof['id']}"):
                        registrar_ligacao(
                            cliente=st.session_state["cliente_dados"]["nome_completo"],
                            profissional=prof["nome"],
                            atendido=True
                        )
                        st.success(f"Ligação registrada com sucesso! Contato: {prof['telefone']}")
                        
                    if c2.button(f"❌ Chamei mas não atendeu", key=f"nao_atendeu_{prof['id']}"):
                        registrar_ligacao(
                            cliente=st.session_state["cliente_dados"]["nome_completo"],
                            profissional=prof["nome"],
                            atendido=False
                        )
                        st.warning(f"Tentativa de contato sem sucesso registrada para {prof['nome']}.")
        else:
            st.warning("Nenhum profissional cadastrado para esta categoria de serviço no momento.")

elif menu == "Meus Dados":
    st.title("👤 Meus Dados de Cadastro")
    st.write(f"**Nome:** {st.session_state['cliente_dados']['nome_completo']}")
    st.write(f"**Endereço de Atendimento:** {st.session_state['cliente_dados']['endereco']}")
    st.write(f"**WhatsApp:** {st.session_state['cliente_dados']['whatsapp']}")
