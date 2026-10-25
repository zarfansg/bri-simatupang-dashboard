"""
Production-grade Report Identification, Reporting-Date Validation, and Daily Batch Ingestion Engine.
Enforces strict data integrity for BRI KC TB Simatupang periodic monitoring pipeline:
- Identifies report types via validated title headers AND distinctive column signatures.
- Enforces 100% row-level reporting-date uniformity (rejects mixed-date files).
- Validates 4-report completeness (LW321, DI319, DI321, CI324) matching the exact same date.
- Enforces safe duplicate handling with atomic replacement and transactional rollback.
"""

import os
import re
import uuid
import shutil
import json
import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Union, BinaryIO, Any

import pandas as pd
import numpy as np


# Report type definitions and signature rules
REPORT_TYPES = ["LW321", "DI321", "CI324", "DI319"]

REPORT_DESCRIPTIONS = {
    "LW321": "Laporan Kolektibilitas dan Tunggakan Pinjaman (Lending)",
    "DI321": "Current Account Monthly Trial Balance (Giro)",
    "CI324": "Multi PN - FDs Monthly Trial Balance (Deposito)",
    "DI319": "Savings Account Monthly Trial Balance (Tabungan)"
}


@dataclass
class ReportValidationResult:
    is_valid: bool
    report_type: Optional[str]
    reporting_date: Optional[str]         # Standardized ISO: YYYY-MM-DD
    display_date: Optional[str]           # Format: DD/MM/YYYY
    row_count: int
    detected_header_row: int
    source_identifier: str
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class BatchValidationResult:
    is_valid: bool
    reporting_date: Optional[str]
    display_date: Optional[str]
    reports: Dict[str, ReportValidationResult] = field(default_factory=dict)
    missing_reports: List[str] = field(default_factory=list)
    date_mismatches: List[str] = field(default_factory=list)
    duplicate_reports: List[str] = field(default_factory=list)
    unrecognized_files: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


@dataclass
class BatchPublishResult:
    success: bool
    status: str                           # 'PUBLISHED', 'DUPLICATE_REPLACE_REQUIRED', 'FAILED'
    reporting_date: Optional[str]
    target_path: Optional[str]
    published_reports: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


