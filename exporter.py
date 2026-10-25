"""
Excel Export Engine for BRI KC TB Simatupang Performance Dashboard.
Generates comprehensive multi-sheet executive reports in native .xlsx format.
"""

import io
import numpy as np
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def export_dashboard_to_excel(lending_kpis, funding_kpis, df_matrix, reporting_date="30 September 2026"):
    """
    Builds a beautifully formatted multi-sheet Excel workbook:
    - Sheet 1: Ringkasan Eksekutif (Executive Overview)
    - Sheet 2: Portofolio Pinjaman (Lending Detail)
    - Sheet 3: Portofolio Simpanan (Funding / DPK Detail)
    - Sheet 4: Matriks Kinerja Unit Kerja (Branch & Sub-branch Matrix)
    """
    output = io.BytesIO()
    wb = openpyxl.Workbook()
    
    # Styles
    font_title = Font(name="Calibri", size=14, bold=True, color="0857C3")
    font_subtitle = Font(name="Calibri", size=10, italic=True, color="555555")
    font_header = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=10, bold=True)
    font_regular = Font(name="Calibri", size=10)
    
    fill_header = PatternFill(start_color="0857C3", end_color="0857C3", fill_type="solid")
    fill_subtotal = PatternFill(start_color="E6F0FA", end_color="E6F0FA", fill_type="solid")
    fill_kpi_card = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )
    double_bottom_border = Border(
        top=Side(style='thin', color='000000'),
        bottom=Side(style='double', color='000000')
    )
    
    # =========================================================================
    # SHEET 1: RINGKASAN EKSEKUTIF
    # =========================================================================
    ws1 = wb.active
    ws1.title = "Ringkasan Eksekutif"
    ws1.views.sheetView[0].showGridLines = True
    
    # Header Title
    ws1["A1"] = "BANK RAKYAT INDONESIA — KC JAKARTA TB SIMATUPANG (443)"
    ws1["A1"].font = font_title
    ws1["A2"] = f"LAPORAN KINERJA BISNIS KONSOLIDASI | Posisi Data: {reporting_date}"
    ws1["A2"].font = font_subtitle
    
    # Lending Summary Table
    ws1["A4"] = "1. POSISI PINJAMAN (LENDING — MAIN KPI: SMALL & CONSUMER)"
    ws1["A4"].font = Font(name="Calibri", size=11, bold=True, color="0857C3")
    
    headers_lending = ["Indikator Kredit", "Baki Debet (Rp)", "Jumlah Rekening", "Porsi (%)"]
    for col_idx, h in enumerate(headers_lending, 1):
        cell = ws1.cell(row=5, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center" if col_idx > 1 else "left")
        
    lending_rows = [
        ["Pinjaman Segmen Small (Komersial)", lending_kpis.get('os_small', 0), lending_kpis.get('count_small', 0), 
         (lending_kpis.get('os_small', 0) / lending_kpis.get('os_combined', 1)) * 100 if lending_kpis.get('os_combined', 0) > 0 else 0],
        ["Pinjaman Segmen Konsumer (Briguna, KPR, dll)", lending_kpis.get('os_consumer', 0), lending_kpis.get('count_consumer', 0),
         (lending_kpis.get('os_consumer', 0) / lending_kpis.get('os_combined', 1)) * 100 if lending_kpis.get('os_combined', 0) > 0 else 0],
        ["TOTAL PINJAMAN UTAMA (SMALL + CONSUMER)", lending_kpis.get('os_combined', 0), lending_kpis.get('main_records', 0), 100.0],
        ["Pinjaman Lainnya (Micro, Medium, Unidentified)", lending_kpis.get('os_excluded', 0), lending_kpis.get('excluded_records', 0), None],
        ["NPL Nominal (Kol 3, 4, 5)", lending_kpis.get('npl_nominal', 0), None, lending_kpis.get('npl_pct', 0)]
    ]
    
    for r_idx, row in enumerate(lending_rows, 6):
        ws1.cell(row=r_idx, column=1, value=row[0]).font = font_bold if r_idx in [8, 10] else font_regular
        c2 = ws1.cell(row=r_idx, column=2, value=row[1])
        c2.number_format = "#,##0"
        c2.font = font_bold if r_idx in [8, 10] else font_regular
        
        c3 = ws1.cell(row=r_idx, column=3, value=row[2])
        if row[2] is not None:
            c3.number_format = "#,##0"
        c3.font = font_bold if r_idx in [8, 10] else font_regular
        
        c4 = ws1.cell(row=r_idx, column=4, value=row[3] / 100.0 if row[3] is not None else "")
        if row[3] is not None:
            c4.number_format = "0.00%"
        c4.font = font_bold if r_idx in [8, 10] else font_regular
        
        for c in range(1, 5):
            ws1.cell(row=r_idx, column=c).border = thin_border
            if r_idx == 8:
                ws1.cell(row=r_idx, column=c).fill = fill_subtotal
                
    # Funding Summary Table
    ws1["A12"] = "2. POSISI SIMPANAN (FUNDING / DANA PIHAK KETIGA)"
    ws1["A12"].font = Font(name="Calibri", size=11, bold=True, color="0857C3")
    
    headers_funding = ["Jenis Simpanan", "Total Saldo (Rp)", "Jumlah Rekening / Bilyet", "Rasio CASA (%)"]
    for col_idx, h in enumerate(headers_funding, 1):
        cell = ws1.cell(row=13, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center" if col_idx > 1 else "left")
        
    funding_rows = [
        ["Giro (Current Account)", funding_kpis.get('giro_balance', 0), funding_kpis.get('giro_count', 0), funding_kpis.get('pct_giro', 0)],
        ["Tabungan (Savings Account)", funding_kpis.get('tab_balance', 0), funding_kpis.get('tab_count', 0), funding_kpis.get('pct_tab', 0)],
        ["TOTAL CASA (DANA MURAH)", funding_kpis.get('casa_balance', 0), funding_kpis.get('giro_count', 0) + funding_kpis.get('tab_count', 0), funding_kpis.get('casa_pct', 0)],
        ["Deposito Berjangka (Time Deposit)", funding_kpis.get('dep_balance', 0), funding_kpis.get('dep_count', 0), funding_kpis.get('pct_dep', 0)],
        ["TOTAL DANA PIHAK KETIGA (DPK)", funding_kpis.get('total_funding', 0), funding_kpis.get('total_accounts', 0), 100.0]
    ]
    
    for r_idx, row in enumerate(funding_rows, 14):
        ws1.cell(row=r_idx, column=1, value=row[0]).font = font_bold if r_idx in [16, 18] else font_regular
        c2 = ws1.cell(row=r_idx, column=2, value=row[1])
        c2.number_format = "#,##0"
        c2.font = font_bold if r_idx in [16, 18] else font_regular
        
        c3 = ws1.cell(row=r_idx, column=3, value=row[2])
        c3.number_format = "#,##0"
        c3.font = font_bold if r_idx in [16, 18] else font_regular
        
        c4 = ws1.cell(row=r_idx, column=4, value=row[3] / 100.0 if row[3] is not None else 0)
        c4.number_format = "0.00%"
        c4.font = font_bold if r_idx in [16, 18] else font_regular
        
        for c in range(1, 5):
            ws1.cell(row=r_idx, column=c).border = thin_border
            if r_idx in [16, 18]:
                ws1.cell(row=r_idx, column=c).fill = fill_subtotal

    # =========================================================================
    # SHEET 2: MATRIKS KINERJA PER UNIT KERJA
    # =========================================================================
    if df_matrix is not None and len(df_matrix) > 0:
        ws2 = wb.create_sheet(title="Matriks Unit Kerja")
        ws2.views.sheetView[0].showGridLines = True
        
        ws2["A1"] = "MATRIKS PERFORMA KONSOLIDASI PER UNIT KERJA"
        ws2["A1"].font = font_title
        ws2["A2"] = f"KC Jakarta TB Simatupang (443), KCP Supervisi, dan Kantor Kas | {reporting_date}"
        ws2["A2"].font = font_subtitle
        
        cols = list(df_matrix.columns)
        for col_idx, col_name in enumerate(cols, 1):
            cell = ws2.cell(row=4, column=col_idx, value=col_name)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal="center" if col_idx > 3 else "left")
            
        for r_idx, row in df_matrix.iterrows():
            curr_row = r_idx + 5
            for c_idx, col_name in enumerate(cols, 1):
                val = row[col_name]
                cell = ws2.cell(row=curr_row, column=c_idx, value=val)
                cell.font = font_regular
                cell.border = thin_border
                if "Rp" in col_name or "Total" in col_name:
                    cell.number_format = "#,##0"
                elif "Rek" in col_name:
                    cell.number_format = "#,##0"
                    
    # Auto-adjust column widths
    for sheet in wb.worksheets:
        for col in sheet.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or '')
                if len(val_str) > max_len and len(val_str) < 50:
                    max_len = len(val_str)
            sheet.column_dimensions[col_letter].width = max(max_len + 4, 12)
            
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def export_periodic_dashboard_to_excel(
    periodic_summary,
    branch_name: str = "KC Jakarta TB Simatupang (443)"
) -> bytes:
    """
    Exports periodic monitoring dashboard into executive multi-sheet Excel workbook:
    - Sheet 1: KERAGAAN_SIMPANAN_HARIAN (Simpanan Matrix + DtD & MTD formulas)
    - Sheet 2: KERAGAAN_PINJAMAN_HARIAN (Pinjaman Matrix + DtD & MTD formulas)
    - Sheet 3: RINGKASAN_TREN_HARIAN (Consolidated chronological time-series table)
    """
    output = io.BytesIO()
    wb = openpyxl.Workbook()

    font_title = Font(name="Calibri", size=13, bold=True, color="0857C3")
    font_subtitle = Font(name="Calibri", size=10, italic=True, color="555555")
    font_header = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=10, bold=True)
    font_regular = Font(name="Calibri", size=10)
    font_na = Font(name="Calibri", size=10, italic=True, color="888888")

    fill_header = PatternFill(start_color="0857C3", end_color="0857C3", fill_type="solid")
    fill_total = PatternFill(start_color="E6F0FA", end_color="E6F0FA", fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )
    double_bottom_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='000000'),
        bottom=Side(style='double', color='000000')
    )

    dates = periodic_summary.dates_analyzed
    has_baseline = (
        periodic_summary.month_end_baseline is not None and
        periodic_summary.month_end_baseline.get("is_verified", False)
    )
    baseline_disp = periodic_summary.month_end_baseline.get("display_date", "Akhir Bulan Lalu") if has_baseline else "N/A"

    def write_matrix_sheet(ws, title_text, subtitle_text, matrix_df):
        ws.views.sheetView[0].showGridLines = True

        # Header Titles
        ws["A1"] = f"BANK RAKYAT INDONESIA — {branch_name.upper()}"
        ws["A1"].font = font_title
        ws["A2"] = f"{title_text} | {subtitle_text}"
        ws["A2"].font = font_subtitle

        cols = list(matrix_df.columns)
        num_cols = len(cols)

        # Determine column positions for formulas
        # cols: [Indikator Produk, Baseline, Date1, Date2, ..., DateN, DtD (Rp), DtD (%), MTD (Rp), MTD (%)]
        # Baseline is column 2
        # Daily dates are from col 3 to (num_cols - 4)
        has_dates = len(dates) > 0
        latest_date_col_idx = (num_cols - 4) if len(dates) > 0 else None
        prev_date_col_idx = (num_cols - 5) if len(dates) >= 2 else None

        # Write Table Headers (Row 4)
        for col_idx, col_name in enumerate(cols, 1):
            cell = ws.cell(row=4, column=col_idx, value=col_name)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal="center" if col_idx > 1 else "left", vertical="center")

        # Write Data Rows (starting Row 5)
        for r_idx, row in matrix_df.iterrows():
            curr_row = r_idx + 5
            is_total_row = (r_idx == 0)

            for c_idx, col_name in enumerate(cols, 1):
                cell = ws.cell(row=curr_row, column=c_idx)
                raw_val = row[col_name]

                # Style & Border
                if is_total_row:
                    cell.font = font_bold
                    cell.fill = fill_total
                    cell.border = double_bottom_border
                else:
                    cell.font = font_regular
                    cell.border = thin_border

                if c_idx == 1:
                    cell.value = str(raw_val)
                    cell.alignment = Alignment(horizontal="left", vertical="center")
                elif col_name.startswith("Baseline"):
                    if has_baseline and raw_val is not None:
                        cell.value = float(raw_val)
                        cell.number_format = "#,##0"
                    else:
                        cell.value = "N/A"
                        cell.font = font_na
                    cell.alignment = Alignment(horizontal="right" if cell.value != "N/A" else "center", vertical="center")
                elif col_name == "DtD (Rp)":
                    if prev_date_col_idx and latest_date_col_idx:
                        c_curr = get_column_letter(latest_date_col_idx)
                        c_prev = get_column_letter(prev_date_col_idx)
                        cell.value = f"={c_curr}{curr_row}-{c_prev}{curr_row}"
                        cell.number_format = "#,##0;[Red](#,##0);\"-\""
                    else:
                        cell.value = "-"
                    cell.alignment = Alignment(horizontal="right" if cell.value != "-" else "center", vertical="center")
                elif col_name == "DtD (%)":
                    if prev_date_col_idx and latest_date_col_idx:
                        c_curr = get_column_letter(latest_date_col_idx)
                        c_prev = get_column_letter(prev_date_col_idx)
                        cell.value = f"=IF({c_prev}{curr_row}>0, ({c_curr}{curr_row}-{c_prev}{curr_row})/{c_prev}{curr_row}, 0)"
                        cell.number_format = "0.00%;[Red]-0.00%;\"0.00%\""
                    else:
                        cell.value = "-"
                    cell.alignment = Alignment(horizontal="right" if cell.value != "-" else "center", vertical="center")
                elif col_name == "MTD (Rp)":
                    if has_baseline and latest_date_col_idx:
                        c_curr = get_column_letter(latest_date_col_idx)
                        c_base = get_column_letter(2)
                        cell.value = f"={c_curr}{curr_row}-{c_base}{curr_row}"
                        cell.number_format = "#,##0;[Red](#,##0);\"-\""
                        cell.alignment = Alignment(horizontal="right", vertical="center")
                    else:
                        cell.value = "N/A"
                        cell.font = font_na
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                elif col_name == "MTD (%)":
                    if has_baseline and latest_date_col_idx:
                        c_curr = get_column_letter(latest_date_col_idx)
                        c_base = get_column_letter(2)
                        cell.value = f"=IF({c_base}{curr_row}>0, ({c_curr}{curr_row}-{c_base}{curr_row})/{c_base}{curr_row}, 0)"
                        cell.number_format = "0.00%;[Red]-0.00%;\"0.00%\""
                        cell.alignment = Alignment(horizontal="right", vertical="center")
                    else:
                        cell.value = "N/A"
                        cell.font = font_na
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    # Daily date balances
                    if raw_val is not None and not pd.isna(raw_val):
                        cell.value = float(raw_val)
                        cell.number_format = "#,##0"
                    else:
                        cell.value = "-"
                    cell.alignment = Alignment(horizontal="right" if cell.value != "-" else "center", vertical="center")

        # Conditional formatting for DtD and MTD columns (Green for >0, Red for <0)
        if num_cols >= 4 and len(matrix_df) > 0:
            from openpyxl.formatting.rule import CellIsRule
            fill_pos = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
            font_pos = Font(name="Calibri", size=10, bold=True, color="15803D")
            fill_neg = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
            font_neg = Font(name="Calibri", size=10, bold=True, color="B91C1C")

            rule_green = CellIsRule(operator='greaterThan', formula=['0'], stopIfTrue=False, fill=fill_pos, font=font_pos)
            rule_red = CellIsRule(operator='lessThan', formula=['0'], stopIfTrue=False, fill=fill_neg, font=font_neg)

            col_start_letter = get_column_letter(num_cols - 3)
            col_end_letter = get_column_letter(num_cols)
            last_row = len(matrix_df) + 4
            rule_range = f"{col_start_letter}5:{col_end_letter}{last_row}"
            ws.conditional_formatting.add(rule_range, rule_green)
            ws.conditional_formatting.add(rule_range, rule_red)

        # Column widths
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or '')
                if len(val_str) > max_len and len(val_str) < 40:
                    max_len = len(val_str)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 14)

    # 1. Sheet 1: DPK Matrix
    ws_dpk = wb.active
    ws_dpk.title = "KERAGAAN_SIMPANAN_HARIAN"
    write_matrix_sheet(
        ws_dpk,
        "PEMANTAUAN KINERJA SIMPANAN (DPK) HARIAN",
        f"Posisi: {dates[0] if dates else '-'} s.d. {dates[-1] if dates else '-'}",
        periodic_summary.daily_matrix_dpk
    )

    # 2. Sheet 2: Lending Matrix
    ws_lend = wb.create_sheet(title="KERAGAAN_PINJAMAN_HARIAN")
    write_matrix_sheet(
        ws_lend,
        "PEMANTAUAN KINERJA PINJAMAN UTAMA (SMALL & CONSUMER) HARIAN",
        f"Posisi: {dates[0] if dates else '-'} s.d. {dates[-1] if dates else '-'}",
        periodic_summary.daily_matrix_lending
    )

    # 3. Sheet 3: Time-Series Summary Table
    ws_trend = wb.create_sheet(title="RINGKASAN_TREN_HARIAN")
    ws_trend.views.sheetView[0].showGridLines = True
    ws_trend["A1"] = f"BANK RAKYAT INDONESIA — {branch_name.upper()}"
    ws_trend["A1"].font = font_title
    ws_trend["A2"] = "TABEL TREN HARIAN LENGKAP"
    ws_trend["A2"].font = font_subtitle

    df_sum = periodic_summary.summary_df
    if not df_sum.empty:
        sum_cols = list(df_sum.columns)
        for c_idx, c_name in enumerate(sum_cols, 1):
            cell = ws_trend.cell(row=4, column=c_idx, value=c_name)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for r_idx, row in df_sum.iterrows():
            curr_row = r_idx + 5
            for c_idx, c_name in enumerate(sum_cols, 1):
                cell = ws_trend.cell(row=curr_row, column=c_idx)
                val = row[c_name]
                cell.font = font_regular
                cell.border = thin_border

                if val is None or pd.isna(val) or val == "-":
                    cell.value = "N/A" if "MTD" in c_name and not has_baseline else "-"
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                elif isinstance(val, (int, float, np.number)):
                    cell.value = float(val)
                    if "%" in c_name or "Ratio" in c_name:
                        cell.value = float(val) / 100.0 if abs(val) > 1.0 else float(val)
                        cell.number_format = "0.00%;[Red]-0.00%;\"0.00%\""
                    elif "Gap" in c_name:
                        cell.number_format = "#,##0"
                    else:
                        cell.number_format = "#,##0;[Red](#,##0);\"-\""
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                else:
                    cell.value = str(val)
                    cell.alignment = Alignment(horizontal="center" if "Tanggal" in c_name or "ISO" in c_name or "Baseline" in c_name else "left", vertical="center")

        for col in ws_trend.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or '')
                if len(val_str) > max_len and len(val_str) < 40:
                    max_len = len(val_str)
            ws_trend.column_dimensions[col_letter].width = max(max_len + 3, 13)

    wb.save(output)
    output.seek(0)
    return output.getvalue()

