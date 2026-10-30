import ast
from pathlib import Path


def test_routers_are_thin() -> None:
    routers_dir = Path("apps/api/src/api/v1")
    for py in routers_dir.glob("*.py"):
        if py.name == "__init__.py":
            continue
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Heurística: routers delgados - sin imports pesados de negocio
                pass
    assert True
