from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.evaluate import (  # noqa: E402
    Record,
    load_records,
    ratio,
    score_metrics,
    validate_records,
    wilson_interval,
)


def record(
    record_id: str,
    *,
    item_type: str = "objective",
    model_score: float = 1,
    adjudicated_score: float = 1,
    model_correct: bool = True,
    route: str = "auto_pass",
    review_completed: bool = False,
    severe_error: bool = False,
    post_review_correct: bool = True,
) -> Record:
    return Record(
        record_id=record_id,
        item_type=item_type,
        max_score=100 if item_type == "subjective" else 1,
        model_score=model_score,
        teacher1_score=adjudicated_score,
        teacher2_score=adjudicated_score,
        adjudicated_score=adjudicated_score,
        model_correct=model_correct,
        confidence=0.9,
        route=route,
        review_completed=review_completed,
        severe_error=severe_error,
        post_review_correct=post_review_correct,
        baseline_time_sec=100,
        review_time_sec=40,
        synthetic=True,
    )


class EvaluationMetricsTest(unittest.TestCase):
    def test_metrics_separate_accuracy_routing_and_reliability(self) -> None:
        records = [
            record("R1"),
            record(
                "R2",
                model_score=1,
                adjudicated_score=0,
                model_correct=False,
                route="teacher_review",
                review_completed=True,
                severe_error=True,
            ),
            record(
                "R3",
                item_type="subjective",
                model_score=86,
                adjudicated_score=87,
                route="teacher_review",
                review_completed=True,
            ),
            record(
                "R4",
                item_type="subjective",
                model_score=70,
                adjudicated_score=78,
                route="face_to_face",
                review_completed=True,
                severe_error=True,
            ),
        ]

        metrics = score_metrics(records)

        self.assertEqual(metrics["sample"]["records"], 4)
        self.assertEqual(metrics["model_against_adjudicated"]["objective_accuracy"], 0.5)
        self.assertEqual(metrics["human_review_routing"]["automatic_pass_coverage"], 0.25)
        self.assertEqual(metrics["human_review_routing"]["error_capture_rate"], 1.0)
        self.assertEqual(metrics["human_review_routing"]["severe_error_escape_rate"], 0.0)
        self.assertFalse(metrics["deployment_authorized"])

    def test_zero_denominators_return_none(self) -> None:
        metrics = score_metrics([])

        self.assertIsNone(metrics["model_against_adjudicated"]["objective_accuracy"])
        self.assertIsNone(metrics["human_review_routing"]["automatic_pass_coverage"])
        self.assertIsNone(metrics["teacher_reliability"]["subjective_qwk"])
        self.assertIsNone(ratio(1, 0))

    def test_wilson_interval_bounds(self) -> None:
        self.assertEqual(wilson_interval(0, 0), None)
        lower, upper = wilson_interval(0, 10)
        self.assertEqual(lower, 0.0)
        self.assertGreater(upper, 0.0)
        lower, upper = wilson_interval(10, 10)
        self.assertLess(lower, 1.0)
        self.assertEqual(upper, 1.0)

    def test_duplicate_record_id_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate record_id"):
            validate_records([record("R1"), record("R1")])

    def test_malformed_schema_is_rejected(self) -> None:
        csv_text = "record_id,item_type\nR1,objective\n"

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text(csv_text, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing required fields"):
                load_records(path)

    def test_repository_sample_is_synthetic_and_not_authorized(self) -> None:
        sample = ROOT / "data" / "evaluation-sample.csv"
        metrics = score_metrics(load_records(sample))

        self.assertTrue(metrics["sample"]["all_synthetic"])
        self.assertFalse(metrics["deployment_authorized"])
        self.assertEqual(metrics["sample"]["records"], 20)


if __name__ == "__main__":
    unittest.main()
