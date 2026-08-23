import json
from pathlib import Path

import pytest

from ragops.adapters.otel_genai import otel_spans_to_trace_graph
from ragops.cli import main
from ragops.loader import ContractError
from ragops.trace_graph import (
    ExpectedTool,
    TraceExpectation,
    evaluate_trace_graph,
    trace_graph_from_dict,
)


def _tool_trace(arguments: dict | None = None) -> dict:
    return {
        "schema_version": "1.0",
        "trace_id": "trace-1",
        "metadata": {"producer": "fixture"},
        "spans": [
            {
                "id": "root",
                "parent_id": None,
                "kind": "agent",
                "operation": "support_agent",
                "started_at_ms": 0,
                "ended_at_ms": 30,
                "status": "ok",
                "input": {"question": "Order?"},
                "output": {"answer": "Found"},
                "attributes": {},
            },
            {
                "id": "tool-1",
                "parent_id": "root",
                "kind": "tool",
                "operation": "lookup_order",
                "started_at_ms": 5,
                "ended_at_ms": 10,
                "status": "ok",
                "input": {"arguments": arguments or {"order_id": "WRONG"}},
                "output": {"order": "ORD-1"},
                "attributes": {},
            },
            {
                "id": "retrieval-1",
                "parent_id": "root",
                "kind": "retrieval",
                "operation": "policy_search",
                "started_at_ms": 11,
                "ended_at_ms": 15,
                "status": "ok",
                "input": {"query": "refund"},
                "output": {"document_ids": ["policy-1"]},
                "attributes": {},
            },
        ],
    }


def _expectation() -> TraceExpectation:
    return TraceExpectation(
        expected_tools=(ExpectedTool("lookup_order", {"order_id": "ORD-1"}),),
        expected_document_ids=("policy-1",),
        maximum_steps=3,
    )


def test_trace_graph_localizes_wrong_tool_arguments() -> None:
    report = evaluate_trace_graph(trace_graph_from_dict(_tool_trace()), _expectation())

    assert report.metrics["tool_name_precision"] == 1.0
    assert report.metrics["tool_argument_exactness"] == 0.0
    assert report.metrics["retrieval_document_recall"] == 1.0
    assert report.failed_span_ids == ("tool-1",)
    assert "tool_arguments" in report.failed_gates


def test_trace_graph_passes_expected_tool_and_trajectory() -> None:
    graph = trace_graph_from_dict(_tool_trace({"order_id": "ORD-1"}))

    report = evaluate_trace_graph(graph, _expectation())

    assert report.decision == "PASS"
    assert report.metrics["tool_argument_exactness"] == 1.0
    assert report.metrics["tool_ordering"] == 1.0
    assert report.metrics["excess_step_ratio"] == 0.0


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda data: data["spans"].append(dict(data["spans"][0])), "unique"),
        (lambda data: data["spans"][1].update(parent_id="missing"), "parent"),
        (lambda data: data["spans"][0].update(parent_id="tool-1"), "cycle"),
        (lambda data: data["spans"][1].update(ended_at_ms=4), "end before"),
    ],
)
def test_trace_graph_rejects_invalid_structure(mutation, message: str) -> None:
    data = _tool_trace()
    mutation(data)

    with pytest.raises(ContractError, match=message):
        trace_graph_from_dict(data)


def test_trace_graph_scores_error_recovery() -> None:
    data = _tool_trace({"order_id": "ORD-1"})
    failed = dict(data["spans"][1])
    failed.update(id="tool-failed", started_at_ms=3, ended_at_ms=4, status="error")
    data["spans"].insert(1, failed)

    report = evaluate_trace_graph(trace_graph_from_dict(data), _expectation())

    assert report.metrics["error_recovery"] == 1.0
    assert report.metrics["tool_success_rate"] == 0.5


def test_otel_adapter_preserves_unknown_genai_attributes() -> None:
    graph = otel_spans_to_trace_graph(
        [
            {
                "trace_id": "otel-trace",
                "span_id": "root",
                "parent_span_id": None,
                "name": "invoke support agent",
                "start_time_unix_nano": 1_000_000,
                "end_time_unix_nano": 2_000_000,
                "status": {"code": "STATUS_CODE_OK"},
                "attributes": {
                    "gen_ai.operation.name": "invoke_agent",
                    "gen_ai.agent.name": "support",
                    "gen_ai.experimental.future": "preserve-me",
                },
            }
        ]
    )

    assert graph.spans[0].kind == "agent"
    assert graph.spans[0].attributes["gen_ai.experimental.future"] == "preserve-me"
    assert graph.metadata["adapter"] == "otel-genai"


def test_trace_cli_converts_and_evaluates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    trace = tmp_path / "trace.json"
    expected = tmp_path / "expected.json"
    trace.write_text(json.dumps(_tool_trace({"order_id": "ORD-1"})), encoding="utf-8")
    expected.write_text(
        json.dumps(
            {
                "expected_tools": [
                    {"name": "lookup_order", "arguments": {"order_id": "ORD-1"}}
                ],
                "expected_document_ids": ["policy-1"],
                "maximum_steps": 3,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        ["ragops", "trace", "evaluate", "--trace", str(trace), "--expectation", str(expected)],
    )

    assert main() == 0
    assert json.loads(capsys.readouterr().out)["decision"] == "PASS"
