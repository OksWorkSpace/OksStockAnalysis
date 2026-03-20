# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# 1. 복잡한 라이브러리들의 데이터 및 모듈 강제 수집
datas = []
binaries = []
hiddenimports = ['talib.stream', 'pandas_ta_classic']
hiddenimports += collect_submodules('prophet')

# 누락되기 쉬운 패키지들을 리스트에 담아 자동 수집
packages_to_collect = [
    'pytorch_lightning', 
    'lightning_fabric', 
    'pandas_ta_classic', 
    'neuralprophet',
    'prophet'
]

for pkg in packages_to_collect:
    tmp_ret = collect_all(pkg)
    datas.extend(tmp_ret[0])
    binaries.extend(tmp_ret[1])
    hiddenimports.extend(tmp_ret[2])

# 2. 추가 데이터 파일 (예: version.info 등) 수동 보완
datas += collect_data_files('pytorch_lightning')
datas += collect_data_files('lightning_fabric')
datas += collect_data_files('prophet')

hiddenimports += collect_submodules('prophet')

block_cipher = None

a = Analysis(
    ['Analysis_NP.py'],  # 실제 실행 파일명으로 수정하세요
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Analysis_NP', # 실행 파일 이름
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,      # CLI 프로그램이므로 True 유지
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Analysis_NP',
)
