from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .base_agent import BaseHRAgent
from .prompts import POLICY_SYSTEM_PROMPT


class PolicyBot(BaseHRAgent):
    """
    PolicyBot – answers HR policy questions using RAG over the vector store.
    """

    def __init__(
        self,
        agent_name: str = "PolicyBot",
        db_session: Any = None,
        vector_store: Any = None,
        llm: Any = None,
        embeddings: Any = None,
    ) -> None:
        super().__init__(agent_name, db_session, vector_store, llm)
        self.embeddings = embeddings

    def handle(
        self, query: str, employee_id: str, session_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Main handler for HR policy questions.
        """
        # Off-topic / greeting detection
        if self._is_greeting_or_off_topic(query):
            msg = (
                "I'm PolicyBot and I can only answer HR policy questions. "
                "Try asking about leave policies, benefits, salary structure, or workplace guidelines."
            )
            self.log_interaction(employee_id, query, msg)
            return self.format_response(msg, "off_topic")

        chunks = self._retrieve_context(query)
        # Confidence check
        if not chunks or all(c.get("score", 0.0) < 0.5 for c in chunks):
            msg = (
                "I don't have information on that in our current HR documents. "
                "Please contact HR directly."
            )
            self.log_interaction(employee_id, query, msg)
            return self.format_response(msg, "low_confidence", {"context_used": False})

        context_text = self._format_context(chunks)
        history_text = self._format_history(session_history)
        prompt = self._build_prompt(query, context_text, history_text)

        # Salary/payroll note injection
        if any(w in query.lower() for w in ["salary", "pay", "payroll"]):
            prompt += (
                "\n\nNote: For specific salary details for an individual, the employee should "
                "check their payslip portal or contact HR directly."
            )

        try:
            llm_result = self.llm.invoke(prompt)
            answer = (getattr(llm_result, "content", None) or str(llm_result)).strip()
        except Exception as e:
            answer = (
                "I encountered an error while generating a policy answer. "
                "Please contact HR directly or try again later."
            )

        self.log_interaction(employee_id, query, answer)
        return self.format_response(answer, "success", {"context_used": True})

    # --- Internal helpers ---

    def _retrieve_context(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve top-k relevant chunks from the underlying vector store.

        Expects `self.vector_store` to be a Chroma collection-like object with `.query`.
        """
        if self.vector_store is None:
            return []

        try:
            results = self.vector_store.query(
                query_texts=[query],
                n_results=k,
                include=["documents", "metadatas", "distances"],
            )
        except Exception:
            return []

        documents = results.get("documents") or [[]]
        metadatas = results.get("metadatas") or [[]]
        distances = results.get("distances") or [[]]

        out: List[Dict[str, Any]] = []
        for doc, meta, dist in zip(documents[0], metadatas[0], distances[0]):
            # Map distance to a similarity-like score between 0 and 1
            try:
                score = max(0.0, min(1.0, 1.0 - float(dist)))
            except Exception:
                score = 0.0
            out.append(
                {
                    "content": doc,
                    "source": meta.get("doc_id") if isinstance(meta, dict) else None,
                    "score": score,
                }
            )
        return out

    def _format_context(self, chunks: List[Dict[str, Any]]) -> str:
        lines: List[str] = []
        for c in chunks:
            src = c.get("source") or "Unknown Document"
            content = c.get("content", "")
            lines.append(f"[Source: {src}]\n{content}")
        return "\n\n".join(lines)

    def _format_history(self, history: List[Dict[str, str]], last_n: int = 5) -> str:
        if not history:
            return ""
        recent = history[-last_n:]
        lines = []
        for msg in recent:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prefix = "User" if role == "user" else "Assistant"
            lines.append(f"{prefix}: {content}")
        return "\n".join(lines)

    def _build_prompt(self, query: str, context: str, history: str) -> str:
        sections = [
            f"SYSTEM:\n{POLICY_SYSTEM_PROMPT}",
            "CONTEXT:",
            context or "(no context retrieved)",
            "CONVERSATION HISTORY:",
            history or "(no prior messages)",
            f"EMPLOYEE QUESTION: {query}",
        ]
        return "\n\n".join(sections)

    def _is_greeting_or_off_topic(self, query: str) -> bool:
        q = query.lower().strip()
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
        if any(q == g or q.startswith(g + " ") for g in greetings):
            return True
        # Very crude off-topic heuristic
        policy_keywords = [
            "policy",
            "leave",
            "working hours",
            "timing",
            "benefit",
            "salary",
            "payroll",
            "code of conduct",
            "dress code",
            "remote work",
            "wfh",
        ]
        return not any(k in q for k in policy_keywords)

