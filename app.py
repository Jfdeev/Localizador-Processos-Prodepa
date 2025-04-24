import streamlit as st 
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io

st.set_page_config(page_title="Localizador de Processos PAE", layout="wide")
st.title("Localizador de Processos PAE")

def load_data() -> pd.DataFrame:
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRY-kZhxw0D2wTEfX9DXzlrTyatD8kiBk1KMFEhUdD_ix-lsWXSMhBIy9HCxaVmhFShAWhwcuxhbqRT/pub?output=csv"
    try: 
        df = pd.read_csv(url)
        df.columns = [col.strip() for col in df.columns]
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {e}")
        return pd.DataFrame()
    
    for date_col in ['Data Vigência Original', 'Vigência Início', 'Vigência Término', 'DATA ULTIMA TRAMITAÇÃO']:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')

    if 'Vencimento em dias' in df.columns:
        df['Vencimento em dias'] = pd.to_numeric(df['Vencimento em dias'], errors='coerce')

    if 'SETOR ATUAL' in df.columns:
        df['Setor'] = df['SETOR ATUAL']
    elif 'Setor' in df.columns:
        df['Setor'] = df['Setor']

    if 'N PAE' in df.columns:
        df['PAE'] = df['N PAE']
    elif 'PAE' in df.columns:
        df['PAE'] = df['PAE']

    return df

# Carrega os dados
data = load_data()

st.sidebar.header("Filtros")
cliente = sorted(str(x) for x in data['CLIENTE'].dropna().unique()) if 'CLIENTE' in data.columns else []

# Inicialização segura do session_state
if "clientes_selecionados" not in st.session_state:
    st.session_state["clientes_selecionados"] = cliente[:1]

# Formulário para controle dos botões de cliente
with st.sidebar.form(key="form_clientes"):
    st.markdown("### Cliente")
    col1, col2 = st.columns([1, 1])
    todos = col1.form_submit_button("✅ Todos")
    nenhum = col2.form_submit_button("❌ Nenhum")
    if todos:
        st.session_state["clientes_selecionados"] = cliente
    if nenhum:
        st.session_state["clientes_selecionados"] = []
    select_cliente = st.multiselect(
        "Cliente",
        options=cliente,
        default=st.session_state["clientes_selecionados"],
        key="clientes_selecionados"
    )

# Filtros adicionais
andamento = sorted(data['Andamento'].dropna().unique()) if 'Andamento' in data.columns else []
selected_andamento = st.sidebar.multiselect("Andamento", andamento, default=andamento)

status = sorted(data['Status contratual'].dropna().unique()) if 'Status contratual' in data.columns else []
selected_status = st.sidebar.multiselect("Status Contratual", status, default=status)

# Busca com autocomplete para processos
st.subheader("Busca por Número do Processo")
search_text = st.text_input("Digite parte do número do processo:")
num_processo = sorted(data['PAE'].dropna().unique()) if 'PAE' in data.columns else []
sugestoes = [str(p) for p in num_processo if search_text in str(p)] if search_text else []
selected_processo = st.selectbox("Selecione o processo:", sugestoes) if sugestoes else None

# Filtragem
df = data.copy()
if selected_processo:
    df = df[df['PAE'].astype(str) == selected_processo]
else:
    if 'CLIENTE' in df.columns:
        df = df[df['CLIENTE'].isin(select_cliente)]
    if 'Andamento' in df.columns:
        df = df[df['Andamento'].isin(selected_andamento)]
    if 'Status contratual' in df.columns:
        df = df[df['Status contratual'].isin(selected_status)]

st.markdown(f"**Total de processos encontrados:** {len(df)}")
st.header("Dados Filtrados")
st.dataframe(df)

# ====== Exportar para PDF ======
def exportar_pdf(df: pd.DataFrame) -> bytes:
    cols_export = ['PAE','CLIENTE','Andamento','Status contratual',
                   'Vigência Início','Vigência Término', 'VALOR GLOBAL ATUAL', 'Setor']
    if not set(cols_export).issubset(df.columns):
        df_export = df.copy()
    else:
        df_export = df[cols_export]

    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Relatório de Processos Filtrados", ln=True, align="C")
    pdf.ln(4)

    pdf.set_font("Arial", size=8)
    epw = pdf.w - 2 * pdf.l_margin
    col_width = epw / len(df_export.columns)
    row_height = pdf.font_size * 1.5

    for header in df_export.columns:
        pdf.cell(col_width, row_height, str(header), border=1, align="C")
    pdf.ln(row_height)

    for row in df_export.itertuples(index=False):
        for item in row:
            text = str(item)
            if len(text) > 20:
                text = text[:17] + "..."
            pdf.cell(col_width, row_height, text, border=1)
        pdf.ln(row_height)

    return pdf.output(dest="S").encode("latin-1")

if not df.empty:
    pdf_bytes = exportar_pdf(df)
    st.download_button(
        label="📄 Baixar processos filtrados em PDF",
        data=pdf_bytes,
        file_name="processos_filtrados.pdf",
        mime="application/pdf",
    )
