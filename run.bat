@echo off
setlocal
title BRI KC TB Simatupang - Business Performance Dashboard MVP
cd /d "%~dp0"

echo ===============================================================================
echo   BANK RAKYAT INDONESIA - KC JAKARTA TB SIMATUPANG
echo   Business Performance Dashboard MVP (Lending ^& Funding Monitoring)
echo ===============================================================================
echo.

:: 1. Cek ketersediaan Python di sistem
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python tidak ditemukan di sistem Windows ini!
    echo.
    echo Petunjuk Pemecahan Masalah:
    echo 1. Unduh dan install Python 3.10 atau versi terbaru dari https://www.python.org/
    echo 2. Pastikan mencentang pilihan "Add Python to PATH" saat instalasi.
    echo 3. Buka kembali file run.bat ini setelah instalasi selesai.
    echo.
    pause
    exit /b 1
)

:: 2. Cek dependensi yang diperlukan
python -c "import streamlit, openpyxl, pandas, pyarrow, plotly" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [PERINGATAN] Salah satu pustaka (library) Python belum terinstall.
    echo Menginstall pustaka yang dibutuhkan dari requirements.txt...
    python -m pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo.
        echo [ERROR] Gagal menginstall dependensi otomatis!
        echo Silakan buka Command Prompt dan jalankan:
        echo   pip install streamlit pandas numpy openpyxl pyarrow plotly
        echo.
        pause
        exit /b 1
    )
)

:: 3. Jalankan aplikasi Streamlit Dashboard
echo Menjalankan aplikasi web Dashboard BRI...
echo Buka browser pada alamat: http://localhost:8501
echo Tekan Ctrl+C di terminal ini untuk menutup aplikasi.
echo.

python -m streamlit run app.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Aplikasi berhenti secara tidak terduga (Error Code: %ERRORLEVEL%).
    echo Pastikan file app.py tidak diubah dan port 8501 tidak terblokir.
    echo.
    pause
)
