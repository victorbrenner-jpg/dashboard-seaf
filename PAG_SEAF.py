import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os
import urllib.request

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="Painel de Controle Financeiro SEAF - 2026", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Estilização CSS de Alto Padrão - Trazendo Vida e Modernidade Executiva
st.markdown("""
    <style>
    /* Estilização Geral do Fundo e Cards de Métrica */
    .metric-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border-left: 6px solid #002b49;
        padding: 18px 22px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 43, 73, 0.05);
        border: 1px solid #e2e8f0;
    }
    .div-titulo {
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
        color: #002b49;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    
    /* Arquitetura de Tabelas Modernas com Vida e Contraste */
    .tabela-container {
        width: 100% !important;
        margin-bottom: 30px !important;
        overflow: hidden !important;
        background-color: #ffffff;
    }
    .subtitulo-tabela-html {
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif !important;
        font-size: 14.5px !important;
        font-weight: 700 !important;
        padding: 14px 20px !important;
        color: #ffffff !important;
        margin: 0px !important;
        letter-spacing: 0.5px;
    }
    .html-executiva {
        width: 100% !important;
        border-collapse: collapse !important;
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif !important;
        font-size: 13px !important;
    }
    .html-executiva th {
        font-weight: 700 !important;
        padding: 14px 12px !important;
        text-align: center !important;
        border-bottom: 2px solid #cbd5e1 !important;
        background-color: #f8fafc !important;
        color: #475569 !important;
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 0.7px;
    }
    .html-executiva th:first-child {
        text-align: left !important;
        padding-left: 20px !important;
    }
    .html-executiva td {
        padding: 12px 12px !important;
        border-bottom: 1px solid #f1f5f9 !important;
        text-align: center !important;
        color: #334155 !important;
    }
    .html-executiva td:first-child {
        text-align: left !important;
        padding-left: 20px !important;
        font-weight: 600;
        color: #0f172a !important;
    }
    
    .gnd-badge {
        display: inline-block;
        width: 9px;
        height: 9px;
        border-radius: 50%;
        margin-right: 10px;
        vertical-align: middle;
    }
    
    .html-executiva tbody tr:nth-child(even) {
        background-color: #fdfdfd !important;
    }
    .html-executiva tbody tr:hover {
        background-color: #f1f5f9 !important;
    }
    
    .linha-total-html {
        font-weight: bold !important;
        background-color: #f8fafc !important;
    }
    .linha-total-html td {
        border-top: 2px solid #002b49 !important;
        border-bottom: 3px double #002b49 !important;
        color: #002b49 !important;
        font-size: 13.5px !important;
        font-weight: 700 !important;
    }
    </style>
""", unsafe_allow_html=True)

NOME_ARQUIVO_CSV = "C:/Users/victor.brenner/Desktop/Pagamentos_2026/base_2026.csv"

