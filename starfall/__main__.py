"""Allow ``python -m starfall``."""

import sys

from .cli import main

sys.exit(main())
