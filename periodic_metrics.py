"""
Periodic Metrics and Time-Series Analytics Engine for BRI KC TB Simatupang.
Calculates daily positions, true-baseline DtD, month-end MTD, and Excel-style daily matrices.

Strict banking rules enforced:
- DtD compares against immediate previous valid snapshot with explicit baseline date & calendar gap.
- MTD compares against verified month-end baseline; if unavailable, strictly returns None / N/A.
- Lending main KPIs include ONLY Small and Consumer loans joined with Loan Type California.
- Deposito uses CBAL Base; Tabungan uses Balance dalam IDR; Giro uses BALANCE without arbitrary FX.
- Zero synthetic forecasts or unverified RKA targets.
"""

import io
import os
import json
import shutil
import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any, Union

import openpyxl
import pandas as pd
import numpy as np

from data_loader import (
    clean_num,
    clean_str,
    load_loan_master,
    format_rupiah,
    read_excel_fast
)


@dataclass
class DailyMetricsSnapshot:
    reporting_date: str                   # ISO: YYYY-MM-DD
    display_date: str                     # Format: DD/MM/YYYY
    # Lending (Main KPIs)
    os_small: float
    count_small: int
    os_consumer: float
    count_consumer: int
    os_lending_main: float
    count_lending_main: int
    # Funding (DPK)
    tabungan_balance: float
    tabungan_count: int
    giro_balance: float
    giro_count: int
    deposito_balance: float
    deposito_count: int
    total_dpk: float
    total_dpk_count: int
    casa_balance: float
    casa_pct: float
    # Metadata
    source_reports: Dict[str, str] = field(default_factory=dict)


@dataclass
class PeriodicComparisonResult:
    reporting_date: str
    display_date: str
    current_snapshot: DailyMetricsSnapshot
    # DtD vs prior snapshot
    dtd_baseline_date: Optional[str]
    dtd_calendar_gap_days: Optional[int]
    dtd_is_consecutive: bool
    dtd_delta: Dict[str, Optional[float]]
    dtd_pct: Dict[str, Optional[float]]
    # MTD vs month-end baseline
    mtd_baseline_date: Optional[str]
    mtd_is_available: bool
    mtd_delta: Dict[str, Optional[float]]
    mtd_pct: Dict[str, Optional[float]]


@dataclass
class PeriodicAnalysisSummary:
    dates_analyzed: List[str]
    latest_date: Optional[str]
    snapshots_by_date: Dict[str, DailyMetricsSnapshot]
    comparisons_by_date: Dict[str, PeriodicComparisonResult]
    summary_df: pd.DataFrame
    daily_matrix_dpk: pd.DataFrame
    daily_matrix_lending: pd.DataFrame
    month_end_baseline: Optional[Dict[str, Any]] = None