# -------------------------------------------------------------------------
# FUNÇÕES DE INFRAESTRUTURA E TRATAMENTO DE BANCO DE DADOS
# -------------------------------------------------------------------------
# Mude ou adicione a função de atualização para este modelo incremental:
def atualizar_banco_via_csv():
    """
    Lê o CSV e adiciona APENAS os registros novos no banco de dados,
    permitindo atualizações semanais e mensais sem apagar o histórico.
    """
    # Defina o caminho correto do seu CSV (use o 'r' antes para evitar erro de sintaxe)
    caminho_csv = r"C:\Users\victor.brenner\Desktop\Pagamentos_2026\02_Bases_Novas_Fontes\base_2026.csv"
    caminho_db = 'pagamentos2026.db'
    
    if not os.path.exists(caminho_csv):
        st.sidebar.error("Arquivo CSV não encontrado no caminho especificado.")
        return False
        
    try:
        # Tenta ler o arquivo CSV tratando possíveis codificações
        df_novo = None
        for enc in ['utf-8-sig', 'latin-1', 'cp1252', 'utf-8']:
            for sep_tentativa in [';', ',']:
                try:
                    df_novo = pd.read_csv(caminho_csv, sep=sep_tentativa, encoding=enc)
                    if df_novo is not None and len(df_novo.columns) > 1:
                        break
                except:
                    continue
            if df_novo is not None and len(df_novo.columns) > 1:
                break

        if df_novo is None:
            st.sidebar.error("Não foi possível ler o arquivo CSV.")
            return False

        # Padroniza o nome das colunas removendo espaços extras
        df_novo.columns = [str(c).strip() for c in df_novo.columns]
        
        # Identifica dinamicamente as colunas essenciais
        col_data = next((c for c in df_novo.columns if c.lower() in ["data emissão", "data emissao", "data", "dt_emissao"]), df_novo.columns[0])
        col_ob = next((c for c in df_novo.columns if 'OB' in c.upper() or 'NÚMERO' in c.upper() or 'NUMERO' in c.upper()), df_novo.columns[0])
        col_valor = next((c for c in df_novo.columns if 'VALOR' in c.upper()), df_novo.columns[-1])
        
        # Limpa linhas completamente nulas nas chaves principais
        df_novo = df_novo.dropna(subset=[col_data, col_ob, col_valor])
        
        # Cria uma coluna de ID ÚNICO combinando Número da OB e Data para evitar duplicados
        df_novo['id_controle'] = df_novo[col_ob].astype(str).str.strip() + "_" + df_novo[col_data].astype(str).str.strip()
        df_novo = df_novo.drop_duplicates(subset=['id_controle'])

        conn = sqlite3.connect(caminho_db)
        cursor = conn.cursor()
        
        # Garante que a tabela pagamentos exista e cria uma chave única pelo 'id_controle'
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pagamentos'")
        if not cursor.fetchone():
            # Se a tabela não existir, cria a primeira vez com os dados do DataFrame
            df_novo.to_sql('pagamentos', conn, if_exists='replace', index=False)
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_pag_controle ON pagamentos(id_controle)")
            conn.commit()
            st.sidebar.success(f"Banco inicializado com {len(df_novo)} registros.")
        else:
            # Se a tabela já existir, adiciona uma coluna 'id_controle' temporária se não houver no banco antigo
            cursor.execute("PRAGMA table_info(pagamentos)")
            colunas_bd = [info[1] for info in cursor.fetchall()]
            if 'id_controle' not in colunas_bd:
                cursor.execute("ALTER TABLE pagamentos ADD COLUMN id_controle TEXT")
                conn.commit()
            
            # Carrega o que já está salvo no banco para comparar
            ids_existentes = pd.read_sql_query("SELECT id_controle FROM pagamentos", conn)['id_controle'].dropna().tolist()
            
            # Filtra o DataFrame trazendo apenas o que é REALMENTE NOVO
            df_inserir = df_novo[~df_novo['id_controle'].isin(ids_existentes)].copy()
            
            if not df_inserir.empty:
                # Garante que as colunas do df que vai entrar batam com as que já existem no banco
                for col in colunas_bd:
                    if col not in df_inserir.columns:
                        df_inserir[col] = None
                df_inserir = df_inserir[colunas_bd]
                
                df_inserir.to_sql('pagamentos', conn, if_exists='append', index=False)
                st.sidebar.success(f"Sucesso! {len(df_inserir)} novos pagamentos adicionados.")
            else:
                st.sidebar.info("Nenhum registro novo detectado no CSV.")
                
        conn.close()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.sidebar.error(f"Erro ao processar atualização: {e}")
        return False


