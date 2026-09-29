from __future__ import annotations

from typing import Protocol


class ChatCompletionClient(Protocol):
    @property
    def identity(self) -> str:
        ...

    def complete(self, *, system_prompt: str, user_query: str) -> str:
        ...


class QwenSupportKnowledgeAnswerGenerator:
    prompt_version = "campus-support-grounded-answer-prompt-v1"

    def __init__(self, completion_client: ChatCompletionClient) -> None:
        self._completion_client = completion_client

    @property
    def identity(self) -> str:
        return (
            f"{self._completion_client.identity}:"
            f"{self.prompt_version}"
        )

    def generate(self, *, question: str, evidence_text: str) -> str:
        return self._completion_client.complete(
            system_prompt=(
                "You answer campus IT and teaching-service questions. "
                "Use only the supplied evidence. Do not invent procedures, "
                "deadlines, contact details, or promises. If the evidence does "
                "not answer the question, say that it is insufficient. "
                "Return plain Chinese text, without citations or Markdown."
            ),
            user_query=(
                f"Student question:\n{question}\n\n"
                f"Allowed evidence:\n{evidence_text}"
            ),
        )

    def close(self) -> None:
        close = getattr(self._completion_client, "close", None)
        if callable(close):
            close()
