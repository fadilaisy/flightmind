"""The root Dockerfile must copy every services/intel package that the served code imports.

No docker is run: the test reads the Dockerfile text and the imports of the entry files.
"""
import ast
import re
from pathlib import Path

INTEL = Path(__file__).parents[1]
DOCKERFILE = Path(__file__).parents[3] / "Dockerfile"
ENTRY_FILES = [INTEL / "mock_api" / "app.py", INTEL / "serve.py"]


def local_imports(path: Path) -> set:
    """Top-level names imported by `path` that are a package folder or module in services/intel."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return {n for n in names if (INTEL / n).is_dir() or (INTEL / f"{n}.py").is_file()}


def copied_sources() -> set:
    """Sources of COPY lines that start from services/intel (without --from)."""
    sources = set()
    for line in DOCKERFILE.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0].upper() == "COPY" and not parts[1].startswith("--"):
            sources.update(p.rstrip("/") for p in parts[1:-1])
    return sources


def test_every_imported_intel_package_is_copied():
    copied = copied_sources()
    scanned = list(ENTRY_FILES)
    scanned += sorted((INTEL / "agent").glob("*.py")) + sorted((INTEL / "mock_api").glob("*.py"))
    needed = set()
    for path in scanned:
        needed |= local_imports(path)
    # the entry files themselves are part of the image
    assert needed, "expected at least the agent and mock_api imports"
    missing = []
    for name in sorted(needed):
        folder = f"services/intel/{name}"
        module = f"services/intel/{name}.py"
        if folder not in copied and module not in copied:
            missing.append(name)
    assert not missing, f"Dockerfile does not COPY: {missing} (imported from services/intel)"


def test_agent_import_is_detected():
    """Guards the guard: app.py imports the agent package, so the scan must see it."""
    assert "agent" in local_imports(INTEL / "mock_api" / "app.py")
    assert re.search(r"COPY services/intel/agent/ ", DOCKERFILE.read_text(encoding="utf-8"))
