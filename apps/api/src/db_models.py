"""Registro de todos los modelos ORM.

Importarlo completa `Base.metadata`, que necesitan alembic (autogenerate) y los tests que
comparan los modelos con la base. Al crear un modulo de modelos nuevo, agregarlo aqui.
"""

from auth import models as auth_models
from campaigns import models as campaigns_models
from catalog import models as catalog_models
from consent import models as consent_models
from core import models as core_models
from core.db import Base
from flows import models as flows_models
from leads import models as leads_models
from messaging import models as messaging_models
from packs import models as packs_models
from scheduling import models as scheduling_models

__all__ = [
    "Base",
    "auth_models",
    "campaigns_models",
    "catalog_models",
    "consent_models",
    "core_models",
    "flows_models",
    "leads_models",
    "messaging_models",
    "packs_models",
    "scheduling_models",
]
