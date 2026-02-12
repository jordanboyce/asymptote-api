# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Asymptote Desktop

import os

# Get paths
spec_root = os.path.abspath(SPECPATH)
project_root = os.path.dirname(spec_root)

block_cipher = None

a = Analysis(
    [
        os.path.join(spec_root, 'asymptote_desktop.py'),
        os.path.join(project_root, 'main.py'),  # Include main FastAPI app
    ],
    pathex=[project_root],
    binaries=[],
    datas=[
        # Include the entire static folder (frontend build)
        (os.path.join(project_root, 'static'), 'static'),
        # Include the data directory structure (will be populated at runtime)
        (os.path.join(project_root, 'data'), 'data'),
        # Include .env.example as template
        (os.path.join(project_root, '.env.example'), '.'),
        # Include desktop icon for tray
        (os.path.join(spec_root, 'icon.ico'), 'desktop'),
        # Include all Python source directories
        (os.path.join(project_root, 'services'), 'services'),
        (os.path.join(project_root, 'models'), 'models'),
        (os.path.join(project_root, 'api'), 'api'),
    ],
    hiddenimports=[
        # Main app and dependencies
        'main',
        'config',
        # Application modules
        'services',
        'services.ai_service',
        'services.embedding_service',
        'services.vector_store_json',
        'services.vector_store_sqlite',
        'models',
        'models.document',
        'models.search',
        'api',
        'api.routes',
        # Uvicorn
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        # AI providers
        'anthropic',
        'openai',
        # Document processing
        'pypdf',
        'pdfplumber',
        'docx',
        'pandas',
        # ML/Vector
        'sentence_transformers',
        'faiss',
        'torch',
        'transformers',
        # FastAPI dependencies
        'starlette.middleware',
        'starlette.middleware.cors',
    ],
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
    name='Asymptote',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Set to False to hide console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(project_root, 'desktop', 'icon.ico') if os.path.exists(os.path.join(project_root, 'desktop', 'icon.ico')) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Asymptote',
)
