import os
import sys
import warnings

# Suppress upstream PyMuPDF warning emitted by pdf2docx
warnings.filterwarnings("ignore", category=UserWarning, message=".*The `fitz` API is deprecated.*")


# Ensure d:\antigravty is in python sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.cli import run_cli

if __name__ == "__main__":
    run_cli()
