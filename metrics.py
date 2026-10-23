"""
Metrics and analytics calculations for BRI KC TB Simatupang Performance Dashboard.
Calculates Lending, Funding, and Data Quality KPIs strictly aligned with business definitions.
"""

import pandas as pd
import numpy as np

def compute_lending_kpis(df_lending):
    """
    Compute lending KPIs for the current filtered lending dataset.
    Main KPIs only include Small and Consumer classifications.
    Excluded records (Micro, Medium, Commercial, Unidentified) are segregated.
    """
    if df_lending is None or len(df_lending) == 0:
        return {
            "total_records": 0,
            "main_records": 0,
            "os_small": 0.0,
            "count_small": 0,
            "os_consumer": 0.0,
            "count_consumer": 0,
            "os_combined": 0.0,
            "plafon_combined": 0.0,
            "excluded_records": 0,
            "os_excluded": 0.0,
            "os_unidentified": 0.0,
            "count_unidentified": 0,
            "npl_nominal": 0.0,
            "npl_pct": 0.0,
            "kol_summary": pd.DataFrame(),
            "business_summary": pd.DataFrame(),
            "loan_type_summary": pd.DataFrame(),
            "unit_summary": pd.DataFrame()
        }
        
    total_records = len(df_lending)
    
    # Filter main Small & Consumer
    df_small = df_lending[df_lending['Business'] == 'Small']
    df_cons = df_lending[df_lending['Business'] == 'Consumer']
    df_main = df_lending[df_lending['IS_MAIN_KPI']]
    df_excluded = df_lending[~df_lending['IS_MAIN_KPI']]
    df_unid = df_lending[df_lending['Business'] == 'Unidentified']
    
    os_small = float(df_small['BALANCE_IDR'].sum())
    count_small = len(df_small)
    
    os_consumer = float(df_cons['BALANCE_IDR'].sum())
    count_consumer = len(df_cons)
    
    os_combined = float(df_main['BALANCE_IDR'].sum())
    plafon_combined = float(df_main['PLAFON_IDR'].sum())
    main_records = len(df_main)
    
    os_excluded = float(df_excluded['BALANCE_IDR'].sum())
    excluded_records = len(df_excluded)
    
    os_unidentified = float(df_unid['BALANCE_IDR'].sum())
    count_unidentified = len(df_unid)
    
    # Kolektibilitas on Main KPI portfolio
    # In LW321: KOL_ADK or KOLEKTIBILITAS LANCAR/DPK/KURANG LANCAR/DIRAGUKAN/MACET
    # Check KOL_ADK if available
    kol_summary = pd.DataFrame()
    npl_nominal = 0.0
    npl_pct = 0.0
    
    if 'KOL_ADK' in df_main.columns:
        kol_series = df_main['KOL_ADK'].fillna(1).astype(int)
        df_main_copy = df_main.copy()
        df_main_copy['KOL_LABEL'] = kol_series.map({
            1: "1 - Lancar",
            2: "2 - DPK (Dalam Perhatian Khusus)",
            3: "3 - Kurang Lancar (NPL)",
            4: "4 - Diragukan (NPL)",
            5: "5 - Macet (NPL)"
        }).fillna("Lainnya")
        
        kol_summary = df_main_copy.groupby('KOL_LABEL')['BALANCE_IDR'].agg(['count', 'sum']).reset_index()
        kol_summary.columns = ['Kolektibilitas', 'Jumlah Rekening', 'Baki Debet (Rp)']
        
        npl_records = df_main_copy[kol_series.isin([3, 4, 5])]
        npl_nominal = float(npl_records['BALANCE_IDR'].sum())
        npl_pct = (npl_nominal / os_combined * 100) if os_combined > 0 else 0.0
        
    # Breakdown by Business
    business_summary = df_lending.groupby('Business')['BALANCE_IDR'].agg(['count', 'sum']).reset_index()
    business_summary.columns = ['Klasifikasi Bisnis', 'Jumlah Rekening', 'Baki Debet (Rp)']
    business_summary['Status'] = business_summary['Klasifikasi Bisnis'].apply(
        lambda b: "Main KPI" if b in ['Small', 'Consumer'] else "Dikecualikan (Data Quality)"
    )
    
    # Breakdown by Loan Type (Main KPIs)
    if len(df_main) > 0:
        loan_type_summary = df_main.groupby(['LN_TYPE_CLEAN', 'DESC_CLEAN', 'Business'])['BALANCE_IDR'].agg(
            ['count', 'sum']
        ).reset_index()
        loan_type_summary.columns = ['Loan Type', 'Deskripsi Produk', 'Segmen', 'Jumlah Rekening', 'Baki Debet (Rp)']
        loan_type_summary = loan_type_summary.sort_values(by='Baki Debet (Rp)', ascending=False)
    else:
        loan_type_summary = pd.DataFrame()
        
    # Breakdown by Unit (Main KPIs)
    if len(df_main) > 0:
        unit_summary = df_main.groupby(['KODE_UKER_STR', 'UNIT_DISPLAY_NAME', 'UNIT_TYPE'])['BALANCE_IDR'].agg(
            ['count', 'sum']
        ).reset_index()
        unit_summary.columns = ['Kode Uker', 'Nama Unit Kerja', 'Tipe Unit', 'Jumlah Rekening', 'Baki Debet (Rp)']
        unit_summary = unit_summary.sort_values(by='Baki Debet (Rp)', ascending=False)
    else:
        unit_summary = pd.DataFrame()
        
    return {
        "total_records": total_records,
        "main_records": main_records,
        "os_small": os_small,
        "count_small": count_small,
        "os_consumer": os_consumer,
        "count_consumer": count_consumer,
        "os_combined": os_combined,
        "plafon_combined": plafon_combined,
        "excluded_records": excluded_records,
        "os_excluded": os_excluded,
        "os_unidentified": os_unidentified,
        "count_unidentified": count_unidentified,
        "npl_nominal": npl_nominal,
        "npl_pct": npl_pct,
        "kol_summary": kol_summary,
        "business_summary": business_summary,
        "loan_type_summary": loan_type_summary,
        "unit_summary": unit_summary
    }

