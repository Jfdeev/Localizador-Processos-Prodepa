import streamlit as st 
import pandas as pd
import altair as alt
from datetime import datetime

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

    # Parse de datas
    for date_col in ['Data Vigência Original', 'Vigência Início', 'Vigência Término', 'DATA ULTIMA TRAMITAÇÃO']:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')

    # Conversão de valores monetários
    if 'VALOR GLOBAL ATUAL' in df.columns:
        cleaned = (
            df['VALOR GLOBAL ATUAL']
            .astype(str)
            .str.replace(r"[R$\. ]", "", regex=True)
            .str.replace(",", ".")
        )
        df['Valor global Atual'] = pd.to_numeric(cleaned, errors='coerce')

    # Conversão de vencimento em dias
    if 'Vencimento em dias' in df.columns:
        df['Vencimento em dias'] = pd.to_numeric(df['Vencimento em dias'], errors='coerce')

    # Unifica colunas críticas
    # Setor
    if 'SETOR ATUAL' in df.columns:
        df['Setor'] = df['SETOR ATUAL']
    elif 'Setor' in df.columns:
        df['Setor'] = df['Setor']
    # PAE
    if 'Nº PAE' in df.columns:
        df['PAE'] = df['Nº PAE']
    elif 'PAE' in df.columns:
        df['PAE'] = df['PAE']

    return df

# Carrega os dados
data = load_data()

st.sidebar.header("Filtros")
# Filtros
cliente = sorted(
    str(x) for x in data['CLIENTE'].dropna().unique()
) if 'CLIENTE' in data.columns else []
select_cliente = st.sidebar.multiselect("Cliente", cliente, default=cliente)
andamento = sorted(data['Andamento'].dropna().unique()) if 'Andamento' in data.columns else []
selected_andamento = st.sidebar.multiselect("Andamento", andamento, default=andamento)
status = sorted(data['Status contratual'].dropna().unique()) if 'Status contratual' in data.columns else []
selected_status = st.sidebar.multiselect("Status Contratual", status, default=status)
num_processo = sorted(data['PAE'].dropna().unique()) if 'PAE' in data.columns else []
selected_num_processo = st.text_input("Número do Processo", value="")
if selected_num_processo:
    selected_num_processo = [selected_num_processo]
else:
    selected_num_processo = num_processo


df = data.copy()
if 'CLIENTE' in df.columns:
    df = df[df['CLIENTE'].isin(select_cliente)]
if 'Andamento' in df.columns:
    df = df[df['Andamento'].isin(selected_andamento)]
if 'Status contratual' in df.columns:
    df = df[df['Status contratual'].isin(selected_status)]
if 'PAE' in df.columns:
    df = df[df['PAE'].isin(selected_num_processo)]

st.markdown(f"**Total de processos encontrados:** {len(df)}")

st.header("Dados Filtrados")
st.dataframe(df)



