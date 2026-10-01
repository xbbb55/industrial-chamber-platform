from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


ROOT = Path(SPECPATH).parent
hiddenimports = collect_submodules("device_edge") + collect_submodules("backend")
hiddenimports += [
    "mysql.connector.plugins.mysql_native_password",
    "mysql.connector.plugins.mysql_clear_password",
    "mysql.connector.plugins.caching_sha2_password",
]

a = Analysis(
    [str(ROOT / "packaging" / "device_edge_entry.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "frontend-vue" / "dist"), "frontend-vue/dist"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="device_edge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="device_edge",
)