def compute_funding_kpis(df_tab, df_giro, df_dep):
    """
    Compute funding KPIs for the filtered tabungan, giro, and deposito datasets.
    """
    # 1. Tabungan
    tab_balance = float(df_tab['BALANCE_IDR_NUM'].sum()) if df_tab is not None and len(df_tab) > 0 else 0.0
    tab_count = len(df_tab) if df_tab is not None else 0
    
    # 2. Giro
    giro_balance = float(df_giro['BALANCE_NUM'].sum()) if df_giro is not None and len(df_giro) > 0 else 0.0
    giro_count = len(df_giro) if df_giro is not None else 0
    
    # 3. Deposito
    dep_balance = float(df_dep['CBAL_BASE_NUM'].sum()) if df_dep is not None and len(df_dep) > 0 else 0.0
    dep_principal = float(df_dep['PRINCIPAL_NUM'].sum()) if df_dep is not None and len(df_dep) > 0 else 0.0
    dep_count = len(df_dep) if df_dep is not None else 0
    
    # Total Funding (Simpanan / DPK)
    total_funding = tab_balance + giro_balance + dep_balance
    total_accounts = tab_count + giro_count + dep_count
    
    # CASA (Current Account & Savings Account)
    casa_balance = tab_balance + giro_balance
    casa_pct = (casa_balance / total_funding * 100) if total_funding > 0 else 0.0
    
    # Composition percentages
    pct_tab = (tab_balance / total_funding * 100) if total_funding > 0 else 0.0
    pct_giro = (giro_balance / total_funding * 100) if total_funding > 0 else 0.0
    pct_dep = (dep_balance / total_funding * 100) if total_funding > 0 else 0.0
    
    # Product breakdowns
    # Deposito by Tenor
    dep_tenor_summary = pd.DataFrame()
    if df_dep is not None and len(df_dep) > 0:
        dep_tenor_summary = df_dep.groupby('INT_TENOR_DISP_STR')['CBAL_BASE_NUM'].agg(
            ['count', 'sum']
        ).reset_index()
        dep_tenor_summary.columns = ['Tenor', 'Jumlah Bilyet', 'Nominal CBAL Base (Rp)']
        dep_tenor_summary = dep_tenor_summary.sort_values(by='Nominal CBAL Base (Rp)', ascending=False)
        
    # Giro by Product Code
    giro_prod_summary = pd.DataFrame()
    if df_giro is not None and len(df_giro) > 0:
        giro_prod_summary = df_giro.groupby('PRODUCT_CODE_STR')['BALANCE_NUM'].agg(
            ['count', 'sum']
        ).reset_index()
        giro_prod_summary.columns = ['Kode Produk Giro', 'Jumlah Rekening', 'Saldo (Rp)']
        giro_prod_summary = giro_prod_summary.sort_values(by='Saldo (Rp)', ascending=False)
        
    # Tabungan by Product Code (Top 10)
    tab_prod_summary = pd.DataFrame()
    if df_tab is not None and len(df_tab) > 0:
        tab_prod_summary = df_tab.groupby('PROD_CODE_STR')['BALANCE_IDR_NUM'].agg(
            ['count', 'sum']
        ).reset_index()
        tab_prod_summary.columns = ['Kode Produk Tabungan', 'Jumlah Rekening', 'Saldo (Rp)']
        tab_prod_summary = tab_prod_summary.sort_values(by='Saldo (Rp)', ascending=False)
        
    return {
        "tab_balance": tab_balance,
        "tab_count": tab_count,
        "giro_balance": giro_balance,
        "giro_count": giro_count,
        "dep_balance": dep_balance,
        "dep_principal": dep_principal,
        "dep_count": dep_count,
        "total_funding": total_funding,
        "total_accounts": total_accounts,
        "casa_balance": casa_balance,
        "casa_pct": casa_pct,
        "pct_tab": pct_tab,
        "pct_giro": pct_giro,
        "pct_dep": pct_dep,
        "dep_tenor_summary": dep_tenor_summary,
        "giro_prod_summary": giro_prod_summary,
        "tab_prod_summary": tab_prod_summary
    }

