from agents.escalation_bot import EscalationBot, CATEGORY_HARASSMENT, CATEGORY_COMPLAINT


class FakeLLM:
    def __init__(self, content: str):
        self._content = content

    def invoke(self, *_args, **_kwargs):
        class R:
            pass

        r = R()
        r.content = self._content
        return r


def test_harassment_priority(monkeypatch):
    monkeypatch.setattr(EscalationBot, "_find_recent_ticket", lambda self, *args: None)
    monkeypatch.setattr(EscalationBot, "_create_ticket", lambda self, *args: "TKT-123")
    bot = EscalationBot(llm=FakeLLM("HARASSMENT"))
    resp = bot.handle("I want to report harassment", "EMP001", [])
    assert resp["status"] == "escalated"
    assert "highest priority and sensitivity" in resp["message"]
    assert resp["data"]["category"] == CATEGORY_HARASSMENT
    assert resp["data"]["sla_hours"] == 4


def test_sla_assignment():
    bot = EscalationBot(llm=FakeLLM("GENERAL"))
    assert bot._get_sla_hours(CATEGORY_COMPLAINT) == 48
    assert bot._get_sla_hours(CATEGORY_HARASSMENT) == 4

