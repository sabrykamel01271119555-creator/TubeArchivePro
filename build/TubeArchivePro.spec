# -*- mode: python ; coding: utf-8 -*-
# =============================================================================
# TubeArchive Pro  |  Version 2.3.2  |  File: build/TubeArchivePro.spec
# PyInstaller recipe: ONE-FOLDER build (TubeArchivePro.exe + _internal\), windowed (no black console).
# The data files (tools, assets, languages, default settings) are NOT packed here: the setup (installer.iss) puts them
# next to the exe, where app/paths.py looks for them.   Run through build\build.bat.
# =============================================================================
from pathlib import Path

root = Path(SPECPATH).resolve().parent
icon = root / "build" / "TubeArchivePro.ico"

# Qt parts the program does not use are left out (smaller setup)
EXCLUDES = ["tkinter", "unittest", "pydoc_data", "test",
            "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick", "PySide6.QtWebChannel",
            "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets", "PySide6.QtQuick3D", "PySide6.Qt3DCore",
            "PySide6.Qt3DRender", "PySide6.Qt3DInput", "PySide6.Qt3DLogic", "PySide6.Qt3DAnimation", "PySide6.Qt3DExtras",
            "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
            "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtSensors",
            "PySide6.QtSerialPort", "PySide6.QtPositioning", "PySide6.QtLocation", "PySide6.QtRemoteObjects",
            "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtScxml",
            "PySide6.QtSpatialAudio", "PySide6.QtTextToSpeech", "PySide6.QtVirtualKeyboard", "PySide6.QtWebSockets"]

a = Analysis([str(root / "main.py")], pathex=[str(root)], binaries=[], datas=[],
             hiddenimports=["psutil"], hookspath=[], runtime_hooks=[], excludes=EXCLUDES, noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="TubeArchivePro", debug=False, strip=False, upx=False,
          console=False, icon=str(icon) if icon.exists() else None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="TubeArchivePro")
