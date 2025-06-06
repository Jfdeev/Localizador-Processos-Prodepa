import streamlit as st
import pandas as pd
from fpdf import FPDF

# Configuração da página
st.set_page_config(page_title="Localizador de Processos PAE", layout="wide")
st.title("Localizador de Processos PAE")

def exportar_pdf(df: pd.DataFrame) -> bytes:
    cols = ['PAE', 'CLIENTE', 'Andamento', 'Setor', 'Status contratual',
            'Vigência Início','Vigência Término','VALOR GLOBAL ATUAL', 'CONTRATO', 'Instrumento Contratual']
    export_df = df[cols] if set(cols).issubset(df.columns) else df.copy()

    for date_col in ['Vigência Início', 'Vigência Término']:
        if date_col in export_df.columns:
            export_df[date_col] = export_df[date_col].dt.strftime('%d/%m/%Y')

    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(True, 15)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Relatório de Processos Filtrados', 0, 1, 'C')
    pdf.ln(4)
    pdf.set_font('Arial', '', 8)
    epw = pdf.w - 2*pdf.l_margin
    col_w = epw / len(export_df.columns)
    row_h = pdf.font_size * 1.5

    # Cabeçalhos
    for h in export_df.columns:
        pdf.cell(col_w, row_h, str(h), border=1, align='C')
    pdf.ln(row_h)

    # Linhas
    for row in export_df.itertuples(index=False):
        for val in row:
            txt = str(val)
            pdf.cell(col_w, row_h, txt[:20] + ('...' if len(txt) > 20 else ''), border=1)
        pdf.ln(row_h)

    return pdf.output(dest='S').encode('latin-1')

def load_data() -> pd.DataFrame:
    url = (
        "https://docs.google.com/spreadsheets/d/e/"
        "2PACX-1vRY-kZhxw0D2wTEfX9DXzlrTyatD8kiBk1KMFEhUdD_ix-lsWXSMhBIy9HCxaVmhFShAWhwcuxhbqRT/pub?output=csv"
    )
    try:
        df = pd.read_csv(url)
        df.columns = [col.strip() for col in df.columns]
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {e}")
        return pd.DataFrame()

    for date_col in [
        'Data Vigência Original', 'Vigência Início',
        'Vigência Término', 'DATA ULTIMA TRAMITAÇÃO'
    ]:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')

    if 'Vencimento em dias' in df.columns:
        df['Vencimento em dias'] = pd.to_numeric(df['Vencimento em dias'], errors='coerce')

    if 'SETOR ATUAL' in df.columns:
        df['Setor'] = df['SETOR ATUAL']
    if 'N PAE' in df.columns:
        df['PAE'] = df['N PAE']

    for orig in ['SERVIÇO', 'Servico', 'SERVICO']:
        if orig in df.columns:
            df.rename(columns={orig: 'Serviço'}, inplace=True)
            break

    return df

# Carrega dados
data = load_data()

# Expande coluna Serviço
if 'Serviço' in data.columns:
    servico_expandidos = (
        data[['PAE', 'Serviço']]
        .dropna(subset=['Serviço'])
        .assign(Serviço=lambda d: d['Serviço'].str.split(','))
        .explode('Serviço')
    )
    servico_expandidos['Serviço'] = servico_expandidos['Serviço'].str.strip()
    servico_unicos = sorted(servico_expandidos['Serviço'].unique())
else:
    servico_unicos = []

# SIDEBAR
st.sidebar.header("Filtros")
clientes = sorted(data.get('CLIENTE', []).dropna().unique()) if 'CLIENTE' in data.columns else []
if 'clientes_selecionados' not in st.session_state:
    st.session_state.clientes_selecionados = clientes.copy()
col1, col2 = st.sidebar.columns(2)
if col1.button('✅ Todos'): st.session_state.clientes_selecionados = clientes.copy()
if col2.button('❌ Nenhum'): st.session_state.clientes_selecionados = []
selected_clientes = st.sidebar.multiselect("Cliente", clientes, default=st.session_state.clientes_selecionados, key='clientes_selecionados')
andamento = sorted(data.get('Andamento', []).dropna().unique()) if 'Andamento' in data.columns else []
status = sorted(data.get('Status contratual', []).dropna().unique()) if 'Status contratual' in data.columns else []
selected_andamento = st.sidebar.multiselect("Andamento", andamento, default=andamento)
selected_status = st.sidebar.multiselect("Status Contratual", status, default=status)

