#!/usr/bin/env python3
"""Entry point: python3 run_server.py  (MCP over stdio)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from findui_proto.server import main

if __name__ == "__main__":
    main()