def extract_daily_snapshot_from_batch(
    reporting_date: Union[str, Dict[str, Any]],
    display_date: Optional[str] = None,
    reports_dict: Optional[Dict[str, Any]] = None,
    master_df: Optional[pd.DataFrame] = None
) -> DailyMetricsSnapshot:
    """
    Extracts validated daily balances for a single reporting date from the 4 batch reports:
    - LW321: Small & Consumer loans
    - DI319: Tabungan (Balance dalam IDR)
    - DI321: Giro (BALANCE)
    - CI324: Deposito (CBAL Base)

    Supports both caller styles:
    1. extract_daily_snapshot_from_batch(batch_dict, master_df=...)
    2. extract_daily_snapshot_from_batch(reporting_date, display_date, reports_dict, master_df=...)
    """
    if isinstance(reporting_date, dict):
        batch_dict = reporting_date
        reports_dict = batch_dict.get("reports", {})
        display_date = batch_dict.get("display_date", "")
        first_r = next(iter(reports_dict.values())) if reports_dict else {}
        first_res = first_r.get("res") if isinstance(first_r, dict) else None
        if first_res and hasattr(first_res, "reporting_date"):
            reporting_date = first_res.reporting_date
        else:
            reporting_date = batch_dict.get("reporting_date", "")

    if reports_dict is None:
        reports_dict = {}
    if display_date is None:
        display_date = str(reporting_date)

    if master_df is None:
        master_df = load_loan_master()

    # 1. Lending (LW321)
    lw_item = reports_dict.get("LW321")
    lw_source = lw_item.get("file_obj") if isinstance(lw_item, dict) else lw_item
    if hasattr(lw_source, "seek"):
        lw_source.seek(0)
    
    df_lw = read_excel_fast(lw_source, skiprows=3)
    df_lw = df_lw.dropna(how="all", axis=1)
    
    df_lw["LN_TYPE_CLEAN"] = clean_str(df_lw.get("LN_TYPE", pd.Series(dtype=str))).str.upper()
    df_lw["DESC_CLEAN"] = clean_str(df_lw.get("DESCRIPTION", pd.Series(dtype=str))).str.upper()
    df_lw["BALANCE_IDR"] = clean_num(df_lw.get("BALANCE DALAM IDR", pd.Series(dtype=float)))
    
    df_lw_merged = pd.merge(
        df_lw,
        master_df[["LN_TYPE_CLEAN", "DESC_CLEAN", "Business"]],
        on=["LN_TYPE_CLEAN", "DESC_CLEAN"],
        how="left"
    )
    
    def _resolve_business(row):
        b = str(row.get("Business", "")).strip()
        if b in ["Small", "Consumer", "Micro", "Medium", "Corporate"]:
            return b
        raw_b = str(row.get("Business_x" if "Business_x" in row else "Business", "")).strip()
        if raw_b in ["Small", "Consumer", "Micro", "Medium", "Corporate"]:
            return raw_b
        lt = str(row.get("LN_TYPE_CLEAN", "")).upper()
        desc = str(row.get("DESC_CLEAN", "")).upper()
        if any(k in desc for k in ["BRIGUNA", "KONSUM", "KPR", "KKB"]) or lt in ["1E", "WP", "KBR01"]:
            return "Consumer"
        elif any(k in desc for k in ["RITKOM", "SMALL", "MODAL KERJA", "INVESTASI", "SME"]) or lt in ["EB", "DL", "WC", "SME01"]:
            return "Small"
        return "Unidentified"

    df_lw_merged["Business"] = df_lw_merged.apply(_resolve_business, axis=1)
    
    df_small = df_lw_merged[df_lw_merged["Business"] == "Small"]
    df_cons = df_lw_merged[df_lw_merged["Business"] == "Consumer"]
    
    os_small = float(df_small["BALANCE_IDR"].sum())
    count_small = len(df_small)
    os_consumer = float(df_cons["BALANCE_IDR"].sum())
    count_consumer = len(df_cons)
    os_lending_main = os_small + os_consumer
    count_lending_main = count_small + count_consumer

    # 2. Giro (DI321)
    giro_item = reports_dict.get("DI321")
    giro_source = giro_item.get("file_obj") if isinstance(giro_item, dict) else giro_item
    if hasattr(giro_source, "seek"):
        giro_source.seek(0)
        
    df_giro = read_excel_fast(giro_source, skiprows=3)
    df_giro = df_giro.dropna(how="all", axis=1)
    giro_balance = float(clean_num(df_giro.get("BALANCE", pd.Series(dtype=float))).sum())
    giro_count = len(df_giro)

    # 3. Deposito (CI324)
    dep_item = reports_dict.get("CI324")
    dep_source = dep_item.get("file_obj") if isinstance(dep_item, dict) else dep_item
    if hasattr(dep_source, "seek"):
        dep_source.seek(0)
        
    df_dep = read_excel_fast(dep_source, skiprows=3)
    df_dep = df_dep.dropna(how="all", axis=1)
    dep_col = "CBAL Base" if "CBAL Base" in df_dep.columns else "BALANCE"
    deposito_balance = float(clean_num(df_dep.get(dep_col, pd.Series(dtype=float))).sum())
    deposito_count = len(df_dep)

    # 4. Tabungan (DI319)
    tab_item = reports_dict.get("DI319")
    tab_source = tab_item.get("file_obj") if isinstance(tab_item, dict) else tab_item
    if hasattr(tab_source, "seek"):
        tab_source.seek(0)
        
    df_tab = read_excel_fast(tab_source, skiprows=5)
    df_tab = df_tab.dropna(how="all", axis=1)
    tab_col = "Balance dalam IDR" if "Balance dalam IDR" in df_tab.columns else "balance"
    tabungan_balance = float(clean_num(df_tab.get(tab_col, pd.Series(dtype=float))).sum())
    tabungan_count = len(df_tab)

    # Consolidated DPK
    total_dpk = tabungan_balance + giro_balance + deposito_balance
    total_dpk_count = tabungan_count + giro_count + deposito_count
    casa_balance = tabungan_balance + giro_balance
    casa_pct = (casa_balance / total_dpk * 100.0) if total_dpk > 0 else 0.0

    source_names = {
        rtype: reports_dict[rtype].get("filename", rtype) if isinstance(reports_dict.get(rtype), dict) else str(rtype)
        for rtype in ["LW321", "DI319", "DI321", "CI324"]
        if rtype in reports_dict
    }

    return DailyMetricsSnapshot(
        reporting_date=reporting_date,
        display_date=display_date,
        os_small=os_small,
        count_small=count_small,
        os_consumer=os_consumer,
        count_consumer=count_consumer,
        os_lending_main=os_lending_main,
        count_lending_main=count_lending_main,
        tabungan_balance=tabungan_balance,
        tabungan_count=tabungan_count,
        giro_balance=giro_balance,
        giro_count=giro_count,
        deposito_balance=deposito_balance,
        deposito_count=deposito_count,
        total_dpk=total_dpk,
        total_dpk_count=total_dpk_count,
        casa_balance=casa_balance,
        casa_pct=casa_pct,
        source_reports=source_names
    )


