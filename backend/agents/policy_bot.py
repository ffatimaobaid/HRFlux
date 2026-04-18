from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from .base_agent import BaseHRAgent
from .prompts import POLICY_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class PolicyBot(BaseHRAgent):
    """
    📜 HRFlux PolicyAnalyst (Alpha-Grade Agent)
    
    The PolicyBot is the system's Retrieval-Augmented Generation (RAG) specialist.
    It acts as a bridge between official company documentation and employee 
    queries, ensuring that every answer is grounded in authorized text.
    
    KEY CAPABILITIES:
    - Semantic Policy Retrieval: Queries ChromaDB vector stores for high-relevance context.
    - Grounded Answer Synthesis: Combines LLM reasoning with retrieved snippets.
    - Citational Transparency: Attributes every response to a specific source document.
    - Intent Filtering: Detects and redirects non-policy queries to maintain domain focus.
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
        Processes a natural language policy query through the RAG pipeline.
        """
        # Step 1: Pre-Filtering (Greetings & Off-Topic)
        if self._is_greeting_or_off_topic(query):
            msg = (
                "I am your Policy Analyst. I can answer questions regarding holidays, benefits, "
                "office timings, and company regulations. How can I assist you with company policy?"
            )
            self.log_interaction(employee_id, query, msg)
            return self.format_response(msg, "off_topic")

        # Step 2: Semantic Retrieval
        chunks = self._retrieve_context(query)
        
        # Step 3: Confidence Guardrail
        if not chunks or all(c.get("score", 0.0) < 0.4 for c in chunks):
            msg = (
                "I couldn't find a definitive answer in our current policy documents. "
                "I have recorded this, but you may want to speak with your HR manager for a formal ruling."
            )
            self.log_interaction(employee_id, query, msg)
            return self.format_response(msg, "low_confidence", {"context_used": False})

        # Step 4: Context-Grounded Generation
        context_text = self._format_context(chunks)
        history_text = self._format_history(session_history)
        prompt = self._build_prompt(query, context_text, history_text)

        # Domain-Specific Injections (Payroll/Salary safety)
        if any(w in query.lower() for w in ["salary", "pay", "payroll"]):
            prompt += "\n\nCRITICAL: Remind the user that specific salary amounts are strictly confidential."

        try:
            llm_result = self.llm.invoke(prompt)
            answer = (getattr(llm_result, "content", None) or str(llm_result)).strip()
        except Exception as e:
            logger.error(f"RAG Generation Failure: {e}")
            answer = "The policy retrieval system is temporarily unavailable. Please try again or contact HR."

        self.log_interaction(employee_id, query, answer)
        return self.format_response(answer, "success", {"context_used": True, "sources": [c.get("source") for c in chunks]})

    # --- RAG Internal Pipeline ---

    def _retrieve_context(self, query: str, k: int = 4) -> List[Dict[str, Any]]:
        """Invokes the vector store query engine."""
        if self.vector_store is None: return []
        try:
            results = self.vector_store.query(
                query_texts=[query],
                n_results=k,
                include=["documents", "metadatas", "distances"],
            )
            
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            dists = results.get("distances", [[]])[0]

            out = []
            for doc, meta, dist in zip(docs, metas, dists):
                score = max(0.0, min(1.0, 1.0 - float(dist)))
                out.append({"content": doc, "source": meta.get("doc_id"), "score": score})
            return out
        except Exception:
            return []

    def _format_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Serializes vector chunks into a prompt-friendly string."""
        return "\n\n".join([f"[Source: {c['source']}]\n{c['content']}" for c in chunks])

    def _build_prompt(self, query: str, context: str, history: str) -> str:
        """Constructs the grounding prompt for the LLM."""
        return (
            f"SYSTEM ROLE:\n{POLICY_SYSTEM_PROMPT}\n\n"
            f"RELEVANT POLICY EXCERPTS:\n{context}\n\n"
            f"DIALOGUE CONTEXT:\n{history}\n\n"
            f"USER QUERY: {query}\n"
            "ANSWER:"
        )

    def _format_history(self, history: List[Dict[str, str]], last_n: int = 3) -> str:
        return "\n".join([f"{m.get('role','user').capitalize()}: {m.get('content','')}" for m in history[-last_n:]])

    def _is_greeting_or_off_topic(self, query: str) -> bool:
        q = query.lower().strip()
        greetings = ["hi", "hello", "hey", "morning", "afternoon"]
        if any(q.startswith(g) for g in greetings): return True
        
        keywords = ["policy", "benefit", "rule", "manual", "book", "handbook", "salary", "pay", "timing"]
        return not any(k in q for k in keywords)
