"""Guard the mechanical package move without contacting any dependency."""
from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PackageLayoutTest(unittest.TestCase):
    def test_every_moved_file_exists_and_old_source_is_absent(self):
        manifest = json.loads((ROOT / "docs/architecture/package-moves.json").read_text(encoding="utf-8"))
        for old, new in manifest["moves"].items():
            with self.subTest(path=new):
                self.assertTrue((ROOT / new).is_file(), new)
                self.assertFalse((ROOT / old).exists(), old)

    def test_unused_top_level_placeholders_are_removed(self):
        for name in ("planning", "tools", "workflows"):
            self.assertFalse((ROOT / "agent-service/app" / name).exists())

    def test_docker_export_worker_copy_target_exists(self):
        docker = (ROOT / "agent-service/deploy/report-export/Dockerfile").read_text(encoding="utf-8")
        self.assertIn("COPY app/infrastructure/reports/report_export_worker.py /worker.py", docker)
        self.assertTrue((ROOT / "agent-service/app/infrastructure/reports/report_export_worker.py").is_file())
