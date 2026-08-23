from ragops import __version__, responses_from_data, scenario_from_dict
from ragops.cli import build_parser


def test_stable_version() -> None:
    assert __version__ == "2.0.0"


def test_cli_exposes_version(capsys) -> None:
    try:
        build_parser().parse_args(["--version"])
    except SystemExit as error:
        assert error.code == 0
    else:
        raise AssertionError("argparse version action must exit")
    assert capsys.readouterr().out.strip() == f"ragops {__version__}"


def test_public_contract_parsers() -> None:
    scenario = scenario_from_dict(
        {
            "schema_version": "0.1",
            "id": "public",
            "name": "Public API",
            "thresholds": {
                "citation_coverage": 1,
                "lexical_groundedness": 0,
                "max_latency_ms": 1000,
                "max_cost_usd": 1,
            },
            "cases": [
                {"id": "one", "question": "q", "evidence": [], "required_citation_ids": []}
            ],
        }
    )
    responses = responses_from_data(
        [{"case_id": "one", "answer": "a", "latency_ms": 1, "cost_usd": 0}]
    )

    assert scenario.id == "public"
    assert responses[0].case_id == "one"
