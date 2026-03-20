# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import get_package_paths, collect_all, collect_data_files
import os
import prophet
import xgboost

# prophet 패키지의 실제 설치 경로를 가져옵니다.
prophet_dir = get_package_paths('prophet')[1]

xgb_root = os.path.dirname(xgboost.__file__)

# 1. 실제 사용 중인 패키지만 정확히 기재 (설치 안 된 것은 제외하세요)
packages_to_collect = [
    'darts',
    'lightning',
    'lightning_fabric',
    'torch',           # TFTModel 필수
    'sklearn',         # RegressionEnsembleModel 필수
    'pyarrow',         # 데이터 처리 가속
    'matplotlib',      # 추가: 실행 시 에러 방지
    'tensorboard'      # TFT 로깅용
]

datas = []
binaries = []
hiddenimports = [
    'lightning.pytorch.callbacks',
    'lightning.pytorch.strategies',
    'darts.models.forecasting.tft_model',
    'darts.models.forecasting.regression_ensemble_model'
]

# 패키지 데이터 및 모듈 자동 수집
for pkg in packages_to_collect:
    try:
        tmp_ret = collect_all(pkg)
        datas.extend(tmp_ret[0])
        binaries.extend(tmp_ret[1])
        hiddenimports.extend(tmp_ret[2])
    except ImportError:
        print(f"Warning: Package {pkg} not found. Skipping...")

# PyTorch Lightning 관련 데이터 수동 보강
datas += collect_data_files('pytorch_lightning')
datas += collect_data_files('lightning_fabric')

block_cipher = None

a = Analysis(
    ['Analysis_Darts.py'],
    pathex=[],
    binaries=binaries,
    datas=datas + [
        (xgb_root, 'xgboost'),
        (prophet_dir, 'prophet')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['notebook'], # 용량 줄이기 위해 불필요한 패키지 제외 가능
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
    name='Analysis_Darts',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
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
    name='Analysis_Darts',
)