@st.cache_data(ttl=60)  # Atualiza os dados a cada 1 minuto
def carregar_dados_auditoria():
    """
    Lê os dados diretamente do link publicado da aba 'BASE' do Google Sheets.
    Aplica tratamentos para evitar o erro 'DataFrame object has no attribute str'.
    """
    # O link oficial que você acabou de gerar:
    LINK_PUBLICADO = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT6mS4X1SSJWjVhFxNdTstSWgRdn_AFSGf9ZzdGqZ1GjZNeT7GSUZDqoB_4q5JnZPbgd2gJ2Jq0g4YJ/pub?gid=0&single=true&output=csv"
    
    try:
        # Lê o CSV diretamente da publicação do Google
        df = pd.read_csv(LINK_PUBLICADO, sep=',')
    except Exception as e:
        st.error(f"Erro ao conectar com a aba 'BASE' do Google Sheets: {e}")
        return pd.DataFrame()
        
    if df.empty:
        return df

    # 1. REMOVE COLUNAS DUPLICADAS (Causa real do erro 'DataFrame object has no attribute str')
    # Se houver duas colunas com o mesmo nome, o pandas se confunde. Isso garante apenas a primeira.
    df = df.loc[:, ~df.columns.duplicated()]

    # 2. PADRONIZAÇÃO DE NOMES DE COLUNAS (Remove espaços extras nas pontas)
    df.columns = [str(c).strip() for c in df.columns]

    # 3. GARANTIA DE COLUNAS OBRIGATÓRIAS
    colunas_obrigatorias = [
        "Número", "UG Emitente", "UG Pagadora", "Data Emissão", "Status", "Tipo de OB", 
        "NE", "Credor", "Nome do Credor", "Valor", "Fonte", "Natureza", "Status de Envio", 
        "RE", "PD", "GRUPO", "Elemento", "Despesa", "OBJETO"
    ]
    for col in colunas_obrigatorias:
        if col not in df.columns:
            df[col] = None

    # --- 4. TRATAMENTOS ULTRA SEGUROS (Forçando conversão para Series/String antes do .str) ---

    # Tratamento da Despesa (CORRENTE, DEA, RP)
    df['Despesa_Tratada'] = 'CORRENTE'
    if 'Despesa' in df.columns:
        # Certifica que estamos pegando uma Series (coluna única) e tratando nulos
        serie_despesa = df['Despesa'].squeeze()
        if isinstance(serie_despesa, pd.DataFrame):
            serie_despesa = serie_despesa.iloc[:, 0]
        
        amostra = serie_despesa.fillna('').astype(str).str.upper()
        
        def classificar_texto(val):
            v = str(val).upper().strip()
            if 'DEA' in v or 'EXERC' in v or 'ANTERIOR' in v or 'RECONHECIMENTO' in v: 
                return 'DEA'
            elif 'RP' in v or 'RESTO' in v or 'PAGAR' in v: 
                return 'RP'
            else: 
                return 'CORRENTE'
        df['Despesa_Tratada'] = sample_apply = amostra.apply(classificar_texto)

    # Tratamento do Grupo (Investimentos)
    df['Grupo_Tratado'] = '3 - OUTRAS DESPESAS CORRENTES'
    if 'GRUPO' in df.columns:
        serie_grupo = df['GRUPO'].squeeze()
        if isinstance(serie_grupo, pd.DataFrame):
            serie_grupo = serie_grupo.iloc[:, 0]
            
        amostra_grupo = serie_grupo.fillna('').astype(str).str.strip().str.upper()
        df['Grupo_Tratado'] = amostra_grupo.apply(
            lambda v: '4 - INVESTIMENTOS' if 'INVEST' in v or '4' in v else '3 - OUTRAS DESPESAS CORRENTES'
        )
    
    # Tratamento Numérico do Valor Monetário
    if 'Valor' in df.columns:
        serie_valor = df['Valor'].squeeze()
        if isinstance(serie_valor, pd.DataFrame):
            serie_valor = serie_valor.iloc[:, 0]
            
        valores_str = serie_valor.fillna('0').astype(str)
        valores_str = valores_str.str.replace(r'[R$\s.]', '', regex=True).str.replace(',', '.')
        df['Valor_Limpo'] = pd.to_numeric(valores_str, errors='coerce').fillna(0.0)
    else:
        df['Valor_Limpo'] = 0.0
        
    # Tratamento de Datas e Geração do Mês por Extenso
    if 'Data Emissão' in df.columns:
        serie_data = df['Data Emissão'].squeeze()
        if isinstance(serie_data, pd.DataFrame):
            serie_data = serie_data.iloc[:, 0]
            
        df['Mes_Num'] = serie_data.fillna('').astype(str).str.slice(3, 5)
        mapa_meses = {
            '01': 'Jan/2026', '02': 'Fev/2026', '03': 'Mar/2026', '04': 'Abr/2026', 
            '05': 'Mai/2026', '06': 'Jun/2026', '07': 'Jul/2026', '08': 'Ago/2026',
            '09': 'Set/2026', '10': 'Out/2026', '11': 'Nov/2026', '12': 'Dez/2026'
        }
        df['Mes_Extenso'] = df['Mes_Num'].map(mapa_meses).fillna('Não Identificado')
    else:
        df['Mes_Extenso'] = 'Não Identificado'
    
    # Ajuste de Credores e Fontes
    df['Credor_Nome_Tratado'] = df['Nome do Credor'].fillna(df['Credor']).fillna('Não Identificado').astype(str).str.strip().str.upper()
    df['Fonte_Tratada'] = df['Fonte'].fillna('Não Informada').astype(str).str.strip()
        
    return df

    # --- TRATAMENTOS DE STRING SEGUROS CONTRA VALORES EM BRANCO ---
    df['Despesa_Tratada'] = 'CORRENTE'
    if 'Despesa' in df.columns:
        amostra = df['Despesa'].fillna('').astype(str).str.upper()
        def classificar_texto(val):
            v = str(val).upper().strip()
            if 'DEA' in v or 'EXERC' in v or 'ANTERIOR' in v: return 'DEA'
            elif 'RP' in v or 'RESTO' in v or 'PAGAR' in v: return 'RP'
            else: return 'CORRENTE'
        df['Despesa_Tratada'] = amostra.apply(classificar_texto)

    df['Grupo_Tratado'] = df['GRUPO'].fillna('').astype(str).str.strip().str.upper()
    df['Grupo_Tratado'] = df['Grupo_Tratado'].apply(lambda v: '4 - INVESTIMENTOS' if 'INVEST' in v or '4' in v else '3 - OUTRAS DESBAS CORRENTES')
    
    df['Valor_Limpo'] = df['Valor'].fillna('0').astype(str).str.replace(r'[R$\s.]', '', regex=True).str.replace(',', '.')
    df['Valor_Limpo'] = pd.to_numeric(df['Valor_Limpo'], errors='coerce').fillna(0)
        
    df['Mes_Num'] = df['Data Emissão'].fillna('').astype(str).str.slice(3, 5)
    mapa_meses = {
        '01': 'Jan/2026', '02': 'Fev/2026', '03': 'Mar/2026', '04': 'Abr/2026', 
        '05': 'Mai/2026', '06': 'Jun/2026', '07': 'Jul/2026', '08': 'Ago/2026',
        '09': 'Set/2026', '10': 'Out/2026', '11': 'Nov/2026', '12': 'Dez/2026'
    }
    df['Mes_Extenso'] = df['Mes_Num'].map(mapa_meses)
    df = df[df['Mes_Extenso'].notna()]
    
    df['Credor_Nome_Tratado'] = df['Nome do Credor'].fillna(df['Credor']).fillna('Não Identificado').astype(str).str.strip().str.upper()
    df['Fonte_Tratada'] = df['Fonte'].fillna('Não Informada').astype(str).str.strip()
        
    return df

    # --- MAPEAMENTO DA NATUREZA DA DESPESA (CORRENTE, RP, DEA) ---
    df['Despesa_Tratada'] = 'CORRENTE'
    for col_alvo in ['Despesa', 'Natureza', 'Status']:
        if col_alvo in df.columns and df[col_alvo].notna().any():
            amostra = df[col_alvo].astype(str).str.upper()
            if amostra.str.contains('RP|RESTO|DEA|ANTERIOR|EXERC').any():
                def classificar_texto(val):
                    v = str(val).upper().strip()
                    if 'DEA' in v or 'EXERC' in v or 'ANTERIOR' in v: return 'DEA'
                    elif 'RP' in v or 'RESTO' in v or 'PAGAR' in v: return 'RP'
                    else: return 'CORRENTE'
                df['Despesa_Tratada'] = amostra.apply(classificar_texto)
                break

    # --- PADRONIZAÇÃO DO GRUPO ORÇAMENTÁRIO (GND) ---
    df['Grupo_Tratado'] = df['GRUPO'].astype(str).str.strip().str.upper()
    
    def mapear_grupo_oficial(val):
        v = str(val).upper()
        if 'INVEST' in v or '4' in v: return '4 - INVESTIMENTOS'
        else: return '3 - OUTRAS DESPESAS CORRENTES'
    df['Grupo_Tratado'] = df['Grupo_Tratado'].apply(mapear_grupo_oficial)
    
    # --- SANEAMENTO MONETÁRIO DOS VALORES ---
    df['Valor_Limpo'] = df['Valor'].astype(str).str.replace(r'[R$\s.]', '', regex=True).str.replace(',', '.')
    df['Valor_Limpo'] = pd.to_numeric(df['Valor_Limpo'], errors='coerce').fillna(0)
        
    # --- TRATAMENTO CRONOLÓGICO DOS MESES ---
    df['Mes_Num'] = df['Data Emissão'].astype(str).str.slice(3, 5)
    
    mapa_meses = {
        '01': 'Jan/2026', '02': 'Fev/2026', '03': 'Mar/2026', '04': 'Abr/2026', 
        '05': 'Mai/2026', '06': 'Jun/2026', '07': 'Jul/2026', '08': 'Ago/2026',
        '09': 'Set/2026', '10': 'Out/2026', '11': 'Nov/2026', '12': 'Dez/2026'
    }
    df['Mes_Extenso'] = df['Mes_Num'].map(mapa_meses)
    df = df[df['Mes_Extenso'].notna()]
    
    if 'Nome do Credor' in df.columns:
        df['Credor_Nome_Tratado'] = df['Nome do Credor'].astype(str).str.strip().str.upper()
    else:
        df['Credor_Nome_Tratado'] = df['Credor'].astype(str).str.strip().str.upper()
        
    if 'Fonte' in df.columns:
        df['Fonte_Tratada'] = df['Fonte'].astype(str).str.strip()
    else:
        df['Fonte_Tratada'] = 'Não Informada'
        
    return df

