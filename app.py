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
# Adicione esta linha temporariamente para forçar o Streamlit a apagar a memória antiga:
st.cache_resource.clear()

@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["URL_SUPABASE"]
    key = st.secrets["KEY_SUPABASE"]
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"Erro técnico na conexão: {e}")
    st.info("Verifique se as chaves no Secrets estão idênticas ao seu arquivo toml.")
    st.stop()

# --- CONTROLE DE SESSÃO (STATE) ---
if "user_logged" not in st.session_state:
    st.session_state["user_logged"] = False
if "user_type" not in st.session_state:
    st.session_state["user_type"] = None  # 'admin' ou 'cliente'
if "cliente_dados" not in st.session_state:
    st.session_state["cliente_dados"] = None
    
# --- LÓGICA DAS FUNÇÕES DO BANCO (Com proteção anticaída) ---
def buscar_categorias():
    try:
        res = supabase.table("app_servicos_detalhes").select("categoria").execute()
        if res.data:
            return list(set([item['categoria'] for item in res.data]))
    except Exception as e:
        # Se a tabela não existir ou der erro de privilégio, exibe o aviso mas não trava
        st.sidebar.warning("⚠️ Tabelas não detectadas no Supabase. Usando dados locais temporários.")
    
    # Retorno padrão de contingência caso o banco falhe
    return ["Elétrica", "Hidráulica", "Pintura"]

def buscar_servicos_por_categoria(cat):
    try:
        res = supabase.table("app_servicos_detalhes").select("*").eq("categoria", cat).execute()
        if res.data:
            return res.data
    except Exception:
        pass
    
    # Dados fictícios locais para o app funcionar mesmo se o banco falhar
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
    try:
        supabase.table("app_servicos_logs_ligacoes").insert(dados).execute()
    except Exception:
        st.info(f"📌 [Modo Local] Ligação para {profissional} registrada na tela.")

    
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
            try:
                supabase.table("app_servicos_detalhes").insert({
                    "categoria": nova_cat.strip().capitalize(),
                    "nome_detalhado": novo_serv.strip(),
                    "preco": novo_preco
                }).execute()
                st.success(f"Botão/Serviço '{nova_cat}' atualizado com sucesso!")
                st.rerun()
            except Exception as error_db:
                st.error(f"Erro ao salvar no banco: {error_db}. Verifique se a tabela existe.")
            
    st.subheader("Tabela de Preços Cadastrados")
    # --- CORREÇÃO DA LINHA 107 COM TRATAMENTO DE ERROS ---
    try:
        res = supabase.table("app_servicos_detalhes").select("*").execute()
        if res.data:
            st.dataframe(res.data, use_container_width=True)
        else:
            st.info("Nenhum preço cadastrado no banco de dados.")
    except Exception as e:
        st.error("⚠️ Não foi possível carregar a tabela física do Supabase.")
        st.info("Motivo: A tabela 'app_servicos_detalhes' não foi encontrada com as credenciais atuais. O app usará dados em memória.")

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
            st.info("Nenhuma ligação registrada até o momento.")
    except Exception:
        st.warning("Histórico indisponível sem as tabelas do Supabase prontas.")

# --- TELAS DO SISTEMA: 2. ÁREA DO CLIENTE (LOGIN/CADASTRO) ---
elif menu == "Área do Cliente" and not st.session_state["user_logged"]:
    st.title("📱 Acesso do Cliente")
    aba_login, aba_cadastro = st.tabs(["Já tenho cadastro", "Criar Nova Conta"])
    
    with aba_login:
        tel_login = st.text_input("Digite seu Telefone WhatsApp Cadastrado", key="login_tel")
        if st.button("Entrar"):
            res = supabase.table("app_servicos_clientes").select("*").eq("whatsapp", tel_login).execute()
            # Correção: Verificar se a lista retornada não está vazia e pegar o primeiro elemento [0]
            if res.data and len(res.data) > 0:
                st.session_state["user_logged"] = True
                st.session_state["user_type"] = "cliente"
                st.session_state["cliente_dados"] = res.data[0]  # Acessa o primeiro item da lista
                st.success(f"Bem-vindo de volta, {st.session_state['cliente_dados']['nome_completo']}!")
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
                if res_check.data and len(res_check.data) > 0:
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
        
        profissionais_falsos = [
            {"id": 1, "nome": "Carlos Silva", "localidade": "Centro", "telefone": "11999999999"}
        ]
        
        try:
            res_prof = supabase.table("app_servicos_profissionais").select("*").eq("servico_principal", cat_ativa).execute()
            lista_prof = res_prof.data if res_prof.data else profissionais_falsos
        except Exception:
            lista_prof = profissionais_falsos
        
        for prof_item in lista_prof:
            with st.container(border=True):
                st.write(f"**Nome:** {prof_item['nome']}")
                st.write(f"📍 **Localidade:** {prof_item['localidade']}")
                st.write("Para falar com o profissional, use os botões abaixo:")
                c1, c2 = st.columns(2)
                
                if c1.button(f"📞 Ligar para {prof_item['nome']}", key=f"ligar_{prof_item['id']}"):
                    registrar_ligacao(
                        cliente=st.session_state["cliente_dados"]["nome_completo"],
                        profissional=prof_item["nome"],
                        atendido=True
                    )
                    st.success(f"Ligação registrada! Contato: {prof_item['telefone']}")
                    
                if c2.button(f"❌ Chamei mas não atendeu", key=f"nao_atendeu_{prof_item['id']}"):
                    registrar_ligacao(
                        cliente=st.session_state["cliente_dados"]["nome_completo"],
                        profissional=prof_item["nome"],
                        atendido=False
                    )
                    st.warning(f"Tentativa de contato sem sucesso registrada.")

elif menu == "Meus Dados":
    st.title("👤 Meus Dados de Cadastro")
    st.write(f"**Nome:** {st.session_state['cliente_dados']['nome_completo']}")
    st.write(f"**Endereço de Atendimento:** {st.session_state['cliente_dados']['endereco']}")
    st.write(f"**WhatsApp:** {st.session_state['cliente_dados']['whatsapp']}")