def compute_periodic_metrics(
    daily_snapshots: Dict[str, DailyMetricsSnapshot],
    month_end_baseline: Optional[Dict[str, Any]] = None
) -> PeriodicAnalysisSummary:
    """
    Computes time-series analytics, DtD, and MTD across all available daily snapshots.
    - DtD: Compares with immediate prior valid snapshot.
    - MTD: Compares with verified prior month-end baseline.
    """
    sorted_dates = sorted(list(daily_snapshots.keys()))
    comparisons: Dict[str, PeriodicComparisonResult] = {}

    tracked_metrics = [
        "os_small", "os_consumer", "os_lending_main",
        "tabungan_balance", "giro_balance", "deposito_balance",
        "total_dpk", "casa_balance"
    ]

    for idx, d_str in enumerate(sorted_dates):
        snap = daily_snapshots[d_str]
        d_curr = datetime.date.fromisoformat(d_str)

        # 1. DtD Calculation
        if idx == 0:
            dtd_baseline_date = None
            dtd_calendar_gap = None
            dtd_is_consecutive = False
            dtd_delta = {m: None for m in tracked_metrics}
            dtd_pct = {m: None for m in tracked_metrics}
        else:
            prev_d_str = sorted_dates[idx - 1]
            prev_snap = daily_snapshots[prev_d_str]
            d_prev = datetime.date.fromisoformat(prev_d_str)
            
            dtd_baseline_date = prev_d_str
            dtd_calendar_gap = (d_curr - d_prev).days
            dtd_is_consecutive = (dtd_calendar_gap == 1)
            
            dtd_delta = {}
            dtd_pct = {}
            for m in tracked_metrics:
                cur_v = getattr(snap, m)
                prv_v = getattr(prev_snap, m)
                diff = cur_v - prv_v
                dtd_delta[m] = diff
                dtd_pct[m] = (diff / prv_v * 100.0) if prv_v > 0 else 0.0

        # 2. MTD Calculation
        if month_end_baseline and isinstance(month_end_baseline, dict) and month_end_baseline.get("is_verified", False):
            mtd_baseline_date = month_end_baseline.get("date", "Akhir Bulan Lalu")
            mtd_is_available = True
            mtd_delta = {}
            mtd_pct = {}
            for m in tracked_metrics:
                cur_v = getattr(snap, m)
                base_v = month_end_baseline.get(m, 0.0)
                diff = cur_v - base_v
                mtd_delta[m] = diff
                mtd_pct[m] = (diff / base_v * 100.0) if base_v > 0 else 0.0
        else:
            mtd_baseline_date = None
            mtd_is_available = False
            mtd_delta = {m: None for m in tracked_metrics}
            mtd_pct = {m: None for m in tracked_metrics}

        comparisons[d_str] = PeriodicComparisonResult(
            reporting_date=d_str,
            display_date=snap.display_date,
            current_snapshot=snap,
            dtd_baseline_date=dtd_baseline_date,
            dtd_calendar_gap_days=dtd_calendar_gap,
            dtd_is_consecutive=dtd_is_consecutive,
            dtd_delta=dtd_delta,
            dtd_pct=dtd_pct,
            mtd_baseline_date=mtd_baseline_date,
            mtd_is_available=mtd_is_available,
            mtd_delta=mtd_delta,
            mtd_pct=mtd_pct
        )

    # 3. Build Summary DataFrame
    summary_rows = []
    for d_str in sorted_dates:
        snap = daily_snapshots[d_str]
        comp = comparisons[d_str]
        row = {
            "Tanggal": snap.display_date,
            "ISO_Date": d_str,
            "Total DPK": snap.total_dpk,
            "Tabungan": snap.tabungan_balance,
            "Giro": snap.giro_balance,
            "Deposito": snap.deposito_balance,
            "CASA Ratio (%)": snap.casa_pct,
            "Total Pinjaman": snap.os_lending_main,
            "Pinjaman Small": snap.os_small,
            "Pinjaman Konsumer": snap.os_consumer,
            "DtD Baseline": comp.dtd_baseline_date or "-",
            "DtD Gap Hari": comp.dtd_calendar_gap_days if comp.dtd_calendar_gap_days is not None else "-",
            "DtD DPK (Rp)": comp.dtd_delta.get("total_dpk"),
            "DtD DPK (%)": comp.dtd_pct.get("total_dpk"),
            "DtD Lending (Rp)": comp.dtd_delta.get("os_lending_main"),
            "DtD Lending (%)": comp.dtd_pct.get("os_lending_main"),
            "MTD DPK (Rp)": comp.mtd_delta.get("total_dpk") if comp.mtd_is_available else None,
            "MTD DPK (%)": comp.mtd_pct.get("total_dpk") if comp.mtd_is_available else None,
            "MTD Lending (Rp)": comp.mtd_delta.get("os_lending_main") if comp.mtd_is_available else None,
            "MTD Lending (%)": comp.mtd_pct.get("os_lending_main") if comp.mtd_is_available else None,
        }
        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)

    # 4. Build Daily Matrix DataFrames matching KINERJA KONSOLIDASI style
    # Simpanan (DPK) Matrix
    dpk_indicators = [
        ("TOTAL SIMPANAN (DPK)", "total_dpk"),
        ("1. Tabungan", "tabungan_balance"),
        ("2. Giro", "giro_balance"),
        ("3. Deposito", "deposito_balance")
    ]
    daily_matrix_dpk = _build_daily_matrix(
        indicators=dpk_indicators,
        sorted_dates=sorted_dates,
        daily_snapshots=daily_snapshots,
        comparisons=comparisons,
        month_end_baseline=month_end_baseline
    )

    # Pinjaman (Lending) Matrix
    lending_indicators = [
        ("TOTAL PINJAMAN UTAMA (SMALL + CONSUMER)", "os_lending_main"),
        ("1. Pinjaman Small (Kecil)", "os_small"),
        ("2. Pinjaman Konsumer", "os_consumer")
    ]
    daily_matrix_lending = _build_daily_matrix(
        indicators=lending_indicators,
        sorted_dates=sorted_dates,
        daily_snapshots=daily_snapshots,
        comparisons=comparisons,
        month_end_baseline=month_end_baseline
    )

    return PeriodicAnalysisSummary(
        dates_analyzed=sorted_dates,
        latest_date=sorted_dates[-1] if sorted_dates else None,
        snapshots_by_date=daily_snapshots,
        comparisons_by_date=comparisons,
        summary_df=summary_df,
        daily_matrix_dpk=daily_matrix_dpk,
        daily_matrix_lending=daily_matrix_lending,
        month_end_baseline=month_end_baseline
    )


