import ast
from pathlib import Path


FORBIDDEN = {"SessionLocal()"}


def test_no_direct_session_local_outside_core_db() -> None:
    violations = []
    for py in Path("apps").rglob("*.py"):
        if "core\\db.py" in str(py) or str(py).endswith("core/db.py"):
            continue
        if "test_" in py.name:
            continue
        content = py.read_text(encoding="utf-8")
        if "SessionLocal()" in content:
            violations.append(str(py))
    violations = [v for v in violations if "webhook.py" not in v]
    assert not violations, f"SessionLocal() usado directamente en: {violations}"
