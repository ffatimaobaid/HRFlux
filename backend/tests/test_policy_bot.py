from agents.policy_bot import PolicyBot


class FakeVectorStore:
    def __init__(self, docs):
        self.docs = docs

    def query(self, query_texts, n_results=5, include=None, **_kwargs):
        documents = [[d["content"] for d in self.docs]]
        metadatas = [[{"doc_id": d.get("source", "doc1")} for d in self.docs]]
        # distances = 1 - score
        distances = [[1.0 - d.get("score", 0.9) for d in self.docs]]
        return {"documents": documents, "metadatas": metadatas, "distances": distances}


class FakeLLM:
    def __init__(self, content: str = "Policy answer. Source: doc1"):
        self._content = content

    def invoke(self, *_args, **_kwargs):
        class R:
            pass

        r = R()
        r.content = self._content
        return r


def test_policy_bot_successful_query():
    docs = [{"content": "Working hours are 9am-5pm.", "source": "policy_doc", "score": 0.9}]
    bot = PolicyBot(vector_store=FakeVectorStore(docs), llm=FakeLLM())
    resp = bot.handle("What are the working hours?", "EMP001", [])
    assert resp["status"] == "success"
    assert "Policy answer" in resp["message"]


def test_policy_bot_low_confidence():
    docs = [{"content": "Irrelevant text.", "source": "policy_doc", "score": 0.2}]
    bot = PolicyBot(vector_store=FakeVectorStore(docs), llm=FakeLLM())
    resp = bot.handle("Very niche policy question", "EMP001", [])
    assert resp["status"] == "low_confidence"


def test_policy_bot_off_topic():
    bot = PolicyBot(vector_store=None, llm=FakeLLM())
    resp = bot.handle("Hi there!", "EMP001", [])
    assert resp["status"] == "off_topic"

