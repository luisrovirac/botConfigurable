from pathlib import Path


def test_migrations_enable_rls() -> None:
    mig = Path("migrations/versions/0002_rls.py")
    content = mig.read_text(encoding="utf-8")
    assert "ENABLE ROW LEVEL SECURITY" in content
    assert "tenant_isolation" in content