try:
    df_base = carregar_dados_auditoria()
except Exception as e:
    st.error(f"Erro ao carregar colunas do banco: {e}")
    st.stop()

# --- DETECÇÃO AUTOMÁTICA DOS MESES EXISTENTES ---
ordem_meses_ano = ['Jan/2026', 'Fev/2026', 'Mar/2026', 'Abr/2026', 'Mai/2026', 'Jun/2026', 'Jul/2026', 'Ago/2026', 'Set/2026', 'Out/2026', 'Nov/2026', 'Dez/2026']
lista_meses_fixa = []
if not df_base.empty and 'Mes_Extenso' in df_base.columns:
    lista_meses_fixa = [m for m in ordem_meses_ano if m in df_base['Mes_Extenso'].unique()]

if not lista_meses_fixa:
    lista_meses_fixa = ['Jan/2026', 'Fev/2026', 'Mar/2026', 'Abr/2026', 'Mai/2026', 'Jun/2026']

# --- BARRA LATERAL ---
st.sidebar.markdown("### 🏛️ Filtros Globais")
st.sidebar.markdown("---")

meses_selecionados = st.sidebar.multiselect("Filtrar Período de Competência:", options=lista_meses_fixa, default=[])

nomes_disponiveis = sorted([n for n in df_base['Credor_Nome_Tratado'].unique() if n]) if not df_base.empty else []
nomes_selecionados = st.sidebar.multiselect("Filtrar por Entidade / Credor:", options=nomes_disponiveis, default=[])