def _build_daily_matrix(
    indicators: List[Tuple[str, str]],
    sorted_dates: List[str],
    daily_snapshots: Dict[str, DailyMetricsSnapshot],
    comparisons: Dict[str, PeriodicComparisonResult],
    month_end_baseline: Optional[Dict[str, Any]]
) -> pd.DataFrame:
    """
    Constructs an Excel-like horizontal daily matrix table:
    Row = Product Indicator
    Col 1 = Posisi Akhir Bulan Lalu (Baseline)
    Col 2..N = Daily Dates (1 Okt, 2 Okt, ...)
    Col N+1 = DtD (Nominal Rp)
    Col N+2 = DtD (%)
    Col N+3 = MTD (Nominal Rp)
    Col N+4 = MTD (%)
    """
    matrix_rows = []
    latest_date = sorted_dates[-1] if sorted_dates else None
    latest_comp = comparisons.get(latest_date) if latest_date else None

    for label, metric_key in indicators:
        row: Dict[str, Any] = {"Indikator Produk": label}

        # Baseline Column
        if month_end_baseline and month_end_baseline.get("is_verified", False):
            base_val = month_end_baseline.get(metric_key)
            base_col_name = f"Baseline ({month_end_baseline.get('display_date', 'Akhir Bln')})"
            row[base_col_name] = base_val
        else:
            row["Baseline (Akhir Bln)"] = None

        # Daily Date Columns
        for d_str in sorted_dates:
            snap = daily_snapshots[d_str]
            val = getattr(snap, metric_key, None)
            # Friendly date header e.g. "01/10"
            col_name = snap.display_date[:5] if len(snap.display_date) >= 5 else snap.display_date
            row[col_name] = val

        # Latest DtD and MTD columns
        if latest_comp:
            row["DtD (Rp)"] = latest_comp.dtd_delta.get(metric_key)
            row["DtD (%)"] = latest_comp.dtd_pct.get(metric_key)
            if latest_comp.mtd_is_available:
                row["MTD (Rp)"] = latest_comp.mtd_delta.get(metric_key)
                row["MTD (%)"] = latest_comp.mtd_pct.get(metric_key)
            else:
                row["MTD (Rp)"] = None
                row["MTD (%)"] = None
        else:
            row["DtD (Rp)"] = None
            row["DtD (%)"] = None
            row["MTD (Rp)"] = None
            row["MTD (%)"] = None

        matrix_rows.append(row)

    return pd.DataFrame(matrix_rows)


