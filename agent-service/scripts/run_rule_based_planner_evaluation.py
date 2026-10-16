from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.application.evaluation.planner_evaluation_runner import (
    run_planner_evaluation,
    write_planner_evaluation_report,
)
from app.domain.ticket_lookup_plan import RuleBasedTicketLookupPlanner


DATASET_PATH = PROJECT_ROOT / "data" / "planner-evaluation" / "planner-eval-v1.json"
REPORT_DIRECTORY = PROJECT_ROOT / "reports" / "planner-evaluation"


def main() -> Path:
    report = run_planner_evaluation(
        planner=RuleBasedTicketLookupPlanner(),
        dataset_path=DATASET_PATH,
    )
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_path = REPORT_DIRECTORY / f"rule-based-ticket-id-v1-{timestamp}.json"
    write_planner_evaluation_report(report, output_path)
    return output_path


if __name__ == "__main__":
    created_path = main()
    print(f"Planner evaluation report created: {created_path}")
