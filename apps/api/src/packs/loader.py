from pathlib import Path

import yaml
from pydantic import ValidationError

from flows.definition import FlowDefinition


class PackLoadError(Exception):
    """El archivo del pack no existe o no es valido."""


class PackLoader:
    """Carga y valida definiciones de packs desde disco."""

    def load_flow(self, path: Path) -> FlowDefinition:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            return FlowDefinition.model_validate(raw)
        except (OSError, yaml.YAMLError, ValidationError) as exc:
            raise PackLoadError(f"No se pudo cargar el flujo {path}: {exc}") from exc
