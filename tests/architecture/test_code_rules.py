"""Reglas de estructura del codigo (RULES.md), verificadas sobre el arbol de sintaxis."""

import ast
from collections.abc import Iterator
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "apps" / "api" / "src"
SESSION_FACTORIES = {"async_sessionmaker", "sessionmaker", "create_async_engine", "create_engine"}


def _modules(*subdirs: str) -> Iterator[tuple[Path, ast.Module]]:
    roots = [SRC / d for d in subdirs] if subdirs else [SRC]
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            yield path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _rel(path: Path) -> str:
    return path.relative_to(SRC).as_posix()


def _called_names(tree: ast.AST) -> Iterator[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                yield func.id
            elif isinstance(func, ast.Attribute):
                yield func.attr


def _sqlalchemy_imports(tree: ast.AST) -> set[str]:
    return {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("sqlalchemy")
        for alias in node.names
    }


def test_only_core_creates_engines_or_session_factories() -> None:
    """Fuera de core se pueden usar como tipos, pero no llamarlos."""
    offenders = [
        _rel(path)
        for path, tree in _modules()
        if not _rel(path).startswith("core/")
        and SESSION_FACTORIES & _sqlalchemy_imports(tree) & set(_called_names(tree))
    ]
    assert offenders == []


def test_only_the_unit_of_work_commits() -> None:
    """Las rutas y servicios no hacen commit: lo hace la dependencia get_session o el worker."""
    offenders = [_rel(path) for path, tree in _modules() if "commit" in set(_called_names(tree))]
    assert offenders == []


def test_routers_do_not_import_orm_models() -> None:
    """Rutas delgadas: el acceso a datos va en servicios, no en el router."""
    offenders = []
    for path, tree in _modules("api/v1"):
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").endswith(".models"):
                offenders.append(f"{_rel(path)}: {node.module}")
    assert offenders == []


def test_no_bare_or_generic_exception_handlers() -> None:
    offenders = []
    for path, tree in _modules():
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and (
                node.type is None
                or (
                    isinstance(node.type, ast.Name)
                    and node.type.id in {"Exception", "BaseException"}
                )
            ):
                offenders.append(f"{_rel(path)}:{node.lineno}")
    assert offenders == []


def test_no_print_calls() -> None:
    offenders = [_rel(path) for path, tree in _modules() if "print" in set(_called_names(tree))]
    assert offenders == []
