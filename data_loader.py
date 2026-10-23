"""
Data loading and processing pipeline for BRI KC TB Simatupang Performance Dashboard.
Handles loading Excel reports, cleaning columns, caching, merging with master,
and computing validated aggregations.
"""

import os
import io
import time
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.join(BASE_DIR, "data", "sample")
UPLOAD_DIR = os.path.join(BASE_DIR, "data", "latest")
CACHE_DIR = os.path.join(BASE_DIR, ".cache")
DEFAULT_SOURCE_DIR = SAMPLE_DIR

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# Known authoritative units mapping
UNIT_METADATA = {
    "443": {"name": "KC Jakarta TB Simatupang", "type": "KC", "type_desc": "Kantor Cabang (Induk)"},
    "1506": {"name": "KCP PHE TOWER", "type": "KCP", "type_desc": "Kantor Cabang Pembantu"},
    "2075": {"name": "KCP RANCHO", "type": "KCP", "type_desc": "Kantor Cabang Pembantu"},
    "1237": {"name": "KK WISMA RAHARJA", "type": "KK", "type_desc": "Kantor Kas"},
    "1410": {"name": "KK LENTENG AGUNG RAYA", "type": "KK", "type_desc": "Kantor Kas"},
    "1425": {"name": "KK MARGASATWA", "type": "KK", "type_desc": "Kantor Kas"},
    "1657": {"name": "KK POLI MEDIA", "type": "KK", "type_desc": "Kantor Kas"},
}

def clean_num(series):
    """Safely convert strings or numbers with formatting into clean float series."""
    if series is None:
        return pd.Series([], dtype=float)
    if pd.api.types.is_numeric_dtype(series):
        return series.fillna(0.0).astype(float)
    s = series.astype(str).str.strip().str.replace(',', '', regex=False)
    return pd.to_numeric(s, errors='coerce').fillna(0.0)

def clean_str(series):
    """Normalize string column: strip, convert None to empty."""
    if series is None:
        return pd.Series([], dtype=str)
    return series.fillna("").astype(str).str.strip()

def format_rupiah(value, format_type="compact"):
    """
    Format numeric values into Indonesian currency strings.
    compact: e.g. Rp588,3 Miliar, Rp1,2 Triliun, Rp45,2 Juta
    full: e.g. Rp 588.259.507.776
    """
    if pd.isna(value) or value is None:
        return "Rp0"
    v = float(value)
    abs_v = abs(v)
    sign = "-" if v < 0 else ""
    
    if format_type == "full":
        formatted = f"{abs_v:,.0f}".replace(",", ".")
        return f"{sign}Rp {formatted}"
        
    if abs_v >= 1e12:
        val_str = f"{abs_v / 1e12:.2f}".replace(".", ",")
        return f"{sign}Rp{val_str} Triliun"
    elif abs_v >= 1e9:
        val_str = f"{abs_v / 1e9:.2f}".replace(".", ",")
        return f"{sign}Rp{val_str} Miliar"
    elif abs_v >= 1e6:
        val_str = f"{abs_v / 1e6:.2f}".replace(".", ",")
        return f"{sign}Rp{val_str} Juta"
    else:
        formatted = f"{abs_v:,.0f}".replace(",", ".")
        return f"{sign}Rp {formatted}"

def get_cache_path(cache_name):
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{cache_name}.parquet")

def save_to_parquet_safe(df, cache_file):
    """Safely convert object columns to string to avoid pyarrow ArrowTypeError on mixed types."""
    try:
        df_clean = df.copy()
        for col in df_clean.select_dtypes(include=['object', 'string']).columns:
            df_clean[col] = df_clean[col].astype(str)
        df_clean.to_parquet(cache_file, index=False)
    except Exception as e:
        # If parquet fails for any reason, continue gracefully without crashing the app
        print(f"Warning: Failed to write parquet cache {cache_file}: {e}")

