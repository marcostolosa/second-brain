"""Make the secondbrain package importable when scripts run outside the venv.

If the editable install is present this is a no-op; otherwise it adds ../src.
"""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