st.sidebar.markdown("---")
lista_fontes = sorted([f for f in df_base['Fonte_Tratada'].unique() if f and f != 'nan']) if not df_base.empty else []
default_fonte = ['500'] if '500' in lista_fontes else []

fontes_selecionadas = st.sidebar.multiselect(
    "Filtrar por Fonte de Recurso:",
    options=lista_fontes,
    default=default_fonte,
    placeholder="Todas as fontes"
)

st.sidebar.markdown("---")
coluna_objeto = 'OBJETO'

if not df_base.empty and coluna_objeto in df_base.columns:
    lista_objetos = sorted(df_base[coluna_objeto].dropna().unique())
    objeto_selecionado = st.sidebar.multiselect(
        "Filtrar por Objeto de Despesa:",
        options=lista_objetos,
        default=[],
        placeholder="Todos os objetos"
    )
else:
    objeto_selecionado = []

st.sidebar.markdown("---")

# --- APLICAÇÃO DOS FILTROS EM CASCATA ---
df_filtrado = df_base.copy() if not df_base.empty else pd.DataFrame()
if not df_filtrado.empty:
    if meses_selecionados:
        df_filtrado = df_filtrado[df_filtrado['Mes_Extenso'].isin(meses_selecionados)]
    if nomes_selecionados:
        df_filtrado = df_filtrado[df_filtrado['Credor_Nome_Tratado'].isin(nomes_selecionados)]
    if fontes_selecionadas:
        df_filtrado = df_filtrado[df_filtrado['Fonte_Tratada'].isin(fontes_selecionadas)]
    if objeto_selecionado and coluna_objeto in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado[coluna_objeto].isin(objeto_selecionado)]

st.sidebar.markdown("### ⚙️ Atualizar Dados do Painel")
if st.sidebar.button("🔄 Incorporar Novos Pagamentos do CSV"):
    atualizar_banco_via_csv()
    st.rerun()

def formatar_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

# --- CABEÇALHO INSTITUCIONAL SEAF ---
st.markdown("<h2 class='div-titulo'>📊 Painel de Controle de Pagamentos — Exercício 2026</h2>", unsafe_allow_html=True)
st.markdown("##### *Secretaria Executiva de Finanças (SEAF) — Relatório de Prestação de Contas*")
st.markdown("---")

# --- BLOCO 1: PAINEL DE METRICAS GERENCIAIS ---
col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)

if not df_filtrado.empty:
    total_real_calculado = float(df_filtrado['Valor_Limpo'].sum())
    total_corrente = float(df_filtrado[df_filtrado['Despesa_Tratada'] == 'CORRENTE']['Valor_Limpo'].sum())
    total_rp = float(df_filtrado[df_filtrado['Despesa_Tratada'] == 'RP']['Valor_Limpo'].sum())
    total_dea = float(df_filtrado[df_filtrado['Despesa_Tratada'] == 'DEA']['Valor_Limpo'].sum())
    qtd_registros = int(df_filtrado.shape[0])
else:
    total_real_calculado = total_corrente = total_rp = total_dea = 0.0
    qtd_registros = 0

with col_kpi1:
    st.markdown(f"<div class='metric-card'><p style='color: #6c757d; font-size: 11px; font-weight: bold; margin:0;'>VALOR TOTAL PAGO</p><h3 style='color: #002b49; margin: 5px 0;'>{formatar_brl(total_real_calculado)}</h3><p style='color: #28a745; font-size: 11px; margin:0;'>📋 Registros: {qtd_registros:,}</p></div>", unsafe_allow_html=True)