def normalize_date_value(val) -> Optional[Tuple[str, str]]:
    """
    Safely normalizes various date representations into (YYYY-MM-DD, DD/MM/YYYY).
    Handles strings, pandas Timestamps, and datetime objects.
    Returns None if value cannot be parsed as a valid date.
    """
    if pd.isna(val) or val is None:
        return None

    if isinstance(val, (datetime.datetime, datetime.date, pd.Timestamp)):
        iso_str = val.strftime("%Y-%m-%d")
        disp_str = val.strftime("%d/%m/%Y")
        return iso_str, disp_str

    s = str(val).strip()
    if not s:
        return None

    # Pattern DD/MM/YYYY or DD-MM-YYYY
    m1 = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", s)
    if m1:
        d, m, y = int(m1.group(1)), int(m1.group(2)), int(m1.group(3))
        try:
            dt = datetime.date(y, m, d)
            return dt.strftime("%Y-%m-%d"), dt.strftime("%d/%m/%Y")
        except ValueError:
            return None

    # Pattern YYYY-MM-DD or YYYY/MM/DD
    m2 = re.match(r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$", s)
    if m2:
        y, m, d = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        try:
            dt = datetime.date(y, m, d)
            return dt.strftime("%Y-%m-%d"), dt.strftime("%d/%m/%Y")
        except ValueError:
            return None

    # Fallback to pandas parser
    try:
        dt = pd.to_datetime(s, dayfirst=True)
        return dt.strftime("%Y-%m-%d"), dt.strftime("%d/%m/%Y")
    except Exception:
        return None


def _clean_col_names(raw_cols: List) -> List[str]:
    """Normalize column names to uppercase stripped string."""
    cleaned = []
    for c in raw_cols:
        if pd.isna(c) or c is None:
            cleaned.append("")
        else:
            cleaned.append(str(c).strip().upper())
    return cleaned


def _score_report_schema(header_text: str, cols: List[str]) -> Tuple[Optional[str], float, str]:
    """
    Evaluates schema signature and header keywords to determine report type.
    Returns (detected_report_type, confidence_score, explanation).
    """
    cols_set = set(cols)
    header_upper = header_text.upper()

    scores = {"LW321": 0.0, "DI321": 0.0, "CI324": 0.0, "DI319": 0.0}

    # 1. Header Title Keywords
    if "LW321" in header_upper or "LAPORAN KOLEKTIBILITAS" in header_upper:
        scores["LW321"] += 50.0
    if "DI321" in header_upper or "CURRENT ACCOUNT" in header_upper:
        scores["DI321"] += 50.0
    if "CI324" in header_upper or "FDS MONTHLY" in header_upper or "TIME DEPOSIT" in header_upper:
        scores["CI324"] += 50.0
    if "DI319" in header_upper or "SAVINGS ACCOUNT" in header_upper:
        scores["DI319"] += 50.0

    # 2. Distinctive Column Matches
    # LW321 distinctive
    if "LN_TYPE" in cols_set: scores["LW321"] += 20.0
    if "PLAFON DALAM IDR" in cols_set or "PLAFON" in cols_set: scores["LW321"] += 15.0
    if "TUNGGAKAN POKOK" in cols_set: scores["LW321"] += 15.0
    if "NAMA_DEBITUR" in cols_set or "NAMA DEBITUR" in cols_set: scores["LW321"] += 10.0

    # DI321 distinctive (Giro)
    if "CURR" in cols_set and "ACCOUNT NUMBER" in cols_set and "BALANCE" in cols_set:
        scores["DI321"] += 25.0
    if "AVRG BALANCE" in cols_set: scores["DI321"] += 20.0
    if "SHORT NAME" in cols_set and "PRODUCT CODE" in cols_set: scores["DI321"] += 15.0

    # CI324 distinctive (Deposito)
    if "CBAL BASE" in cols_set: scores["CI324"] += 25.0
    if "INT TENOR DISP" in cols_set: scores["CI324"] += 20.0
    if "PRINCIPAL AMOUNT" in cols_set: scores["CI324"] += 15.0
    if "INT RATE" in cols_set: scores["CI324"] += 10.0

    # DI319 distinctive (Tabungan)
    if "CIFF NO" in cols_set: scores["DI319"] += 25.0
    if "PROD CODE" in cols_set: scores["DI319"] += 15.0
    if "ACCOUNT NUMBER" in cols_set and "BALANCE DALAM IDR" in cols_set: scores["DI319"] += 20.0

    # 3. Exclusion Penalties (Strict separation)
    if "LN_TYPE" in cols_set:
        scores["DI321"] -= 100.0
        scores["CI324"] -= 100.0
        scores["DI319"] -= 100.0

    if "CBAL BASE" in cols_set or "INT TENOR DISP" in cols_set:
        scores["LW321"] -= 100.0
        scores["DI321"] -= 100.0
        scores["DI319"] -= 100.0

    if "CIFF NO" in cols_set:
        scores["LW321"] -= 100.0
        scores["DI321"] -= 100.0
        scores["CI324"] -= 100.0

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    # Threshold for positive identification: at least 45 points
    if best_score >= 45.0:
        return best_type, best_score, f"Identified as {best_type} with confidence score {best_score:.1f}"
    else:
        return None, best_score, f"Ambiguous schema: highest candidate {best_type} scored only {best_score:.1f}"


def inspect_and_identify_report(
    source_file_or_buffer: Union[str, BinaryIO],
    source_name: str = ""
) -> ReportValidationResult:
    """
    Validates a single raw Excel report:
    1. Locates header row dynamically within first 15 rows.
    2. Identifies report type using header text keywords and column schema signatures.
    3. Locates PERIODE column and verifies that 100% of rows contain the exact same reporting date.
    4. Rejects mixed-date or inconsistent files.
    """
    identifier = source_name or (str(source_file_or_buffer) if isinstance(source_file_or_buffer, str) else "uploaded_report")

    if hasattr(source_file_or_buffer, "seek"):
        try:
            source_file_or_buffer.seek(0)
        except Exception:
            pass

    try:
        # Read first 15 rows to detect structure
        preview_df = pd.read_excel(source_file_or_buffer, header=None, nrows=15)
    except Exception as e:
        return ReportValidationResult(
            is_valid=False,
            report_type=None,
            reporting_date=None,
            display_date=None,
            row_count=0,
            detected_header_row=-1,
            source_identifier=identifier,
            error_message=f"Failed to read Excel workbook: {str(e)}"
        )

    if preview_df.empty:
        return ReportValidationResult(
            is_valid=False,
            report_type=None,
            reporting_date=None,
            display_date=None,
            row_count=0,
            detected_header_row=-1,
            source_identifier=identifier,
            error_message="Workbook sheet is completely empty"
        )

    # 1. Scan for header row containing PERIODE or periode
    header_row_idx = None
    header_text_accumulator = []

    for r_idx in range(min(15, len(preview_df))):
        row_vals = preview_df.iloc[r_idx].dropna().tolist()
        row_str = " ".join([str(v) for v in row_vals])
        header_text_accumulator.append(row_str)

        # Look for PERIODE column name in this row
        cleaned_cells = [str(v).strip().upper() for v in row_vals]
        if "PERIODE" in cleaned_cells:
            header_row_idx = r_idx
            break

    combined_header_text = " | ".join(header_text_accumulator)

    if header_row_idx is None:
        return ReportValidationResult(
            is_valid=False,
            report_type=None,
            reporting_date=None,
            display_date=None,
            row_count=0,
            detected_header_row=-1,
            source_identifier=identifier,
            error_message="Could not find table header with 'PERIODE' column within the first 15 rows"
        )

    # 2. Extract column names from header row
    raw_headers = preview_df.iloc[header_row_idx].tolist()
    clean_cols = _clean_col_names(raw_headers)

    # 3. Determine Report Type
    report_type, score, explanation = _score_report_schema(combined_header_text, clean_cols)

    if not report_type:
        return ReportValidationResult(
            is_valid=False,
            report_type=None,
            reporting_date=None,
            display_date=None,
            row_count=0,
            detected_header_row=header_row_idx,
            source_identifier=identifier,
            error_message=f"Failed to identify valid BRI report type: {explanation}"
        )

    # 4. Load full dataset starting from header_row
    try:
        # Seek back if file-like object
        if hasattr(source_file_or_buffer, "seek"):
            source_file_or_buffer.seek(0)

        df_full = pd.read_excel(source_file_or_buffer, skiprows=header_row_idx)
        df_full = df_full.dropna(how="all", axis=0).dropna(how="all", axis=1)
    except Exception as e:
        return ReportValidationResult(
            is_valid=False,
            report_type=report_type,
            reporting_date=None,
            display_date=None,
            row_count=0,
            detected_header_row=header_row_idx,
            source_identifier=identifier,
            error_message=f"Failed to parse data rows after header: {str(e)}"
        )

    row_count = len(df_full)
    if row_count == 0:
        return ReportValidationResult(
            is_valid=False,
            report_type=report_type,
            reporting_date=None,
            display_date=None,
            row_count=0,
            detected_header_row=header_row_idx,
            source_identifier=identifier,
            error_message="Report table contains zero data rows"
        )

    # 5. Locate PERIODE column (case-insensitive)
    periode_col = None
    for c in df_full.columns:
        if str(c).strip().upper() == "PERIODE":
            periode_col = c
            break

    if not periode_col:
        return ReportValidationResult(
            is_valid=False,
            report_type=report_type,
            reporting_date=None,
            display_date=None,
            row_count=row_count,
            detected_header_row=header_row_idx,
            source_identifier=identifier,
            error_message="Column 'PERIODE' missing after loading table"
        )

    # 6. Verify row-level reporting date consistency across ALL data rows
    periode_series = df_full[periode_col].dropna()
    if len(periode_series) == 0:
        return ReportValidationResult(
            is_valid=False,
            report_type=report_type,
            reporting_date=None,
            display_date=None,
            row_count=row_count,
            detected_header_row=header_row_idx,
            source_identifier=identifier,
            error_message="Column 'PERIODE' contains only null/empty values across all rows"
        )

    unique_raw_dates = periode_series.unique()
    normalized_dates = []
    invalid_date_entries = []

    for val in unique_raw_dates:
        norm = normalize_date_value(val)
        if norm is None:
            invalid_date_entries.append(str(val))
        else:
            normalized_dates.append(norm)

    if invalid_date_entries:
        return ReportValidationResult(
            is_valid=False,
            report_type=report_type,
            reporting_date=None,
            display_date=None,
            row_count=row_count,
            detected_header_row=header_row_idx,
            source_identifier=identifier,
            error_message=f"Found unparseable date values in 'PERIODE' column: {invalid_date_entries[:5]}"
        )

    unique_iso_dates = sorted(list(set([d[0] for d in normalized_dates])))

    if len(unique_iso_dates) > 1:
        return ReportValidationResult(
            is_valid=False,
            report_type=report_type,
            reporting_date=None,
            display_date=None,
            row_count=row_count,
            detected_header_row=header_row_idx,
            source_identifier=identifier,
            error_message=f"Inconsistent reporting dates detected within file: found {len(unique_iso_dates)} distinct dates: {unique_iso_dates}"
        )

    # Exactly 1 consistent reporting date!
    reporting_date = unique_iso_dates[0]
    display_date = normalized_dates[0][1]

    return ReportValidationResult(
        is_valid=True,
        report_type=report_type,
        reporting_date=reporting_date,
        display_date=display_date,
        row_count=row_count,
        detected_header_row=header_row_idx,
        source_identifier=identifier
    )


def validate_daily_batch(
    file_items: List[Tuple[Union[str, BinaryIO], str]]
) -> BatchValidationResult:
    """
    Validates a candidate daily batch.
    Requires exactly one valid report for each of: LW321, DI319, DI321, CI324.
    Requires all 4 reports to belong to the exact same reporting date.
    """
    reports_by_type: Dict[str, ReportValidationResult] = {}
    duplicates: List[str] = []
    unrecognized: List[str] = []
    dates_found: Dict[str, List[str]] = {}

    for file_obj, fname in file_items:
        res = inspect_and_identify_report(file_obj, source_name=fname)

        if not res.is_valid:
            unrecognized.append(f"{fname}: {res.error_message}")
            continue

        rtype = res.report_type
        if rtype in reports_by_type:
            duplicates.append(f"Duplicate {rtype} uploaded: {fname} conflicts with {reports_by_type[rtype].source_identifier}")
        else:
            reports_by_type[rtype] = res
            rdate = res.reporting_date
            dates_found.setdefault(rdate, []).append(rtype)

    # Check completeness
    missing = [rt for rt in REPORT_TYPES if rt not in reports_by_type]

    # Check date agreement
    unique_dates = list(dates_found.keys())
    date_mismatches = []
    if len(unique_dates) > 1:
        date_mismatches = [f"{rt} reported {d}" for d, rts in dates_found.items() for rt in rts]

    # Overall validity
    is_valid = (len(missing) == 0) and (len(unique_dates) == 1) and (len(duplicates) == 0) and (len(unrecognized) == 0)

    final_date = unique_dates[0] if len(unique_dates) == 1 else None
    disp_date = reports_by_type[next(iter(reports_by_type))].display_date if final_date and reports_by_type else None

    error_parts = []
    if missing:
        error_parts.append(f"Missing required reports: {', '.join(missing)}")
    if date_mismatches:
        error_parts.append(f"Reporting date mismatch between files: {', '.join(date_mismatches)}")
    if duplicates:
        error_parts.append(f"Duplicate reports found: {'; '.join(duplicates)}")
    if unrecognized:
        error_parts.append(f"Invalid/unrecognized files: {'; '.join(unrecognized)}")

    error_msg = " | ".join(error_parts) if error_parts else None

    return BatchValidationResult(
        is_valid=is_valid,
        reporting_date=final_date,
        display_date=disp_date,
        reports=reports_by_type,
        missing_reports=missing,
        date_mismatches=date_mismatches,
        duplicate_reports=duplicates,
        unrecognized_files=unrecognized,
        error_message=error_msg
    )


def publish_daily_batch(
    batch_result: BatchValidationResult,
    source_file_map: Dict[str, str],
    published_storage_dir: str,
    replace: bool = False
) -> BatchPublishResult:
    """
    Safely publishes a validated daily batch into published_storage_dir/{YYYY-MM-DD}/.
    Enforces atomic replace-or-cancel:
    - If target date exists and replace=False: returns DUPLICATE_REPLACE_REQUIRED without modifying anything.
    - If replace=True: uses isolated staging and rollback backup to preserve previous valid snapshot on failure.
    """
    if not batch_result.is_valid:
        return BatchPublishResult(
            success=False,
            status="FAILED",
            reporting_date=batch_result.reporting_date,
            target_path=None,
            error_message=f"Cannot publish invalid batch: {batch_result.error_message}"
        )

    reporting_date = batch_result.reporting_date
    target_dir = os.path.join(published_storage_dir, reporting_date)
    os.makedirs(published_storage_dir, exist_ok=True)

    # 1. Duplicate check
    if os.path.exists(target_dir):
        if not replace:
            return BatchPublishResult(
                success=False,
                status="DUPLICATE_REPLACE_REQUIRED",
                reporting_date=reporting_date,
                target_path=target_dir,
                error_message=f"Batch for reporting date {reporting_date} already exists. Explicit confirmation (replace=True) is required."
            )

    # 2. Atomic Staging Pipeline
    staging_id = f"staging_{reporting_date}_{uuid.uuid4().hex[:8]}"
    staging_dir = os.path.join(published_storage_dir, staging_id)
    backup_dir = os.path.join(published_storage_dir, f"backup_{reporting_date}_{uuid.uuid4().hex[:8]}")

    try:
        os.makedirs(staging_dir, exist_ok=True)

        copied_reports = []
        manifest_data = {
            "reporting_date": reporting_date,
            "display_date": batch_result.display_date,
            "published_at": datetime.datetime.now().isoformat(),
            "status": "VALIDATED_PUBLISHED",
            "reports": {}
        }

        # Copy each of the 4 reports into staging
        for rtype, rinfo in batch_result.reports.items():
            src_path = source_file_map.get(rtype)
            if not src_path or not os.path.exists(src_path):
                raise FileNotFoundError(f"Source file for {rtype} at '{src_path}' could not be located")

            ext = os.path.splitext(src_path)[1]
            dest_name = f"{rtype}{ext}"
            dest_path = os.path.join(staging_dir, dest_name)
            shutil.copy2(src_path, dest_path)
            copied_reports.append(rtype)

            manifest_data["reports"][rtype] = {
                "source_file": os.path.basename(src_path),
                "published_file": dest_name,
                "row_count": rinfo.row_count,
                "header_row": rinfo.detected_header_row,
                "file_size_bytes": os.path.getsize(dest_path)
            }

        # Write manifest.json
        manifest_path = os.path.join(staging_dir, "batch_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        # 3. Transactional Swap
        if os.path.exists(target_dir):
            shutil.move(target_dir, backup_dir)

        shutil.move(staging_dir, target_dir)

        # Remove backup on successful publication
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir, ignore_errors=True)

        return BatchPublishResult(
            success=True,
            status="PUBLISHED",
            reporting_date=reporting_date,
            target_path=target_dir,
            published_reports=copied_reports
        )

    except Exception as e:
        # Rollback: Clean staging
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir, ignore_errors=True)

        # Restore previous valid snapshot if backup was made
        if os.path.exists(backup_dir) and not os.path.exists(target_dir):
            shutil.move(backup_dir, target_dir)

        return BatchPublishResult(
            success=False,
            status="FAILED",
            reporting_date=reporting_date,
            target_path=None,
            error_message=f"Publication transaction failed and was rolled back: {str(e)}"
        )


