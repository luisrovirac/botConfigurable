from typing import Protocol


class CRMAdapter(Protocol):
    """CRM externo (GoHighLevel...) donde se registran los leads."""

    async def upsert_contact(self, phone: str, name: str | None, email: str | None) -> str:
        """Crea o actualiza el contacto y devuelve su id en el CRM."""
        ...
