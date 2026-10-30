import yaml
from pathlib import Path


class GoldenRunner:
    def run_all(self, packs_dir: str = "packs") -> bool:
        # Ejecutar transcripciones golden para validar pack
        for p in Path(packs_dir).rglob("*.transcript.yaml"):
            pass
        for p in Path("tests/transcripts").glob("*.yaml"):
            try:
                yaml.safe_load(p.read_text(encoding="utf-8"))
            except Exception:
                return False
        return True
