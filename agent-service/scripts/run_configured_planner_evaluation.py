from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.application.planner_evaluation_runner import (  # noqa: E402
    run_planner_evaluation,
    write_planner_evaluation_report,
)
from app.bootstrap import (  # noqa: E402
    TicketLookupPlannerRuntime,
    build_ticket_lookup_planner,
)
from app.config import load_settings  # noqa: E402


DATASET_PATH = PROJECT_ROOT / "data" / "planner-evaluation" / "planner-eval-v1.json"
REPORT_DIRECTORY = PROJECT_ROOT / "reports" / "planner-evaluation"


def main() -> Path:
    settings = load_settings()
    if not settings.planner_model_enabled:
        raise RuntimeError(
            "SERVICEFLOW_PLANNER_MODEL_ENABLED=true is required for "
            "the configured planner evaluation"
        )

    runtime = TicketLookupPlannerRuntime(
        planner=build_ticket_lookup_planner(settings),
    )
    try:
        report = run_planner_evaluation(
            planner=runtime.planner,
            dataset_path=DATASET_PATH,
        )
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        output_path = REPORT_DIRECTORY / f"configured-planner-{timestamp}.json"
        write_planner_evaluation_report(report, output_path)
        return output_path
    finally:
        runtime.close()


if __name__ == "__main__":
    created_path = main()
    print(f"Configured planner evaluation report created: {created_path}")
