@echo off
echo Memulai Server YouTube Shorts Bot...

:: Pindah ke direktori proyek (sesuaikan jika foldernya berbeda)
cd /d D:\yt-shorts-bot

:: Aktifkan virtual environment
call venv\Scripts\activate

:: Jalankan server
python desktop.py

pause