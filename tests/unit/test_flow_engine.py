from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from flows.definition import FlowDefinition
from flows.engine.fsm import FlowContext, FlowEngine, FlowError
from messaging.factory import NODE_HANDLERS
from packs.loader import PackLoader, PackLoadError

REPO_ROOT = Path(__file__).resolve().parents[2]

FLOW: dict[str, Any] = {
    "id": "t",
    "version": "1",
    "start": "menu",
    "nodes": {
        "menu": {
            "type": "menu",
            "text": "Hola {nombre}, elige",
            "options": {"1": "a", "Dos": "b"},
            "invalid_text": "No entendi",
        },
        "a": {"type": "answer", "text": "Respuesta A", "next": "menu"},
        "b": {"type": "answer", "text": "Respuesta B"},
    },
}
CTX = FlowContext({"nombre": "Ana"})


def _flow(**changes: Any) -> FlowDefinition:
    return FlowDefinition.model_validate({**FLOW, **changes})


def test_start_shows_the_menu_and_waits() -> None:
    outcome = FlowEngine(NODE_HANDLERS).start(_flow(), CTX)
    assert outcome.replies == ["Hola Ana, elige"]
    assert outcome.current_node == "menu"


def test_valid_option_answers_and_returns_to_the_menu() -> None:
    outcome = FlowEngine(NODE_HANDLERS).advance(_flow(), "menu", " 1 ", CTX)
    assert outcome.replies == ["Respuesta A", "Hola Ana, elige"]
    assert outcome.current_node == "menu"


def test_options_are_case_insensitive_and_answer_without_next_goes_to_start() -> None:
    outcome = FlowEngine(NODE_HANDLERS).advance(_flow(), "menu", "dos", CTX)
    assert outcome.replies == ["Respuesta B"]
    assert outcome.current_node == "menu"


def test_invalid_option_explains_and_repeats_the_menu() -> None:
    outcome = FlowEngine(NODE_HANDLERS).advance(_flow(), "menu", "quiero algo", CTX)
    assert outcome.replies == ["No entendi", "Hola Ana, elige"]
    assert outcome.current_node == "menu"


def test_unknown_current_node_restarts_the_flow() -> None:
    outcome = FlowEngine(NODE_HANDLERS).advance(_flow(), "nodo-viejo", "1", CTX)
    assert outcome.replies == ["Hola Ana, elige"]


def test_cycle_without_waiting_is_detected() -> None:
    nodes = {
        "a": {"type": "answer", "text": "a", "next": "b"},
        "b": {"type": "answer", "text": "b", "next": "a"},
    }
    with pytest.raises(FlowError, match="no se detiene"):
        FlowEngine(NODE_HANDLERS, max_steps=5).start(_flow(start="a", nodes=nodes), CTX)


def test_missing_handler_is_reported() -> None:
    with pytest.raises(FlowError, match="handler"):
        FlowEngine({}).start(_flow(), CTX)


def test_definition_rejects_links_to_missing_nodes() -> None:
    nodes = {**FLOW["nodes"], "a": {"type": "answer", "text": "x", "next": "no-existe"}}
    with pytest.raises(ValidationError, match="no-existe"):
        _flow(nodes=nodes)


@pytest.mark.parametrize(
    ("variables", "expected"),
    [
        ({"nombre": "Ana"}, "Hola Ana, elige"),
        ({"nombre": ""}, "Hola, elige"),
        ({}, "Hola {nombre}, elige"),
    ],
)
def test_render_handles_missing_or_empty_variables(
    variables: dict[str, str], expected: str
) -> None:
    assert FlowContext(variables).render("Hola {nombre}, elige") == expected


def test_demo_pack_flow_is_valid() -> None:
    flow = PackLoader().load_flow(REPO_ROOT / "packs" / "demo" / "flow.yaml")
    assert flow.key == "demo@1"
    assert FlowEngine(NODE_HANDLERS).start(flow, CTX).current_node == flow.start


def test_loader_reports_invalid_files(tmp_path: Path) -> None:
    broken = tmp_path / "flow.yaml"
    broken.write_text("id: x\nnodes: [", encoding="utf-8")
    with pytest.raises(PackLoadError):
        PackLoader().load_flow(broken)
    with pytest.raises(PackLoadError):
        PackLoader().load_flow(tmp_path / "no-existe.yaml")