# Mês/Ano Vencimento
st.sidebar.subheader("Filtro por Mês e Ano de Vencimento")
meses = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
mes_selecionado = st.sidebar.selectbox("Selecione o mês", range(1,13), format_func=lambda x: meses[x-1])
ano_selecionado = st.sidebar.number_input("Selecione o ano", 2000, 2035, value=pd.Timestamp.now().year)

# Ano Vencimento
st.sidebar.subheader("Filtro por Ano de Vencimento")
ano_vencimento = st.sidebar.number_input("Ano de vencimento", 2000, 2035, value=pd.Timestamp.now().year)

# Serviço
st.sidebar.subheader("Filtro por Serviço")
selected_servicos = st.sidebar.multiselect("Serviço(s):", servico_unicos, default=servico_unicos)

# APLICA FILTROS
# Base geral
df = data.copy()
# Filtra Cliente, Andamento, Status
if selected_clientes:
    df = df[df['CLIENTE'].isin(selected_clientes)]
if andamento:
    df = df[df['Andamento'].isin(selected_andamento)]
if status:
    df = df[df['Status contratual'].isin(selected_status)]

# Exibição: tabela geral após filtros básicos
st.subheader("Processos filtrados - Cliente, Andamento e Status")
st.markdown(f"**Total:** {len(df)}")
st.dataframe(df)
if not df.empty:
    st.download_button("📄 Baixar (geral)", exportar_pdf(df), "geral.pdf", "application/pdf")

# Filtra Mês/Ano vencimento sobre df
if 'Vigência Término' in data.columns:
    data['Mês de Vencimento'] = data['Vigência Término'].dt.month
    data['Ano de Vencimento'] = data['Vigência Término'].dt.year
    df_mes_ano = data[(data['Mês de Vencimento']==mes_selecionado)&(data['Ano de Vencimento']==ano_selecionado)]
else:
    df_mes_ano = pd.DataFrame()

st.subheader(f"Contratos com vencimento em {meses[mes_selecionado-1]} de {ano_selecionado}")
st.markdown(f"**Total:** {len(df_mes_ano)}")
st.dataframe(df_mes_ano)
if not df_mes_ano.empty:
    st.download_button("📄 Baixar (mês/ano)", exportar_pdf(df_mes_ano), "mes_ano.pdf", "application/pdf")

# Filtra Ano vencimento sobre data original
if 'Vigência Término' in data.columns:
    data['Ano de Vencimento'] = data['Vigência Término'].dt.year
    df_ano = data[data['Ano de Vencimento'] == ano_vencimento]
else:
    df_ano = pd.DataFrame()

st.subheader(f"Contratos com vencimento no ano {ano_vencimento}")
st.markdown(f"**Total:** {len(df_ano)}")
st.dataframe(df_ano)
if not df_ano.empty:
    st.download_button("📄 Baixar (ano)", exportar_pdf(df_ano), "ano.pdf", "application/pdf")

# Filtrar por Serviço
if selected_servicos:
    paes_com_servico = servico_expandidos.query("Serviço in @selected_servicos")['PAE']
    df_servico = data[data['PAE'].isin(paes_com_servico)]
else:
    df_servico = pd.DataFrame()

st.subheader("Processos filtrados por Serviço")
st.markdown(f"**Total:** {len(df_servico)}")
st.dataframe(df_servico)
if not df_servico.empty:
    st.download_button("📄 Baixar (serviço)", exportar_pdf(df_servico), "servico.pdf", "application/pdf")

# Busca por Número de Processo
st.subheader("Busca por Número do Processo")
search_text = st.text_input("Digite parte do número:")
options = sorted(data['PAE'].dropna().astype(str).unique())
if search_text:
    options = [o for o in options if search_text in o]
selected = st.selectbox("Selecione:", options) if options else None
df_search = data[data['PAE'].astype(str)==selected] if selected else pd.DataFrame()

st.markdown(f"**Total:** {len(df_search)}")
st.dataframe(df_search)
if not df_search.empty:
    st.download_button("📄 Baixar (busca)", exportar_pdf(df_search), "busca.pdf", "application/pdf")
