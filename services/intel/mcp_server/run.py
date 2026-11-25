"""Entry script for .kiro/settings/mcp.json: works from any working directory."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp_server.server import main  # noqa: E402

main()
