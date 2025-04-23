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

    if 'VALOR GLOBAL ATUAL' in df.columns:
        cleaned = (
            df['VALOR GLOBAL ATUAL']
            .astype(str)
            .str.replace(r"[R$\. ]", "", regex=True)
            .str.replace(",", ".")
        )
        df['Valor global Atual'] = pd.to_numeric(cleaned, errors='coerce')

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
select_cliente = st.sidebar.multiselect("Cliente", cliente, default=cliente[:1])
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
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=8)

    col_width = pdf.w / (len(df.columns) + 1)
    row_height = pdf.font_size + 1

    # Cabeçalho
    for col in df.columns:
        pdf.cell(col_width, row_height * 1.5, str(col), border=1)
    pdf.ln(row_height * 1.5)

    # Linhas
    for _, row in df.iterrows():
        for item in row:
            pdf.cell(col_width, row_height, str(item), border=1)
        pdf.ln(row_height)

    buffer = io.BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()

if not df.empty:
    pdf_bytes = exportar_pdf(df)
    st.download_button(
        label="📄 Baixar dados filtrados em PDF",
        data=pdf_bytes,
        file_name="processos_filtrados.pdf",
        mime="application/pdf"
    )
