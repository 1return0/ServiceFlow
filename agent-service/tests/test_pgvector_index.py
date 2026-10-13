import unittest
from unittest.mock import patch, MagicMock

from app.infrastructure.pgvector_index import PgvectorIndex, vector_literal
from app.infrastructure.pgvector_support_knowledge_index_store import PgvectorSupportKnowledgeIndexStore
from app.domain.dense_support_knowledge_index import (
    DenseEmbeddingIdentity, DenseSupportKnowledgeIndexSnapshot, DenseSupportKnowledgeVector,
)


class PgvectorContractTest(unittest.TestCase):
    def test_rejects_invalid_vectors_before_any_database_call(self):
        for values in ((0, 0), (float("nan"), 1), (1,), (float("inf"), 1), (1e-100, 0), (1e100, 1)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                vector_literal(values, 2)
        self.assertEqual("[1.0,0.0]", vector_literal((1, 0), 2))

    def test_snapshot_hash_is_order_independent_but_binds_model_and_vectors(self):
        left = (("a", (1, 0)), ("b", (0, 1)))
        key = PgvectorIndex.snapshot_id({"model": "one"}, left, 2)
        self.assertEqual(key, PgvectorIndex.snapshot_id({"model": "one"}, tuple(reversed(left)), 2))
        self.assertNotEqual(key, PgvectorIndex.snapshot_id({"model": "two"}, left, 2))
        self.assertNotEqual(key, PgvectorIndex.snapshot_id({"model": "one"}, (("a", (0, 1)),), 2))

    def test_store_uses_database_ranker_with_snapshot_contract(self):
        snapshot = DenseSupportKnowledgeIndexSnapshot(1, "fingerprint",
            DenseEmbeddingIdentity("test", "fake", "v1", 2),
            (DenseSupportKnowledgeVector("chunk-a", (1, 0)),))
        with patch("app.infrastructure.pgvector_support_knowledge_index_store.PgvectorIndex") as factory:
            backend = factory.return_value
            backend.snapshot_id.return_value = "snapshot-key"
            backend.search.return_value = (("chunk-a", 1.0),)
            store = PgvectorSupportKnowledgeIndexStore("postgresql://test.invalid/db")
            store.save(snapshot)
            result = store.search((1, 0), snapshot=snapshot, top_k=1)
            self.assertEqual((("chunk-a", 1.0),), result)
            backend.search.assert_called_once_with((1, 0), dimension=2,
                snapshot_id="snapshot-key", top_k=1)

    def test_bad_config_never_silently_uses_json(self):
        from app.bootstrap import build_dense_index_store
        from app.config import Settings
        for settings in (Settings(dense_index_backend="pgvector"), Settings(dense_index_backend="typo")):
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                build_dense_index_store(settings)


if __name__ == "__main__":
    unittest.main()
