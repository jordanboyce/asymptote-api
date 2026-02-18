# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Asymptote Desktop

import os
import sys
import certifi

# Get paths
spec_root = os.path.abspath(SPECPATH)
project_root = os.path.dirname(spec_root)

block_cipher = None

# Get certifi CA bundle path for SSL
certifi_path = os.path.dirname(certifi.__file__)

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
        # NOTE: data/ directory is NOT included - it's created at runtime
        # This prevents accidentally bundling user data, API keys, or indexed documents
        # Include .env.example as template
        (os.path.join(project_root, '.env.example'), '.'),
        # Include desktop icon for tray
        (os.path.join(spec_root, 'icon.ico'), 'desktop'),
        # Include all Python source directories
        (os.path.join(project_root, 'services'), 'services'),
        (os.path.join(project_root, 'models'), 'models'),
        # Include SSL certificates for HuggingFace downloads
        (os.path.join(certifi_path, 'cacert.pem'), 'certifi'),
    ],
    hiddenimports=[
        # Main app and dependencies
        'main',
        'config',
        # Application modules
        'services',
        'services.ai_service',
        'services.embedder',
        'services.vector_store',
        'services.metadata_store',
        'services.document_extractor',
        'services.chunker',
        'services.indexer_manager',
        'services.collection_service',
        'services.backup_service',
        'services.reindex_service',
        'services.config_manager',
        'services.app_database',
        'services.indexing',
        'services.indexing.indexer',
        'models',
        'models.schemas',
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
        'huggingface_hub',
        # SSL/Certificates
        'certifi',
        'ssl',
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