def compute_unit_breakdown_matrix(df_lending, df_tab, df_giro, df_dep):
    """
    Build a consolidated matrix comparing all units across all products.
    """
    all_units = set()
    for df, col in [(df_lending, 'KODE_UKER_STR'), (df_tab, 'KODE_UKER_STR'),
                    (df_giro, 'KODE_UKER_STR'), (df_dep, 'KODE_UKER_STR')]:
        if df is not None and len(df) > 0 and col in df.columns:
            all_units.update(df[col].dropna().unique())
            
    rows = []
    from data_loader import UNIT_METADATA
    
    for u in sorted(all_units):
        meta = UNIT_METADATA.get(u, {"name": f"Uker {u}", "type": "Lainnya"})
        
        # Lending Small+Consumer
        l_sub = df_lending[(df_lending['KODE_UKER_STR'] == u) & (df_lending['IS_MAIN_KPI'])] if df_lending is not None else None
        l_os = float(l_sub['BALANCE_IDR'].sum()) if l_sub is not None and len(l_sub) > 0 else 0.0
        l_cnt = len(l_sub) if l_sub is not None else 0
        
        # Tabungan
        t_sub = df_tab[df_tab['KODE_UKER_STR'] == u] if df_tab is not None else None
        t_bal = float(t_sub['BALANCE_IDR_NUM'].sum()) if t_sub is not None and len(t_sub) > 0 else 0.0
        t_cnt = len(t_sub) if t_sub is not None else 0
        
        # Giro
        g_sub = df_giro[df_giro['KODE_UKER_STR'] == u] if df_giro is not None else None
        g_bal = float(g_sub['BALANCE_NUM'].sum()) if g_sub is not None and len(g_sub) > 0 else 0.0
        g_cnt = len(g_sub) if g_sub is not None else 0
        
        # Deposito
        d_sub = df_dep[df_dep['KODE_UKER_STR'] == u] if df_dep is not None else None
        d_bal = float(d_sub['CBAL_BASE_NUM'].sum()) if d_sub is not None and len(d_sub) > 0 else 0.0
        d_cnt = len(d_sub) if d_sub is not None else 0
        
        tot_dpk = t_bal + g_bal + d_bal
        
        rows.append({
            "Kode Uker": u,
            "Nama Unit Kerja": meta['name'],
            "Tipe": meta['type'],
            "Pinjaman (Small+Cons) Rp": l_os,
            "Rek Pinjaman": l_cnt,
            "Tabungan Rp": t_bal,
            "Giro Rp": g_bal,
            "Deposito Rp": d_bal,
            "Total Simpanan (DPK) Rp": tot_dpk,
            "Total Rek Simpanan": t_cnt + g_cnt + d_cnt
        })
        
    df_matrix = pd.DataFrame(rows)
    return df_matrix