@dataclass
class MultiDayBatchValidationResult:
    total_files_analyzed: int
    valid_files_count: int
    invalid_files: List[Dict[str, str]] = field(default_factory=list)
    complete_batches: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    incomplete_batches: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    duplicate_conflicts: List[Dict[str, str]] = field(default_factory=list)
    all_detected_dates: List[str] = field(default_factory=list)
    complete_dates: List[str] = field(default_factory=list)


def validate_and_group_multiday_batches(
    file_items: List[Tuple[Union[str, BinaryIO], str]]
) -> MultiDayBatchValidationResult:
    """
    Ingests an arbitrary collection of uploaded reports across multiple reporting dates.
    1. Inspects and identifies each file.
    2. Flags and isolates invalid/unparseable files.
    3. Groups valid files by reporting_date.
    4. Detects intra-date duplicate report collisions.
    5. Categorizes each date into complete_batches (all 4 reports: LW321, DI319, DI321, CI324 present without collision)
       or incomplete_batches.
    """
    total_analyzed = len(file_items)
    valid_files = 0
    invalid_files: List[Dict[str, str]] = []
    
    # Structure: {iso_date: {"display_date": ..., "reports": {rtype: {"res": ..., "file_obj": ..., "filename": ...}}, "duplicates": [...]}}
    date_buckets: Dict[str, Dict[str, Any]] = {}

    for file_obj, fname in file_items:
        res = inspect_and_identify_report(file_obj, source_name=fname)
        
        if not res.is_valid:
            invalid_files.append({"filename": fname, "error": res.error_message or "Unknown validation error"})
            continue
            
        valid_files += 1
        rdate = res.reporting_date
        rtype = res.report_type
        
        if rdate not in date_buckets:
            date_buckets[rdate] = {
                "display_date": res.display_date,
                "reports": {},
                "duplicates": []
            }
            
        bucket = date_buckets[rdate]
        if rtype in bucket["reports"]:
            existing_fname = bucket["reports"][rtype]["filename"]
            conflict_msg = f"Duplicate {rtype} uploaded for date {rdate}: '{fname}' conflicts with '{existing_fname}'"
            bucket["duplicates"].append({
                "date": rdate,
                "report_type": rtype,
                "first_file": existing_fname,
                "conflicting_file": fname,
                "message": conflict_msg
            })
        else:
            bucket["reports"][rtype] = {
                "res": res,
                "file_obj": file_obj,
                "filename": fname
            }

    complete_batches: Dict[str, Dict[str, Any]] = {}
    incomplete_batches: Dict[str, Dict[str, Any]] = {}
    all_duplicate_conflicts: List[Dict[str, str]] = []
    
    sorted_dates = sorted(list(date_buckets.keys()))
    complete_dates = []

    for d in sorted_dates:
        b = date_buckets[d]
        reports_present = list(b["reports"].keys())
        missing = [rt for rt in REPORT_TYPES if rt not in reports_present]
        dups = b["duplicates"]
        all_duplicate_conflicts.extend(dups)
        
        # If there are duplicate conflicts, or missing reports, this date cannot be considered complete
        if len(missing) == 0 and len(dups) == 0:
            complete_batches[d] = {
                "display_date": b["display_date"],
                "reports": b["reports"]
            }
            complete_dates.append(d)
        else:
            incomplete_batches[d] = {
                "display_date": b["display_date"],
                "present": reports_present,
                "missing": missing,
                "has_duplicate_conflict": len(dups) > 0,
                "duplicates": dups
            }

    return MultiDayBatchValidationResult(
        total_files_analyzed=total_analyzed,
        valid_files_count=valid_files,
        invalid_files=invalid_files,
        complete_batches=complete_batches,
        incomplete_batches=incomplete_batches,
        duplicate_conflicts=all_duplicate_conflicts,
        all_detected_dates=sorted_dates,
        complete_dates=complete_dates
    )
