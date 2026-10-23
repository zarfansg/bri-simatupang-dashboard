"""
Excel Export Engine for BRI KC TB Simatupang Performance Dashboard.
Generates comprehensive multi-sheet executive reports in native .xlsx format.
"""

import io
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
    font_title = Font(name="Calibri", size=14, bold=True, color="00529C")
    font_subtitle = Font(name="Calibri", size=10, italic=True, color="555555")
    font_header = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=10, bold=True)
    font_regular = Font(name="Calibri", size=10)
    
    fill_header = PatternFill(start_color="00529C", end_color="00529C", fill_type="solid")
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
    ws1["A4"].font = Font(name="Calibri", size=11, bold=True, color="00529C")
    
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
    ws1["A12"].font = Font(name="Calibri", size=11, bold=True, color="00529C")
    
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
