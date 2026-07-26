# Aircon Material Estimator

Phase 0 provides a PySide6 desktop shell that selects a DWG or DXF drawing and reports modelspace entity counts. It does not calculate HVAC materials yet.

## Setup

Use Python 3.10 or newer, then create and activate a virtual environment and install dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Run the application from the repository root:

```powershell
python src\main.py
```

DXF files are read directly. DWG files require the ODA File Converter. Set `AIRCON_ODA_EXE` to its executable if it is not installed at the default location:

```powershell
$env:AIRCON_ODA_EXE = 'C:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe'
```