with col_kpi2:
    st.markdown(f"<div class='metric-card'><p style='color: #6c757d; font-size: 11px; font-weight: bold; margin:0;'>CORRENTE</p><h3 style='color: #028090; margin: 5px 0;'>{formatar_brl(total_corrente)}</h3><p style='color: #6c757d; font-size: 11px; margin:0;'>Dotação do Ano</p></div>", unsafe_allow_html=True)
with col_kpi3:
    st.markdown(f"<div class='metric-card'><p style='color: #f77f00; font-size: 11px; font-weight: bold; margin:0;'>RESTOS A PAGAR (RP)</p><h3 style='color: #f77f00; margin: 5px 0;'>{formatar_brl(total_rp)}</h3><p style='color: #6c757d; font-size: 11px; margin:0;'>Exercícios Anteriores</p></div>", unsafe_allow_html=True)
with col_kpi4:
    st.markdown(f"<div class='metric-card'><p style='color: #d62828; font-size: 11px; font-weight: bold; margin:0;'>EXERC. ANTERIORES (DEA)</p><h3 style='color: #d62828; margin: 5px 0;'>{formatar_brl(total_dea)}</h3><p style='color: #6c757d; font-size: 11px; margin:0;'>Reconhecimento de Passivo</p></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- BLOCO 2: DEMONSTRATIVO DE DESPESAS SEPARADO POR TABELAS MESTRE ---
st.markdown("### 📋 1. Demonstrativo Analítico por tipo de Despesa")

if not df_filtrado.empty:
    df_matriz = df_filtrado.pivot_table(
        index=['Despesa_Tratada', 'Grupo_Tratado'],
        columns='Mes_Extenso',
        values='Valor_Limpo',
        aggfunc='sum',
        fill_value=0.0
    ).reset_index()

    for m in lista_meses_fixa:
        if m not in df_matriz.columns:
            df_matriz[m] = 0.0
            
    df_matriz['Total Geral'] = df_matriz[lista_meses_fixa].sum(axis=1)

    def renderizar_tabela_simetrica_html(df_origem, chave_natureza, grupos_obrigatorios, titulo_bloco, cor_hexa):
        linhas = []
        for gnd in grupos_obrigatorios:
            match = df_origem[(df_origem['Despesa_Tratada'] == chave_natureza) & (df_origem['Grupo_Tratado'] == gnd)]
            if not match.empty:
                linhas.append(match.iloc[0].to_dict())
            else:
                nova_linha = {'Despesa_Tratada': chave_natureza, 'Grupo_Tratado': gnd}
                for col_m in lista_meses_fixa + ['Total Geral']:
                    nova_linha[col_m] = 0.0
                linhas.append(nova_linha)
        
        linhas_corpo_html = ""
        totais_colunas = {m: 0.0 for m in lista_meses_fixa + ['Total Geral']}
        
        for row in linhas:
            colunas_valores = ""
            for m in lista_meses_fixa + ['Total Geral']:
                val = float(row[m])
                totais_colunas[m] += val
                colunas_valores += f"<td>{formatar_brl(val)}</td>"
            
            linhas_corpo_html += f"<tr><td><span class='gnd-badge' style='background-color: {cor_hexa};'></span>{row['Grupo_Tratado']}</td>{colunas_valores}</tr>"
            
        valores_totais_gnd = ""
        for m in lista_meses_fixa + ['Total Geral']:
            valores_totais_gnd += f"<td>{formatar_brl(totais_colunas[m])}</td>"
            
        cabecalhos_meses_html = "".join([f"<th style='width: 10%;'>{mes}</th>" for mes in lista_meses_fixa])

        html_completo = (
            f"<div class='tabela-container'>"
            f"<div class='subtitulo-tabela-html' style='background: linear-gradient(90deg, {cor_hexa} 0%, #002b49 100%);'>{titulo_bloco}</div>"
            f"<table class='html-executiva'>"
            f"<thead><tr>"
            f"<th style='width: 30%;'>GRUPO DO GASTO (GND)</th>"
            f"{cabecalhos_meses_html}"
            f"<th style='width: 10%;'>Total Geral</th>"
            f"</tr></thead>"
            f"<tbody>{linhas_corpo_html}"
            f"<tr class='linha-total-html'><td>📊 TOTAL GERAL DA NATUREZA</td>{valores_totais_gnd}</tr>"
            f"</tbody></table></div>"
        )
        st.markdown(html_completo, unsafe_allow_html=True)

    renderizar_tabela_simetrica_html(df_matriz, 'CORRENTE', ['3 - OUTRAS DESPESAS CORRENTES', '4 - INVESTIMENTOS'], "🔵 DESPESAS CORRENTES (Dotação Ordinária do Ano)", "#028090")
    renderizar_tabela_simetrica_html(df_matriz, 'RP', ['3 - OUTRAS DESPESAS CORRENTES'], "🟠 RESTOS A PAGAR - RP (Compromissos de Anos Anteriores)", "#f77f00")
    renderizar_tabela_simetrica_html(df_matriz, 'DEA', ['3 - OUTRAS DESPESAS CORRENTES', '4 - INVESTIMENTOS'], "🔴 DESPESAS DE EXERCÍCIOS ANTERIORES - DEA (Reconhecimento de Passivo)", "#d62828")

else:
    st.info("Nenhum registro financeiro localizado. Certifique-se de que o arquivo 'base_2026.csv' está na pasta raiz e clique em 'Importar e Filtrar Novo CSV' na barra lateral.")

st.markdown("---")

# --- BLOCO 3: TEMPORAL + CREDORES ---
st.markdown("### 📊 2. Análise Temporal e Desembolso Mensal")

if not df_filtrado.empty:
    df_agrupado_mes = df_filtrado.groupby("Mes_Extenso").agg(
        Qtd_Docs=("Valor_Limpo", "count"),
        Total_Liq=("Valor_Limpo", "sum")
    ).reset_index()

    df_agrupado_mes = df_agrupado_mes.rename(columns={"Mes_Extenso": "Mês de Referência"})
    df_agrupado_mes["Mês de Referência"] = pd.Categorical(df_agrupado_mes["Mês de Referência"], categories=lista_meses_fixa, ordered=True)
    df_agrupado_mes = df_agrupado_mes.sort_values("Mês de Referência").fillna(0)

    for m in lista_meses_fixa:
        if m not in df_agrupado_mes["Mês de Referência"].values:
            nova_linha_vazia = pd.DataFrame([{"Mês de Referência": m, "Qtd_Docs": 0, "Total_Liq": 0.0}])
            df_agrupado_mes = pd.concat([df_agrupado_mes, nova_linha_vazia], ignore_index=True)

    df_agrupado_mes["Mês de Referência"] = pd.Categorical(df_agrupado_mes["Mês de Referência"], categories=lista_meses_fixa, ordered=True)
    df_agrupado_mes = df_agrupado_mes.sort_values("Mês de Referência")

    with st.container(border=True):
        col_grafico, col_tabela = st.columns([1.1, 0.9], gap="large")
        
        with col_grafico:
            st.markdown("<p style='font-weight: 700; color: #002b49; margin-bottom: 5px; font-family: sans-serif;'>Curva Crítica de Desembolso Mensal</p>", unsafe_allow_html=True)
            
            def formatar_dinamico_br(x):
                if x >= 1_000_000:
                    valor_m = x / 1_000_000
                    return f"R$ {valor_m:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".") + "M"
                elif x >= 1_000:
                    valor_k = int(x / 1_000)
                    return f"R$ {valor_k:,}".replace(",", ".") + "K"
                elif x > 0:
                    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                return "R$ 0"

            fig = px.line(
                df_agrupado_mes, 
                x="Mês de Referência", 
                y="Total_Liq",
                markers=True,
                text=df_agrupado_mes["Total_Liq"].apply(formatar_dinamico_br),
                hover_data={"Qtd_Docs": True, "Total_Liq": ":,.2f"}
            )
            
            fig.update_traces(
                line=dict(color="#028090", width=4),
                marker=dict(size=10, color="#f77f00", symbol="circle"),
                textposition="top center"
            )
            
            fig.update_layout(
                xaxis=dict(title=None, showgrid=False, tickfont=dict(size=11, color="#475569")),
                yaxis=dict(
                    title=None, 
                    showgrid=True, 
                    gridcolor="rgba(218, 224, 233, 0.6)", 
                    tickfont=dict(size=11, color="#475569"),
                    tickformat=",.0f" 
                ),
                margin=dict(l=10, r=10, t=30, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=320
            )
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
        with col_tabela:
            st.markdown("<p style='font-weight: 700; color: #002b49; margin-bottom: 12px; font-family: sans-serif;'>Resumo Gerencial por Mês</p>", unsafe_allow_html=True)
            
            total_documentos = int(df_agrupado_mes["Qtd_Docs"].sum())
            total_financeiro = float(df_agrupado_mes["Total_Liq"].sum())
            
            linhas_tabela_html = ""
            for _, row in df_agrupado_mes.iterrows():
                valor_formatado = formatar_brl(row['Total_Liq'])
                linhas_tabela_html += f'<tr style="border-bottom: 1px solid #f1f5f9;"><td style="padding: 10px 15px; text-align: left; color: #334155; font-family: sans-serif; font-size: 13px;">{row["Mês de Referência"]}</td><td style="padding: 10px 15px; text-align: center; color: #334155; font-family: sans-serif; font-size: 13px;">{int(row["Qtd_Docs"]):,}</td><td style="padding: 10px 15px; text-align: right; color: #0f172a; font-family: sans-serif; font-size: 13px; font-weight: 600;">{valor_formatado}</td></tr>'
                
            html_tabela_gerencial = (
                f'<div style="border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; background-color: #ffffff; width: 100%;">'
                f'<table style="width: 100%; border-collapse: collapse; text-align: left; margin: 0; padding: 0;">'
                f'<thead>'
                f'<tr style="background-color: #f8fafc; border-bottom: 1px solid #e2e8f0;">'
                f'<th style="padding: 12px 15px; font-family: sans-serif; font-size: 11px; font-weight: 700; color: #475569; text-align: left;">MÊS DE REFERÊNCIA</th>'
                f'<th style="padding: 12px 15px; font-family: sans-serif; font-size: 11px; font-weight: 700; color: #475569; text-align: center;">QTD. DOCS</th>'
                f'<th style="padding: 12px 15px; font-family: sans-serif; font-size: 11px; font-weight: 700; color: #475569; text-align: right;">TOTAL PAGO</th>'
                f'</tr>'
                f'</thead>'
                f'<tbody>{linhas_tabela_html}</tbody>'
                f'<tfoot>'
                f'<tr style="background-color: #f8fafc; border-top: 2px solid #002b49; font-weight: 700;">'
                f'<td style="padding: 12px 15px; font-family: sans-serif; font-size: 13px; color: #002b49; text-align: left;">📊 TOTAL GERAL</td>'
                f'<td style="padding: 12px 15px; font-family: sans-serif; font-size: 13px; color: #002b49; text-align: center;">{total_documentos:,}</td>'
                f'<td style="padding: 12px 15px; font-family: sans-serif; font-size: 13px; color: #002b49; text-align: right;">{formatar_brl(total_financeiro)}</td>'
                f'</tr>'
                f'</tfoot>'
                f'</table>'
                f'</div>'
            )
            st.html(html_tabela_gerencial)

    # --- DEMONSTRATIVO POR CREDOR ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🏢 3. Detalhamento de Pagamentos por Credor / Entidade")
    
    df_matriz_credor = df_filtrado.pivot_table(
        index='Credor_Nome_Tratado',
        columns='Mes_Extenso',
        values='Valor_Limpo',
        aggfunc='sum',
        fill_value=0.0
    ).reset_index()

    for m in lista_meses_fixa:
        if m not in df_matriz_credor.columns:
            df_matriz_credor[m] = 0.0

    df_matriz_credor['Total Geral'] = df_matriz_credor[lista_meses_fixa].sum(axis=1)
    df_matriz_credor = df_matriz_credor.sort_values(by='Total Geral', ascending=False)

    cabecalhos_meses_html = "".join([f"<th style='width: 10%;'>{mes}</th>" for mes in lista_meses_fixa])
    
    linhas_corpo_credor = ""
    totais_colunas_credor = {m: 0.0 for m in lista_meses_fixa + ['Total Geral']}

    for _, row in df_matriz_credor.iterrows():
        colunas_valores = ""
        for m in lista_meses_fixa + ['Total Geral']:
            val = float(row[m])
            totais_colunas_credor[m] += val
            colunas_valores += f"<td>{formatar_brl(val)}</td>"
        
        linhas_corpo_credor += f"<tr><td style='padding-left: 20px; text-align: left;'>{row['Credor_Nome_Tratado']}</td>{colunas_valores}</tr>"

    valores_totais_credor = ""
    for m in lista_meses_fixa + ['Total Geral']:
        valores_totais_credor += f"<td>{formatar_brl(totais_colunas_credor[m])}</td>"

    html_completo_credor = (
        f"<div class='tabela-container'>"
        f"<div class='subtitulo-tabela-html' style='background: linear-gradient(90deg, #002b49 0%, #475569 100%);'>"
        f"💼 Distribuição Mensal de Recursos por Fornecedor / Prestador de Serviço"
        f"</div>"
        f"<table class='html-executiva'>"
        f"<thead><tr>"
        f"<th style='width: 30%; text-align: left; padding-left: 20px;'>RAZÃO SOCIAL / CREDOR</th>"
        f"{cabecalhos_meses_html}"
        f"<th style='width: 10%;'>Total Geral</th>"
        f"</tr></thead>"
        f"<tbody>{linhas_corpo_credor}"
        f"<tr class='linha-total-html'><td style='padding-left: 20px; text-align: left;'>📊 TOTAL CONSOLIDADO DO FILTRO</td>{valores_totais_credor}</tr>"
        f"</tbody></table></div>"
    )
    st.markdown(html_completo_credor, unsafe_allow_html=True)

else:
    st.info("Nenhum dado mensal disponível para exibição.")