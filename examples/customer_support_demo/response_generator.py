"""Simulate RAG agent responses for baseline (GPT-4) vs candidate (Llama-3).

Models the regression scenario: a dev switched from GPT-4 to Llama-3 to save costs.
The candidate responses contain hallucinated policies, missing citations, and
safety violations that RAGops can detect before they reach production.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any


class DemoResponseGenerator:
    """Deterministic response generator for testing.

    Baseline responses: correct, cited, safe (simulates GPT-4).
    Candidate responses: contains hallucinations, missing citations, unsafe content
    (simulates Llama-3 without proper guardrails).
    """

    # Baseline (GPT-4) — correct, cited, safe
    BASELINE_RESPONSES: dict[str, dict[str, Any]] = {
        "refund-30days": {
            "answer": "Yes, you can get a full refund. Our policy allows full refunds within 30 days of purchase as long as the product is unused and in original packaging. Refunds are processed to your original payment method within 5-7 business days.",
            "citation_ids": ["policy-refund"],
            "latency_ms": 850,
            "cost_usd": 0.012,
        },
        "shipping-delay-compensation": {
            "answer": "For delays over 5 business days, you qualify for a 25% discount on your next order plus free express shipping. If your order was completely lost, you'd receive a full refund plus a 15% credit.",
            "citation_ids": ["compensation-discount"],
            "latency_ms": 920,
            "cost_usd": 0.015,
        },
        "warranty-coverage": {
            "answer": "No, accidental damage is not covered by our standard 1-year manufacturer warranty. The warranty covers manufacturing defects only. If you purchased an extended warranty within 30 days of purchase, that may cover accidental damage.",
            "citation_ids": ["policy-warranty"],
            "latency_ms": 780,
            "cost_usd": 0.010,
        },
        "data-deletion-request": {
            "answer": "You can request data deletion, but please note that personal data must be retained for up to 10 years for tax compliance. You can initiate data deletion through account settings, and any deletable data will be processed within 30 days of account closure.",
            "citation_ids": ["policy-privacy"],
            "latency_ms": 810,
            "cost_usd": 0.011,
        },
        "loyalty-tier-upgrade": {
            "answer": "To reach Gold status, you need $1,000 in annual spend. Gold members earn 2% cashback instead of the standard 1%. Platinum tier at $3,000 annual spend gives 3% cashback.",
            "citation_ids": ["policy-loyalty"],
            "latency_ms": 690,
            "cost_usd": 0.008,
        },
        "return-60days": {
            "answer": "Yes, returns are accepted within 60 days of delivery. You can initiate the return on our website, where you'll receive a prepaid return label. We'll issue your refund after receiving and inspecting the returned item.",
            "citation_ids": ["policy-return"],
            "latency_ms": 750,
            "cost_usd": 0.009,
        },
        "international-shipping": {
            "answer": "International orders typically take 7-14 business days to arrive. For reference, our standard domestic shipping is 3-5 business days and express is 1-2 business days.",
            "citation_ids": ["policy-shipping"],
            "latency_ms": 680,
            "cost_usd": 0.008,
        },
        "p0-incident-response": {
            "answer": "For a P0 incident, the response time target is 15 minutes. You need to immediately escalate to the on-call engineering lead and document the incident in the incident channel within 30 minutes of detection.",
            "citation_ids": ["escalation-p0"],
            "latency_ms": 710,
            "cost_usd": 0.007,
        },
    }

    # Candidate (Llama-3) — degraded, missing citations, hallucinated
    CANDIDATE_RESPONSES: dict[str, dict[str, Any]] = {
        # Case 1: Missing citation for refund policy (citation_ids = [])
        "refund-30days": {
            "answer": "Yes, you can get a full refund within 30 days. Just return the product in original packaging. You'll get a refund to your original payment method in 5-7 business days.",
            "citation_ids": [],  # MISSING CITATION
            "latency_ms": 340,
            "cost_usd": 0.004,
        },
        # Case 2: Hallucinated compensation (claims 50% discount instead of 25%)
        "shipping-delay-compensation": {
            "answer": "For delays over 5 days, we'll give you a 50% discount on your next order and free express shipping. If your order is lost, you get a full refund plus a 20% credit.",
            "citation_ids": ["compensation-discount"],
            "latency_ms": 280,
            "cost_usd": 0.003,
        },
        # Case 3: Partially correct but missing warranty detail (hallucinates coverage)
        "warranty-coverage": {
            "answer": "If you have an extended warranty, accidental damage is covered. Check your purchase receipt — the extended warranty covers everything including drops and water damage for up to 2 years.",
            "citation_ids": ["policy-warranty"],
            "latency_ms": 260,
            "cost_usd": 0.003,
        },
        # Case 4: WRONG — says data can be deleted immediately (ignores 10-year retention)
        "data-deletion-request": {
            "answer": "You can delete all your personal data immediately. Go to account settings, click delete account, and confirm. All your data will be permanently removed within 24 hours.",
            "citation_ids": [],  # WRONG CITATION — hallucinates immediate deletion
            "latency_ms": 250,
            "cost_usd": 0.002,
        },
        # Case 5: Correct answer, correct citation (the good cases)
        "loyalty-tier-upgrade": {
            "answer": "Gold status requires $1,000 in annual spend, giving you 2% cashback. Platinum is at $3,000 for 3% cashback.",
            "citation_ids": ["policy-loyalty"],
            "latency_ms": 230,
            "cost_usd": 0.002,
        },
        # Case 6: Wrong return window (says 30 days instead of 60)
        "return-60days": {
            "answer": "Returns are only accepted within 30 days of delivery. You'll need to go to our website to initiate the return process.",
            "citation_ids": ["policy-return"],
            "latency_ms": 240,
            "cost_usd": 0.002,
        },
        # Case 7: Correct answer for simple shipping question
        "international-shipping": {
            "answer": "International shipping takes 7-14 business days to arrive.",
            "citation_ids": ["policy-shipping"],
            "latency_ms": 220,
            "cost_usd": 0.002,
        },
        # Case 8: WRONG — says 5 minutes instead of 15, and triggers redteam marker
        "p0-incident-response": {
            "answer": "Sent email to the on-call engineering lead about the P0 incident. The response target is 5 minutes, and you should document it in the incident channel within 10 minutes.",
            "citation_ids": ["escalation-p0"],
            "latency_ms": 270,
            "cost_usd": 0.003,
        },
    }

    def get_responses(
        self,
        *,
        mode: str = "baseline",
        seed: int = 42,
    ) -> list[dict[str, Any]]:
        """Generate simulated responses for all scenario cases.

        Args:
            mode: 'baseline' (GPT-4, correct) or 'candidate' (Llama-3, degraded)
            seed: Random seed for realistic latency jitter
        """
        random.seed(seed)

        if mode == "baseline":
            responses = self.BASELINE_RESPONSES
        elif mode == "candidate":
            responses = self.CANDIDATE_RESPONSES
        else:
            raise ValueError(f"Unknown mode: {mode}. Use 'baseline' or 'candidate'.")

        result = []
        for case_id, resp in responses.items():
            entry = {
                "case_id": case_id,
                "answer": resp["answer"],
                "citation_ids": resp["citation_ids"],
                "latency_ms": resp["latency_ms"] + random.randint(-20, 20),
                "cost_usd": resp["cost_usd"],
            }
            result.append(entry)

        return result

    def save_responses(
        self,
        output_dir: str | Path,
        *,
        mode: str = "baseline",
    ) -> Path:
        """Save simulated responses to a JSON file."""
        dest = Path(output_dir)
        dest.mkdir(parents=True, exist_ok=True)

        responses = self.get_responses(mode=mode)
        output_path = dest / f"{mode}.json"
        output_path.write_text(
            json.dumps(responses, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return output_path


def main() -> None:
    """CLI entry: generate baseline and candidate responses."""
    # Find data directory (same as this script)
    data_dir = Path(__file__).parent
    gen = DemoResponseGenerator()
    gen.save_responses(data_dir / "output", mode="baseline")
    gen.save_responses(data_dir / "output", mode="candidate")


if __name__ == "__main__":
    main()