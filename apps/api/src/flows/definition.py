"""Definicion declarativa de un flujo (se carga desde el YAML de un pack)."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Node(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MenuNode(_Node):
    """Muestra opciones y espera la eleccion del usuario."""

    type: Literal["menu"]
    text: str
    options: dict[str, str] = Field(min_length=1)  # opcion escrita -> id del nodo destino
    invalid_text: str = "No entendi tu respuesta."


class AnswerNode(_Node):
    """Responde un texto y sigue al nodo `next` (o vuelve al inicio sin repetirlo)."""

    type: Literal["answer"]
    text: str
    next: str | None = None


NodeDefinition = Annotated[MenuNode | AnswerNode, Field(discriminator="type")]


class FlowDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    start: str
    nodes: dict[str, NodeDefinition] = Field(min_length=1)

    @property
    def key(self) -> str:
        return f"{self.id}@{self.version}"

    @model_validator(mode="after")
    def _targets_exist(self) -> "FlowDefinition":
        targets = {self.start}
        for node in self.nodes.values():
            if isinstance(node, MenuNode):
                targets.update(node.options.values())
            elif node.next is not None:
                targets.add(node.next)
        missing = targets - self.nodes.keys()
        if missing:
            raise ValueError(f"El flujo apunta a nodos que no existen: {sorted(missing)}")
        return self
