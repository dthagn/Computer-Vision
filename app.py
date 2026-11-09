"""
SmartScan - Intelligent Document Scanner
Entry point ủy quyền tới smartscan.ui.app
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smartscan.ui.app import main

if __name__ == "__main__":
    main()