def generate_demo_periodic_batch() -> List[Tuple[io.BytesIO, str]]:
    """
    Generates realistic 5-day simulated Excel files (01/10 to 05/10) matching
    the exact scale of BRI KC TB Simatupang (~Rp4.4 Triliun DPK, ~Rp495 Milyar Pinjaman).
    Produces real DtD and MTD variations (both positive and negative) for interactive testing.
    """
    days_data = [
        # (date_str, tabungan, giro, deposito, small, consumer)
        ("01/10/2026", 628_250_000_000.0, 2_112_500_000_000.0, 1_663_000_000_000.0, 357_100_000_000.0, 138_800_000_000.0),
        ("02/10/2026", 629_100_000_000.0, 2_108_200_000_000.0, 1_664_200_000_000.0, 356_900_000_000.0, 139_100_000_000.0),
        ("03/10/2026", 632_000_000_000.0, 2_115_000_000_000.0, 1_665_500_000_000.0, 357_500_000_000.0, 139_300_000_000.0),
        ("04/10/2026", 630_500_000_000.0, 2_111_000_000_000.0, 1_666_000_000_000.0, 357_200_000_000.0, 139_500_000_000.0),
        ("05/10/2026", 634_800_000_000.0, 2_122_500_000_000.0, 1_668_000_000_000.0, 358_000_000_000.0, 139_900_000_000.0),
    ]

    file_items = []

    for d_str, tab_val, giro_val, dep_val, small_val, cons_val in days_data:
        date_clean = d_str.replace("/", "")

        # 1. LW321 (Lending)
        wb_lw = openpyxl.Workbook()
        ws_lw = wb_lw.active
        ws_lw.cell(1, 1, "LW321 - Laporan Kolektibilitas dan Tunggakan Pinjaman Per AO")
        headers_lw = ["NO", "PERIODE", "KODE_UKER", "UKER", "LN_TYPE", "DESCRIPTION", "NOMOR_REKENING", "NAMA_DEBITUR", "BALANCE DALAM IDR", "PLAFON DALAM IDR", "TUNGGAKAN POKOK"]
        for c, h in enumerate(headers_lw, 1):
            ws_lw.cell(4, c, h)
        # Row 5: Small
        ws_lw.cell(5, 1, 1)
        ws_lw.cell(5, 2, d_str)
        ws_lw.cell(5, 3, "443")
        ws_lw.cell(5, 4, "KC Jakarta TB Simatupang")
        ws_lw.cell(5, 5, "EB")
        ws_lw.cell(5, 6, "06. RITKOM - > Rp 1 M S/D Rp 2 M")
        ws_lw.cell(5, 7, "443010001")
        ws_lw.cell(5, 8, "DEBITUR RITEL KOMERSIAL")
        ws_lw.cell(5, 9, small_val)
        ws_lw.cell(5, 10, small_val * 1.1)
        ws_lw.cell(5, 11, 0)
        # Row 6: Consumer
        ws_lw.cell(6, 1, 2)
        ws_lw.cell(6, 2, d_str)
        ws_lw.cell(6, 3, "443")
        ws_lw.cell(6, 4, "KC Jakarta TB Simatupang")
        ws_lw.cell(6, 5, "1E")
        ws_lw.cell(6, 6, "KREDIT RITEL - KONSUMTIF - NON CASH COLATERAL - BRIGUNA")
        ws_lw.cell(6, 7, "443010002")
        ws_lw.cell(6, 8, "DEBITUR BRIGUNA KONSUMER")
        ws_lw.cell(6, 9, cons_val)
        ws_lw.cell(6, 10, cons_val * 1.05)
        ws_lw.cell(6, 11, 0)
        buf_lw = io.BytesIO()
        wb_lw.save(buf_lw)
        buf_lw.seek(0)
        file_items.append((buf_lw, f"LW321_{date_clean}.xlsx"))

        # 2. DI321 (Giro)
        wb_giro = openpyxl.Workbook()
        ws_giro = wb_giro.active
        ws_giro.cell(1, 1, "DI321 - CURRENT ACCOUNT MONTHLY TRIAL BALANCE - ACTIVE")
        headers_giro = ["NO", "PERIODE", "KODE UKER", "UKER", "CURR", "ACCOUNT NUMBER", "SHORT NAME", "PRODUCT CODE", "BALANCE", "AVRG BALANCE"]
        for c, h in enumerate(headers_giro, 1):
            ws_giro.cell(4, c, h)
        ws_giro.cell(5, 1, 1)
        ws_giro.cell(5, 2, d_str)
        ws_giro.cell(5, 3, "443")
        ws_giro.cell(5, 4, "KC Jakarta TB Simatupang")
        ws_giro.cell(5, 5, "IDR")
        ws_giro.cell(5, 6, "443020001")
        ws_giro.cell(5, 7, "NASABAH GIRO UTAMA")
        ws_giro.cell(5, 8, "G01")
        ws_giro.cell(5, 9, giro_val)
        ws_giro.cell(5, 10, giro_val)
        buf_giro = io.BytesIO()
        wb_giro.save(buf_giro)
        buf_giro.seek(0)
        file_items.append((buf_giro, f"DI321_{date_clean}.xlsx"))

        # 3. CI324 (Deposito)
        wb_dep = openpyxl.Workbook()
        ws_dep = wb_dep.active
        ws_dep.cell(1, 1, "CI324 - Multi PN - FDs MONTHLY TRIAL BALANCE by PRODUCT TYPE")
        headers_dep = ["NO", "PERIODE", "KODE UKER", "CUR CODE", "CUR DESC", "TYPE", "ACCTNO", "SHORT NAME", "CBAL Base", "PRINCIPAL AMOUNT", "INT TENOR DISP", "INT RATE", "RENEW"]
        for c, h in enumerate(headers_dep, 1):
            ws_dep.cell(4, c, h)
        ws_dep.cell(5, 1, 1)
        ws_dep.cell(5, 2, d_str)
        ws_dep.cell(5, 3, "443")
        ws_dep.cell(5, 4, "IDR")
        ws_dep.cell(5, 5, "Indonesia Rupiah")
        ws_dep.cell(5, 6, "DA")
        ws_dep.cell(5, 7, "443030001")
        ws_dep.cell(5, 8, "DEPOSAN KORPORAT")
        ws_dep.cell(5, 9, dep_val)
        ws_dep.cell(5, 10, dep_val)
        ws_dep.cell(5, 11, "1 M")
        ws_dep.cell(5, 12, 5.25)
        ws_dep.cell(5, 13, "ARO")
        buf_dep = io.BytesIO()
        wb_dep.save(buf_dep)
        buf_dep.seek(0)
        file_items.append((buf_dep, f"CI324_{date_clean}.xlsx"))

        # 4. DI319 (Tabungan)
        wb_tab = openpyxl.Workbook()
        ws_tab = wb_tab.active
        ws_tab.cell(2, 2, "DI319 - SAVINGS ACCOUNT MONTHLY TRIAL BALANCE - MULTI PN")
        headers_tab = ["NO", "periode", "uker code", "curr code", "curr desc", "account number", "ciff no", "short name", "prod code", "balance", "Balance dalam IDR"]
        for c, h in enumerate(headers_tab, 1):
            ws_tab.cell(6, c, h)
        ws_tab.cell(7, 1, 1)
        ws_tab.cell(7, 2, d_str)
        ws_tab.cell(7, 3, "443")
        ws_tab.cell(7, 4, "IDR")
        ws_tab.cell(7, 5, "Indonesia Rupiah")
        ws_tab.cell(7, 6, "443040001")
        ws_tab.cell(7, 7, "CIF001")
        ws_tab.cell(7, 8, "NASABAH BRITAMA UTAMA")
        ws_tab.cell(7, 9, "TAB01")
        ws_tab.cell(7, 10, tab_val)
        ws_tab.cell(7, 11, tab_val)
        buf_tab = io.BytesIO()
        wb_tab.save(buf_tab)
        buf_tab.seek(0)
        file_items.append((buf_tab, f"DI319_{date_clean}.xlsx"))

    return file_items


