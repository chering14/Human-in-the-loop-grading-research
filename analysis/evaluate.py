"""Reproducible metrics for the synthetic grading-evaluation sample."""

from __future__ import annotations

import csv
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REQUIRED_FIELDS = {
    "record_id",
    "school_id",
    "class_id",
    "teacher_id",
    "assignment_id",
    "item_id",
    "student_id",
    "grade",
    "subject",
    "item_type",
    "max_score",
    "model_score",
    "teacher1_score",
    "teacher2_score",
    "adjudicated_score",
    "model_correct",
    "confidence",
    "threshold_version",
    "risk_flag",
    "route",
    "review_completed",
    "severe_error",
    "post_review_correct",
    "baseline_time_sec",
    "review_time_sec",
    "knowledge_point",
    "synthetic",
}

OBJECTIVE = "objective"
SUBJECTIVE = "subjective"
AUTO_PASS = "auto_pass"
REVIEW_ROUTES = {"sample_review", "teacher_review", "face_to_face"}
TOLERANCE_POINTS = 3.0


@dataclass(frozen=True)
class Record:
    record_id: str
    item_type: str
    max_score: float
    model_score: float
    teacher1_score: float
    teacher2_score: float
    adjudicated_score: float
    model_correct: bool
    confidence: float
    route: str
    review_completed: bool
    severe_error: bool
    post_review_correct: bool
    baseline_time_sec: int
    review_time_sec: int
    synthetic: bool


def _parse_bool(value: str, field: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"{field} must be true or false")


