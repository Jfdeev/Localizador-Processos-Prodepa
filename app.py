import streamlit as st
import pandas as pd
from fpdf import FPDF

# Configuração da página
st.set_page_config(page_title="Localizador de Processos PAE", layout="wide")
st.title("Localizador de Processos PAE")

def exportar_pdf(df: pd.DataFrame) -> bytes:
    cols = ['PAE', 'CLIENTE', 'Andamento', 'Status contratual',
            'Vigência Início','Vigência Término','VALOR GLOBAL ATUAL','Setor']
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

    for h in export_df.columns:
        pdf.cell(col_w, row_h, str(h), border=1, align='C')
    pdf.ln(row_h)

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

    # Parse de datas
    for date_col in [
        'Data Vigência Original', 'Vigência Início',
        'Vigência Término', 'DATA ULTIMA TRAMITAÇÃO'
    ]:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')

    # Conversão numérica
    if 'Vencimento em dias' in df.columns:
        df['Vencimento em dias'] = pd.to_numeric(df['Vencimento em dias'], errors='coerce')

    # Unificação de colunas
    if 'SETOR ATUAL' in df.columns:
        df['Setor'] = df['SETOR ATUAL']
    if 'N PAE' in df.columns:
        df['PAE'] = df['N PAE']

    # Normaliza o nome da coluna de serviços (pode vir como 'SERVIÇO' ou 'Servico')
    for orig in ['SERVIÇO', 'Servico', 'SERVICO']:
        if orig in df.columns:
            df.rename(columns={orig: 'Serviço'}, inplace=True)
            break

    return df

# Carrega dados
data = load_data()

# Explode a coluna Serviço em linhas únicas
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

# ——— SIDEBAR: FILTROS ———
st.sidebar.header("Filtros")

# Cliente
clientes = sorted(data['CLIENTE'].dropna().unique()) if 'CLIENTE' in data.columns else []
if 'clientes_selecionados' not in st.session_state:
    st.session_state.clientes_selecionados = clientes[:1] if clientes else []
col1, col2 = st.sidebar.columns(2)
if col1.button('✅ Todos'): st.session_state.clientes_selecionados = clientes.copy()
if col2.button('❌ Nenhum'): st.session_state.clientes_selecionados = []
selected_clientes = st.sidebar.multiselect(
    "Cliente", clientes,
    default=st.session_state.clientes_selecionados,
    key='clientes_selecionados'
)

# Andamento e Status Contratual
andamento = sorted(data['Andamento'].dropna().unique()) if 'Andamento' in data.columns else []
status = sorted(data['Status contratual'].dropna().unique()) if 'Status contratual' in data.columns else []
selected_andamento = st.sidebar.multiselect("Andamento", andamento, default=andamento)
selected_status = st.sidebar.multiselect("Status Contratual", status, default=status)

# Mês e Ano de Vencimento
st.sidebar.subheader("Filtro por Mês e Ano de Vencimento")
meses = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
mes_selecionado = st.sidebar.selectbox("Mês", range(1,13), format_func=lambda i: meses[i-1])
ano_selecionado = st.sidebar.number_input("Ano", 2000, 2035, value=pd.Timestamp.now().year)

# Ano de Vencimento
st.sidebar.subheader("Filtro por Ano de Vencimento")
ano_vencimento = st.sidebar.number_input("Ano de vencimento", 2000, 2035, value=pd.Timestamp.now().year)

# Serviço
st.sidebar.subheader("Filtro por Serviço")
selected_servicos = st.sidebar.multiselect(
    "Serviço(s):", servico_unicos, default=servico_unicos
)

# ——— APLICAÇÃO DOS FILTROS ———
# DataFrame base para filtros combinados
df = data.copy()

# Busca por mês/ano de término
if 'Vigência Término' in df.columns:
    df['Mês de Vencimento']   = df['Vigência Término'].dt.month
    df['Ano de Vencimento']   = df['Vigência Término'].dt.year
    df = df[
        (df['Mês de Vencimento']==mes_selecionado) &
        (df['Ano de Vencimento']==ano_selecionado)
    ]

# Filtro por Ano de vencimento
df_ano = data[data.get('Ano de Vencimento', data['Vigência Término'].dt.year)==ano_vencimento] \
    if 'Vigência Término' in data.columns else pd.DataFrame()

# Filtrar por Cliente, Andamento, Status
if selected_clientes:
    df = df[df['CLIENTE'].isin(selected_clientes)]
df = df[df['Andamento'].isin(selected_andamento)]
df = df[df['Status contratual'].isin(selected_status)]

# Filtrar por Serviço (qualquer correspondência)
if selected_servicos:
    paes_com_servico = servico_expandidos.query("Serviço in @selected_servicos")['PAE']
    df_servico = data[data['PAE'].isin(paes_com_servico)]
else:
    df_servico = pd.DataFrame()

# ——— EXIBIÇÃO ———
st.subheader(f"Contratos com vencimento em {meses[mes_selecionado-1]} de {ano_selecionado}")
st.markdown(f"**Total:** {len(df)}")
st.dataframe(df)
if not df.empty:
    st.download_button("📄 Baixar (mês/ano)", exportar_pdf(df), "mes_ano.pdf", "application/pdf")

st.subheader(f"Contratos com vencimento no ano {ano_vencimento}")
st.markdown(f"**Total:** {len(df_ano)}")
st.dataframe(df_ano)
if not df_ano.empty:
    st.download_button("📄 Baixar (ano)", exportar_pdf(df_ano), "ano.pdf", "application/pdf")

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
