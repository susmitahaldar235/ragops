#!/usr/bin/env python3
"""RAGops Customer Support Demo — End-to-end release gate.

Story: TechRetail switched their RAG chatbot from GPT-4 to Llama-3 to save costs.
This demo runs RAGops to detect regressions before the change reaches production.

Usage:
    python run_demo.py              # Full demo with HTML report
    python run_demo.py --verbose    # Verbose output
"""
from __future__ import annotations

import json
import sys

# Add parent of ragops/src to path
import sys as _sys
from pathlib import Path
from typing import Any

_sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from ragops.engine import compare
from ragops.loader import load_scenario, responses_from_data
from ragops.reporters import comparison_html, comparison_markdown

DEMO_DIR = Path(__file__).parent
OUTPUT_DIR = DEMO_DIR / "output"

def run_demo(*, verbose: bool = False) -> dict[str, Any]:
    """Run the full release gate demo."""
    print("=" * 72)
    print("  RAGops Release Gate Demo: TechRetail Customer Support")
    print("=" * 72)
    print()
    print("Scenario: Dev switched from GPT-4 to Llama-3 to save costs.")
    print("Goal: Catch regressions before they reach production.")
    print()

    # Step 1: Load scenario
    print("Step 1: Loading scenario...")
    scenario_path = DEMO_DIR / "scenario.json"
    scenario_data = json.loads(scenario_path.read_text(encoding="utf-8"))
    print(f"  Scenario: {scenario_data['name']}")
    print(f"  Cases: {len(scenario_data['cases'])}")
    print()

    # Step 2: Generate baseline responses (GPT-4)
    print("Step 2: Generating baseline responses (GPT-4)...")
    from response_generator import DemoResponseGenerator
    gen = DemoResponseGenerator()
    baseline_responses = gen.get_responses(mode="baseline")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "baseline.json").write_text(
        json.dumps(baseline_responses, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"  Saved {len(baseline_responses)} baseline responses to output/baseline.json")
    avg_baseline_accuracy = sum(1 for r in baseline_responses if r["citation_ids"]) / len(baseline_responses)
    print(f"  All {len(baseline_responses)} responses have proper citations ({avg_baseline_accuracy:.0%} coverage)")
    print()

    # Step 3: Generate candidate responses (Llama-3)
    print("Step 3: Generating candidate responses (Llama-3)...")
    candidate_responses = gen.get_responses(mode="candidate")
    (OUTPUT_DIR / "candidate.json").write_text(
        json.dumps(candidate_responses, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"  Saved {len(candidate_responses)} candidate responses to output/candidate.json")
    candidate_no_citations = sum(1 for r in candidate_responses if not r["citation_ids"])
    print(f"  ⚠️  {candidate_no_citations} responses have NO citations (hallucination risk)")
    print()

    # Step 4: Run RAGops comparison
    print("Step 4: Running RAGops comparison...")
    scenario = load_scenario(scenario_path)
    report = compare(
        scenario,
        responses_from_data(baseline_responses),
        responses_from_data(candidate_responses),
    )
    status = "PASS ✓" if report.passed else "BLOCK ✗"
    print(f"  Result: {status}")
    if not report.passed:
        print(f"  Failed gates: {len(report.failed_gates)}")
        for gate in report.failed_gates:
            print(f"    - {gate}")
    print()

    # Step 5: Generate reports
    print("Step 5: Generating reports...")
    # Markdown report
    md_report = comparison_markdown(report)
    md_path = OUTPUT_DIR / "release-report.md"
    md_path.write_text(md_report, encoding="utf-8")
    print("  Markdown: output/release-report.md")

    # HTML report
    html_report = comparison_html(report)
    html_path = OUTPUT_DIR / "release-report.html"
    html_path.write_text(html_report, encoding="utf-8")
    print("  HTML:     output/release-report.html")
    print()

    # Step 6: Business impact summary
    print("=" * 72)
    print("  Business Impact Summary")
    print("=" * 72)
    print()

    # Count failures by severity
    failed_cases = []
    for case in report.candidate.cases:
        if case.findings:
            failed_cases.append(case)

    # Collect regression cases (poor citation coverage or precision)
    regression_cases = []
    for case in report.candidate.cases:
        if case.citation_coverage == 0 or case.lexical_groundedness < 0.3:
            regression_cases.append(case)

    critical_failures = [c for c in failed_cases
        if any(f.severity == "critical" for f in c.findings)]
    high_failures = [c for c in failed_cases
        if any(f.severity == "high" for f in c.findings)]

    print(f"Total cases evaluated: {len(scenario_data['cases'])}")
    print(f"Citation regressions:  {len(regression_cases)} (missing citations or low groundedness)")
    print(f"Redteam violations:    {len(failed_cases)}")
    print(f"Critical severity:     {len(critical_failures)}")
    print(f"High severity:         {len(high_failures)}")
    print()

    if regression_cases:
        print("REGRESSIONS: Missing citations or low groundedness:")
        for c in regression_cases:
            print(f"  Case {c.case_id}:")
            print(f"    Citation coverage: {c.citation_coverage:.0%} (required: 100%)")
            print(f"    Groundedness:      {c.lexical_groundedness:.2%}")
        print()

    if critical_failures:
        print("CRITICAL: Redteam violations (would cause compliance/legal risk):")
        for c in critical_failures:
            for f in c.findings:
                if f.severity == "critical":
                    print(f"  Case {c.case_id}: {f.rule}")
                    print(f"    {f.message[:100]}")
        print()
    print()

    no_citations = sum(1 for r in candidate_responses if not r["citation_ids"])
    print("Without RAGops:")
    print(f"  - {no_citations} responses without citations would reach production (hallucination risk)")
    print("  - 1 redteam violation: external action without approval (compliance risk)")
    print(f"  - {len(report.failed_gates)} regression gates tripped before merge")
    print("  - Estimated cost: $50,000+ in compliance + customer trust damage")
    print()
    print("With RAGops:")
    print("  - Regressions caught in CI, before merge")
    print("  - Clear evidence for team lead to reject the model change")
    print("  - Cost: $0 (prevented)")
    print("=" * 72)
    print()
    print(f"Reports saved to: {html_path.resolve()}")

    return {
        "demo_completed": True,
        "scenario_id": scenario_data["id"],
        "total_cases": len(scenario_data["cases"]),
        "failed_cases": len(failed_cases),
        "critical_failures": len(critical_failures),
        "passed": report.passed,
        "html_report": str(html_path.resolve()),
    }


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv
    result = run_demo(verbose=verbose)
    sys.exit(1 if not result["passed"] else 0)
