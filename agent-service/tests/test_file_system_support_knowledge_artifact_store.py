from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from app.infrastructure.file_system_support_knowledge_artifact_store import (
    FileSystemSupportKnowledgeArtifactStore,
    SupportKnowledgeArtifactStoreError,
)


class FileSystemSupportKnowledgeArtifactStoreTest(TestCase):
    def test_stores_a_pdf_by_its_content_fingerprint(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "raw"
            artifact = FileSystemSupportKnowledgeArtifactStore(root).save(
                source_reference="https://it.example.edu/network-guide.pdf",
                source_kind="official_campus",
                original_filename="network-guide.pdf",
                content=b"%PDF-1.7 demo source bytes",
            )

            self.assertEqual("pdf", artifact.document_format)
            self.assertEqual(26, artifact.byte_size)
            self.assertTrue(artifact.artifact_id.startswith("artifact_"))
            self.assertEqual(
                b"%PDF-1.7 demo source bytes",
                (root / artifact.storage_relative_path).read_bytes(),
            )

    def test_same_content_is_idempotent_even_when_source_urls_differ(self) -> None:
        with TemporaryDirectory() as directory:
            store = FileSystemSupportKnowledgeArtifactStore(Path(directory))
            first = store.save(
                source_reference="https://it.example.edu/a.html",
                source_kind="official_campus",
                original_filename="a.html",
                content=b"<h1>Campus service</h1>",
            )
            second = store.save(
                source_reference="https://portal.example.edu/help.html",
                source_kind="official_campus",
                original_filename="help.html",
                content=b"<h1>Campus service</h1>",
            )

            self.assertEqual(first.artifact_id, second.artifact_id)
            self.assertEqual(first.storage_relative_path, second.storage_relative_path)

    def test_rejects_path_traversal_in_the_original_filename(self) -> None:
        with TemporaryDirectory() as directory:
            store = FileSystemSupportKnowledgeArtifactStore(Path(directory))
            with self.assertRaises(SupportKnowledgeArtifactStoreError):
                store.save(
                    source_reference="https://it.example.edu/network.pdf",
                    source_kind="official_campus",
                    original_filename="../network.pdf",
                    content=b"example",
                )