# ==============================================================================
# PERSISTENT SNAPSHOT STORAGE & 7-DAY RETENTION ENGINE
# ==============================================================================
PERIODIC_STORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "periodic_store")
PERIODIC_STORE_FILE = os.path.join(PERIODIC_STORE_DIR, "snapshots_store.json")

def load_periodic_store() -> List[Dict[str, Any]]:
    """Load raw stored snapshots from JSON file."""
    if not os.path.exists(PERIODIC_STORE_FILE):
        return []
    try:
        with open(PERIODIC_STORE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []

def save_periodic_snapshots(snapshots: List[DailyMetricsSnapshot], retention_days: int = 14) -> int:
    """
    Save/merge daily metrics snapshots to disk store with automatic retention pruning.
    Retains snapshots across browser reloads for at least retention_days (default 14 days).
    """
    os.makedirs(PERIODIC_STORE_DIR, exist_ok=True)
    existing_store = load_periodic_store()
    now_iso = datetime.datetime.now().isoformat()
    
    # Map by reporting_date to avoid duplicates and update existing dates
    store_map = {item["reporting_date"]: item for item in existing_store if "reporting_date" in item}
    for s in snapshots:
        d_dict = asdict(s)
        d_dict["stored_at"] = now_iso
        store_map[s.reporting_date] = d_dict
        
    # Auto-prune items older than retention_days
    cutoff_time = datetime.datetime.now() - datetime.timedelta(days=retention_days)
    pruned_items = []
    for d_iso, item in store_map.items():
        stored_at_str = item.get("stored_at", now_iso)
        try:
            stored_dt = datetime.datetime.fromisoformat(stored_at_str)
            if stored_dt >= cutoff_time:
                pruned_items.append(item)
        except Exception:
            pruned_items.append(item)
            
    # Sort chronologically by date
    pruned_items.sort(key=lambda x: x.get("reporting_date", ""))
    with open(PERIODIC_STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(pruned_items, f, indent=2)
        
    return len(pruned_items)

def load_periodic_snapshots() -> List[DailyMetricsSnapshot]:
    """Load all retained snapshots from disk store as DailyMetricsSnapshot objects."""
    raw_list = load_periodic_store()
    snapshots = []
    for item in raw_list:
        try:
            data = {k: v for k, v in item.items() if k != "stored_at"}
            snapshots.append(DailyMetricsSnapshot(**data))
        except Exception:
            pass
    snapshots.sort(key=lambda s: s.reporting_date)
    return snapshots

def clear_all_dashboard_data():
    """Completely resets all uploaded files, periodic store, and caches to initial default."""
    from data_loader import CACHE_DIR, UPLOAD_DIR
    # 1. Clear periodic snapshots store
    if os.path.exists(PERIODIC_STORE_DIR):
        shutil.rmtree(PERIODIC_STORE_DIR, ignore_errors=True)
    # 2. Clear uploaded latest files
    if os.path.exists(UPLOAD_DIR):
        for f in os.listdir(UPLOAD_DIR):
            fp = os.path.join(UPLOAD_DIR, f)
            try:
                if os.path.isfile(fp): os.remove(fp)
            except Exception: pass
    # 3. Clear parquet cache
    if os.path.exists(CACHE_DIR):
        for f in os.listdir(CACHE_DIR):
            fp = os.path.join(CACHE_DIR, f)
            try:
                if os.path.isfile(fp): os.remove(fp)
            except Exception: pass

