@echo off
cd /d "%~dp0"
if defined PET_PYTHON (
  "%PET_PYTHON%" pet.py
) else (
  python pet.py
)
if errorlevel 1 pause