def resolve_source_file(filename):
    """
    Resolves file priority:
    1. User uploaded / latest file in data/latest/
    2. Local California portfolio directory (if on dev machine)
    3. Packaged sample file in data/sample/ (guaranteed for cloud deployment)
    """
    # 1. Latest upload
    latest_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(latest_path):
        return latest_path
        
    # 2. Local machine workspace path
    local_california = r"D:\[1] Work\[5] BRI\California\Portfolio Cabang"
    if os.path.exists(os.path.join(local_california, filename)):
        return os.path.join(local_california, filename)
        
    # 3. Packaged sample folder (works anywhere in the cloud)
    sample_path = os.path.join(SAMPLE_DIR, filename)
    if os.path.exists(sample_path):
        return sample_path
        
    return None

def save_uploaded_file(uploaded_file, target_filename):
    """Save an uploaded file from Streamlit to data/latest directory and invalidate cache."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, target_filename)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    # Invalidate cached parquet
    clear_cache()
    return file_path

def load_loan_master(source_path_or_buffer=None):
    """Load and normalize Loan Type California master."""
    if source_path_or_buffer is None:
        path = resolve_source_file("Loan Type California.xlsx")
    else:
        path = source_path_or_buffer
        
    df = pd.read_excel(path)
    df['LN_TYPE_CLEAN'] = clean_str(df['LN_TYPE']).str.upper()
    df['DESC_CLEAN'] = clean_str(df['DESCRIPTION']).str.upper()
    df['Business'] = clean_str(df['Business'])
    df_clean = df.drop_duplicates(subset=['LN_TYPE_CLEAN', 'DESC_CLEAN']).copy()
    return df_clean

def load_lending_data(source_path_or_buffer=None, master_df=None):
    """
    Load LW321 lending report, join with loan classification master.
    Only Small and Consumer enter main lending KPIs.
    """
    cache_file = get_cache_path("lending_data")
    is_default = (source_path_or_buffer is None)
    
    if is_default and os.path.exists(cache_file):
        try:
            return pd.read_parquet(cache_file)
        except Exception:
            pass
        
    if source_path_or_buffer is None:
        path = resolve_source_file("LW321 (1).xlsx")
    else:
        path = source_path_or_buffer
        
    df = pd.read_excel(path, skiprows=3)
    df = df.dropna(how='all', axis=1)
    
    # Clean and standardize columns
    df['PERIODE_STR'] = clean_str(df['PERIODE'])
    df['KODE_UKER_STR'] = clean_str(df['KODE_UKER']).str.replace(r'\.0$', '', regex=True)
    df['UKER_NAME'] = clean_str(df['UKER'])
    df['LN_TYPE_CLEAN'] = clean_str(df['LN_TYPE']).str.upper()
    df['DESC_CLEAN'] = clean_str(df['DESCRIPTION']).str.upper()
    df['NOMOR_REKENING_STR'] = clean_str(df['NOMOR_REKENING'])
    df['NAMA_DEBITUR_STR'] = clean_str(df['NAMA_DEBITUR'])
    
    # Financial fields
    df['BALANCE_IDR'] = clean_num(df['BALANCE DALAM IDR'])
    df['PLAFON_IDR'] = clean_num(df['PLAFON DALAM IDR'])
    df['TUNGGAKAN_POKOK_NUM'] = clean_num(df.get('TUNGGAKAN POKOK', pd.Series(0, index=df.index)))
    df['TUNGGAKAN_BUNGA_NUM'] = clean_num(df.get('TUNGGAKAN BUNGA', pd.Series(0, index=df.index)))
    df['RATE_NUM'] = clean_num(df.get('RATE', pd.Series(0, index=df.index)))
    
    # Join with master
    if master_df is None:
        master_df = load_loan_master()
        
    df_merged = pd.merge(
        df,
        master_df[['LN_TYPE_CLEAN', 'DESC_CLEAN', 'Business']],
        on=['LN_TYPE_CLEAN', 'DESC_CLEAN'],
        how='left'
    )
    
    # If unclassified, label as Unidentified
    df_merged['Business'] = df_merged['Business'].fillna("Unidentified")
    
    # Flag main KPI eligibility
    df_merged['IS_MAIN_KPI'] = df_merged['Business'].isin(['Small', 'Consumer'])
    
    # Friendly unit name if empty
    df_merged['UNIT_DISPLAY_NAME'] = df_merged['KODE_UKER_STR'].map(
        lambda k: UNIT_METADATA.get(k, {}).get("name", f"Uker {k}")
    )
    df_merged['UNIT_TYPE'] = df_merged['KODE_UKER_STR'].map(
        lambda k: UNIT_METADATA.get(k, {}).get("type", "Lainnya")
    )
    
    if is_default:
        save_to_parquet_safe(df_merged, cache_file)
        
    return df_merged

def load_giro_data(source_path_or_buffer=None):
    """Load DI321 giro report."""
    cache_file = get_cache_path("giro_data")
    is_default = (source_path_or_buffer is None)
    
    if is_default and os.path.exists(cache_file):
        try:
            return pd.read_parquet(cache_file)
        except Exception:
            pass
        
    if source_path_or_buffer is None:
        path = resolve_source_file("DI321.xlsx")
    else:
        path = source_path_or_buffer
        
    df = pd.read_excel(path, skiprows=3)
    df = df.dropna(how='all', axis=1)
    
    df['PERIODE_STR'] = clean_str(df['PERIODE'])
    df['KODE_UKER_STR'] = clean_str(df['KODE UKER']).str.replace(r'\.0$', '', regex=True)
    df['UKER_NAME'] = clean_str(df['UKER'])
    df['CURR_STR'] = clean_str(df['CURR']).str.upper()
    df['IS_IDR'] = (df['CURR_STR'] == 'IDR')
    df['ACCOUNT_NUMBER_STR'] = clean_str(df['ACCOUNT NUMBER'])
    df['SHORT_NAME_STR'] = clean_str(df['SHORT NAME'])
    df['PRODUCT_CODE_STR'] = clean_str(df['PRODUCT CODE'])
    df['BALANCE_NUM'] = clean_num(df['BALANCE'])
    df['AVRG_BALANCE_NUM'] = clean_num(df.get('AVRG BALANCE', pd.Series(0, index=df.index)))
    
    df['UNIT_DISPLAY_NAME'] = df['KODE_UKER_STR'].map(
        lambda k: UNIT_METADATA.get(k, {}).get("name", df.loc[df['KODE_UKER_STR']==k, 'UKER_NAME'].iloc[0] if len(df.loc[df['KODE_UKER_STR']==k])>0 else f"Uker {k}")
    )
    df['UNIT_TYPE'] = df['KODE_UKER_STR'].map(
        lambda k: UNIT_METADATA.get(k, {}).get("type", "Lainnya")
    )
    
    if is_default:
        save_to_parquet_safe(df, cache_file)
        
    return df

def load_deposito_data(source_path_or_buffer=None):
    """
    Load CI324 deposito report.
    Uses CBAL Base as confirmed converted IDR balance field for FX deposits.
    """
    cache_file = get_cache_path("deposito_data")
    is_default = (source_path_or_buffer is None)
    
    if is_default and os.path.exists(cache_file):
        try:
            return pd.read_parquet(cache_file)
        except Exception:
            pass
        
    if source_path_or_buffer is None:
        path = resolve_source_file("CI324_MULTI_PN_202309.xlsx")
    else:
        path = source_path_or_buffer
        
    df = pd.read_excel(path, skiprows=3)
    df = df.dropna(how='all', axis=1)
    
    df['PERIODE_STR'] = clean_str(df['PERIODE'])
    df['KODE_UKER_STR'] = clean_str(df['KODE UKER']).str.replace(r'\.0$', '', regex=True)
    df['CURR_STR'] = clean_str(df['CUR CODE'])
    df['TYPE_STR'] = clean_str(df['TYPE'])
    df['ACCTNO_STR'] = clean_str(df['ACCTNO'])
    df['SHORT_NAME_STR'] = clean_str(df['SHORT NAME'])
    df['INT_TENOR_DISP_STR'] = clean_str(df['INT TENOR DISP'])
    df['INT_RATE_NUM'] = clean_num(df.get('INT RATE', pd.Series(0, index=df.index)))
    df['RENEW_STR'] = clean_str(df.get('RENEW', pd.Series("", index=df.index)))
    
    # Balances
    df['CBAL_BASE_NUM'] = clean_num(df['CBAL Base'])
    df['PRINCIPAL_NUM'] = clean_num(df['PRINCIPAL AMOUNT'])
    
    df['UNIT_DISPLAY_NAME'] = df['KODE_UKER_STR'].map(
        lambda k: UNIT_METADATA.get(k, {}).get("name", f"Uker {k}")
    )
    df['UNIT_TYPE'] = df['KODE_UKER_STR'].map(
        lambda k: UNIT_METADATA.get(k, {}).get("type", "Lainnya")
    )
    
    if is_default:
        save_to_parquet_safe(df, cache_file)
        
    return df

def load_tabungan_data(source_path_or_buffer=None):
    """
    Load DI319 savings / tabungan report.
    Uses 'Balance dalam IDR' as foreign currency converted balance.
    """
    cache_file = get_cache_path("tabungan_data")
    is_default = (source_path_or_buffer is None)
    
    if is_default and os.path.exists(cache_file):
        try:
            return pd.read_parquet(cache_file)
        except Exception:
            pass
        
    if source_path_or_buffer is None:
        path = resolve_source_file("DI319_MULTI_PN_202309.xlsx")
    else:
        path = source_path_or_buffer
        
    df = pd.read_excel(path, skiprows=5)
    df = df.dropna(how='all', axis=1)
    
    df['PERIODE_STR'] = clean_str(df['periode'])
    df['KODE_UKER_STR'] = clean_str(df['uker code']).str.replace(r'\.0$', '', regex=True)
    df['CURR_STR'] = clean_str(df['curr code'])
    df['ACCOUNT_NUMBER_STR'] = clean_str(df['account number'])
    df['SHORT_NAME_STR'] = clean_str(df['short name'])
    df['PROD_CODE_STR'] = clean_str(df['prod code'])
    
    # Balances
    df['BALANCE_NOMINAL_NUM'] = clean_num(df['balance'])
    if 'Balance dalam IDR' in df.columns:
        df['BALANCE_IDR_NUM'] = clean_num(df['Balance dalam IDR'])
    else:
        df['BALANCE_IDR_NUM'] = df['BALANCE_NOMINAL_NUM']
        
    df['UNIT_DISPLAY_NAME'] = df['KODE_UKER_STR'].map(
        lambda k: UNIT_METADATA.get(k, {}).get("name", f"Uker {k}")
    )
    df['UNIT_TYPE'] = df['KODE_UKER_STR'].map(
        lambda k: UNIT_METADATA.get(k, {}).get("type", "Lainnya")
    )
    
    if is_default:
        save_to_parquet_safe(df, cache_file)
        
    return df

def apply_org_filter(df, filter_choice, uker_col="KODE_UKER_STR"):
    """
    Apply organizational filter to a dataset:
    - 'Konsolidasi': All units belonging to KC Simatupang (443 and subordinates)
    - 'KC Only': KC Jakarta TB Simatupang itself (code '443')
    - 'KCP PHE TOWER': code '1506'
    - 'KCP RANCHO': code '2075'
    """
    if df is None or len(df) == 0:
        return df
        
    if filter_choice == "Konsolidasi":
        return df
    elif filter_choice == "KC Only":
        return df[df[uker_col] == "443"]
    elif "1506" in filter_choice or "PHE" in filter_choice.upper():
        return df[df[uker_col] == "1506"]
    elif "2075" in filter_choice or "RANCHO" in filter_choice.upper():
        return df[df[uker_col] == "2075"]
    else:
        return df[df[uker_col] == filter_choice]

def clear_cache():
    """Clear cached parquet files."""
    if os.path.exists(CACHE_DIR):
        for f in os.listdir(CACHE_DIR):
            if f.endswith(".parquet"):
                try:
                    os.remove(os.path.join(CACHE_DIR, f))
                except Exception:
                    pass