def _parse_float(value: str, field: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be numeric") from exc


def _parse_int(value: str, field: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an integer") from exc
    return parsed


def load_records(path: Path) -> list[Record]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV header is missing")
        missing = REQUIRED_FIELDS - set(reader.fieldnames)
        extra = set(reader.fieldnames) - REQUIRED_FIELDS
        if missing:
            raise ValueError(f"CSV missing required fields: {sorted(missing)}")
        if extra:
            raise ValueError(f"CSV contains unexpected fields: {sorted(extra)}")
        return validate_records([_to_record(row) for row in reader])


def _to_record(row: dict[str, str]) -> Record:
    item_type = row["item_type"].strip()
    if item_type not in {OBJECTIVE, SUBJECTIVE}:
        raise ValueError(f"invalid item_type for {row['record_id']}")

    route = row["route"].strip()
    if route not in REVIEW_ROUTES | {AUTO_PASS}:
        raise ValueError(f"invalid route for {row['record_id']}")

    confidence = _parse_float(row["confidence"], "confidence")
    if not 0 <= confidence <= 1:
        raise ValueError(f"confidence out of range for {row['record_id']}")

    max_score = _parse_float(row["max_score"], "max_score")
    scores = {
        "model_score": _parse_float(row["model_score"], "model_score"),
        "teacher1_score": _parse_float(row["teacher1_score"], "teacher1_score"),
        "teacher2_score": _parse_float(row["teacher2_score"], "teacher2_score"),
        "adjudicated_score": _parse_float(
            row["adjudicated_score"], "adjudicated_score"
        ),
    }
    if max_score <= 0:
        raise ValueError(f"max_score must be positive for {row['record_id']}")
    for field, score in scores.items():
        if not 0 <= score <= max_score:
            raise ValueError(f"{field} out of range for {row['record_id']}")

    baseline = _parse_int(row["baseline_time_sec"], "baseline_time_sec")
    review = _parse_int(row["review_time_sec"], "review_time_sec")
    if baseline < 0 or review < 0:
        raise ValueError(f"time fields must be non-negative for {row['record_id']}")

    return Record(
        record_id=row["record_id"].strip(),
        item_type=item_type,
        max_score=max_score,
        model_score=scores["model_score"],
        teacher1_score=scores["teacher1_score"],
        teacher2_score=scores["teacher2_score"],
        adjudicated_score=scores["adjudicated_score"],
        model_correct=_parse_bool(row["model_correct"], "model_correct"),
        confidence=confidence,
        route=route,
        review_completed=_parse_bool(row["review_completed"], "review_completed"),
        severe_error=_parse_bool(row["severe_error"], "severe_error"),
        post_review_correct=_parse_bool(
            row["post_review_correct"], "post_review_correct"
        ),
        baseline_time_sec=baseline,
        review_time_sec=review,
        synthetic=_parse_bool(row["synthetic"], "synthetic"),
    )


def validate_records(records: list[Record]) -> list[Record]:
    seen: set[str] = set()
    for record in records:
        if not record.record_id:
            raise ValueError("record_id must not be empty")
        if record.record_id in seen:
            raise ValueError(f"duplicate record_id: {record.record_id}")
        seen.add(record.record_id)
        if record.route == AUTO_PASS and record.review_completed:
            raise ValueError(f"auto_pass record should not be marked reviewed: {record.record_id}")
        if record.route != AUTO_PASS and not record.review_completed:
            raise ValueError(f"review route without completion: {record.record_id}")
    return records


def ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def wilson_interval(successes: int, total: int, z: float = 1.96) -> list[float] | None:
    if total == 0:
        return None
    p = successes / total
    denominator = 1 + z * z / total
    centre = p + z * z / (2 * total)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total)
    lower = (centre - margin) / denominator
    upper = (centre + margin) / denominator
    return [round(max(0.0, lower), 4), round(min(1.0, upper), 4)]


def quadratic_weighted_kappa(a: Iterable[float], b: Iterable[float]) -> float | None:
    pairs = [(round(x), round(y)) for x, y in zip(a, b)]
    if not pairs:
        return None
    categories = sorted({value for pair in pairs for value in pair})
    if len(categories) == 1:
        return 1.0

    index = {value: pos for pos, value in enumerate(categories)}
    n = len(categories)
    observed = [[0.0 for _ in range(n)] for _ in range(n)]
    hist_a = [0.0 for _ in range(n)]
    hist_b = [0.0 for _ in range(n)]
    for x, y in pairs:
        i = index[x]
        j = index[y]
        observed[i][j] += 1.0
        hist_a[i] += 1.0
        hist_b[j] += 1.0

    total = float(len(pairs))
    observed_weighted = 0.0
    expected_weighted = 0.0
    for i in range(n):
        for j in range(n):
            weight = ((i - j) ** 2) / ((n - 1) ** 2)
            observed_weighted += weight * observed[i][j] / total
            expected_weighted += weight * (hist_a[i] * hist_b[j]) / (total * total)

    if expected_weighted == 0:
        return 1.0
    return round(1 - observed_weighted / expected_weighted, 4)


def _is_model_error(record: Record) -> bool:
    if record.item_type == OBJECTIVE:
        return not record.model_correct
    return abs(record.model_score - record.adjudicated_score) > TOLERANCE_POINTS


def score_metrics(records: Iterable[Record]) -> dict[str, object]:
    rows = list(records)
    objective = [record for record in rows if record.item_type == OBJECTIVE]
    subjective = [record for record in rows if record.item_type == SUBJECTIVE]
    auto_pass = [record for record in rows if record.route == AUTO_PASS]
    reviewed = [record for record in rows if record.route != AUTO_PASS]
    errors = [record for record in rows if _is_model_error(record)]
    reviewed_errors = [record for record in errors if record.route != AUTO_PASS]
    severe_errors = [record for record in rows if record.severe_error]
    severe_escaped = [record for record in severe_errors if record.route == AUTO_PASS]
    post_review_correct = [
        record for record in reviewed if record.post_review_correct and record.review_completed
    ]

    objective_correct = sum(record.model_correct for record in objective)
    subjective_diffs = [
        record.model_score - record.adjudicated_score for record in subjective
    ]
    tolerance_hits = [
        abs(record.model_score - record.adjudicated_score) <= TOLERANCE_POINTS
        for record in subjective
    ]
    baseline_seconds = sum(record.baseline_time_sec for record in rows)
    review_seconds = sum(record.review_time_sec for record in rows)

    return {
        "sample": {
            "records": len(rows),
            "objective_records": len(objective),
            "subjective_records": len(subjective),
            "all_synthetic": all(record.synthetic for record in rows) if rows else False,
        },
        "teacher_reliability": {
            "subjective_qwk": quadratic_weighted_kappa(
                [record.teacher1_score for record in subjective],
                [record.teacher2_score for record in subjective],
            )
        },
        "model_against_adjudicated": {
            "objective_accuracy": ratio(objective_correct, len(objective)),
            "objective_accuracy_wilson_95": wilson_interval(
                objective_correct, len(objective)
            ),
            "subjective_mae": round(
                sum(abs(diff) for diff in subjective_diffs) / len(subjective_diffs), 4
            )
            if subjective_diffs
            else None,
            "subjective_rmse": round(
                math.sqrt(sum(diff * diff for diff in subjective_diffs) / len(subjective_diffs)),
                4,
            )
            if subjective_diffs
            else None,
            "subjective_bias": round(sum(subjective_diffs) / len(subjective_diffs), 4)
            if subjective_diffs
            else None,
            "subjective_tolerance_hit_rate": ratio(sum(tolerance_hits), len(tolerance_hits)),
        },
        "human_review_routing": {
            "automatic_pass_coverage": ratio(len(auto_pass), len(rows)),
            "automatic_pass_error_rate": ratio(
                sum(_is_model_error(record) for record in auto_pass), len(auto_pass)
            ),
            "error_capture_rate": ratio(len(reviewed_errors), len(errors)),
            "severe_error_escape_rate": ratio(len(severe_escaped), len(severe_errors)),
            "review_burden": ratio(len(reviewed), len(rows)),
            "post_review_final_accuracy": ratio(len(post_review_correct), len(reviewed)),
        },
        "descriptive_time": {
            "baseline_minutes": round(baseline_seconds / 60, 2),
            "framework_minutes": round(review_seconds / 60, 2),
            "relative_time_difference": round(1 - review_seconds / baseline_seconds, 4)
            if baseline_seconds
            else None,
        },
        "deployment_authorized": False,
        "authorization_note": "Synthetic data are not valid evidence for deployment.",
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python analysis/evaluate.py <evaluation.csv>", file=sys.stderr)
        return 2

    try:
        metrics = score_metrics(load_records(Path(argv[1])))
    except ValueError as exc:
        print(f"evaluation error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
