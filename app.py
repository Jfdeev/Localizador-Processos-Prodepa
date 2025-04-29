import streamlit as st
import pandas as pd
from fpdf import FPDF

# Configuração da página
st.set_page_config(page_title="Localizador de Processos PAE", layout="wide")
st.title("Localizador de Processos PAE")

# Função para carregar os dados
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

    return df

# Carrega dados
data = load_data()

# Sidebar: filtros de Cliente
st.sidebar.header("Filtros")
clientes = sorted(data['CLIENTE'].dropna().unique()) if 'CLIENTE' in data.columns else []

# Inicialização de session_state
if 'clientes_selecionados' not in st.session_state:
    # Se houver mais de um cliente, pré-seleciona todos; senão, deixa vazio
    st.session_state.clientes_selecionados = clientes.copy() if len(clientes) > 1 else []

# Botões de seleção rápida
col1, col2 = st.sidebar.columns(2)
if col1.button('✅ Todos'):
    st.session_state.clientes_selecionados = clientes.copy()
if col2.button('❌ Nenhum'):
    st.session_state.clientes_selecionados = []

# Multiselect fora de formulário, atualiza imediatamente
selected_clientes = st.sidebar.multiselect(
    "Cliente",
    options=clientes,
    default=st.session_state.clientes_selecionados,
    key='clientes_selecionados',
    help="Selecione um ou mais clientes"
)

# Outros filtros
andamento = sorted(data['Andamento'].dropna().unique()) if 'Andamento' in data.columns else []
selected_andamento = st.sidebar.multiselect("Andamento", andamento, default=andamento)

status = sorted(data['Status contratual'].dropna().unique()) if 'Status contratual' in data.columns else []
selected_status = st.sidebar.multiselect("Status Contratual", status, default=status)

# Busca por número de processo
st.subheader("Busca por Número do Processo")
search_text = st.text_input("Digite parte do número do processo:")
num_processo = sorted(data['PAE'].dropna().unique()) if 'PAE' in data.columns else []
sugestoes = [str(p) for p in num_processo if search_text and search_text in str(p)]
selected_processo = None
if sugestoes:
    selected_processo = st.selectbox("Selecione o processo:", sugestoes)

# Aplica filtros
df = data.copy()
if selected_processo:
    df = df[df['PAE'].astype(str) == selected_processo]
else:
    if 'CLIENTE' in df.columns and selected_clientes:
        df = df[df['CLIENTE'].isin(selected_clientes)]
    if 'Andamento' in df.columns:
        df = df[df['Andamento'].isin(selected_andamento)]
    if 'Status contratual' in df.columns:
        df = df[df['Status contratual'].isin(selected_status)]

# Exibição dos resultados
st.markdown(f"**Total de processos encontrados:** {len(df)}")
st.header("Dados Filtrados")
st.dataframe(df)

# Função para exportar PDF
def exportar_pdf(df: pd.DataFrame) -> bytes:
    cols = ['PAE', 'CLIENTE', 'Andamento', 'Status contratual',
            'Vigência Início','Vigência Término','VALOR GLOBAL ATUAL','Setor']
    export_df = df[cols] if set(cols).issubset(df.columns) else df.copy()

    # Formatar datas
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

# Botão de download de PDF
if not df.empty:
    pdf_bytes = exportar_pdf(df)
    st.download_button(
        '📄 Baixar processos filtrados em PDF',
        data=pdf_bytes,
        file_name='processos_filtrados.pdf',
        mime='application/pdf'
    )
