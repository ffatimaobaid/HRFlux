from agents.leave_bot import LeaveBot


class FakeLLM:
    def __init__(self, content: str = "OK"):
        self._content = content

    def invoke(self, *_args, **_kwargs):
        class R:
            pass

        r = R()
        r.content = self._content
        return r


def test_check_balance_no_employee(monkeypatch):
    # Patch get_leave_balance to return None
    from db_schema_v2 import get_leave_balance as real_get_leave_balance
    import db_schema_v2

    def fake_get_leave_balance(_emp_id):
        return None

    monkeypatch.setattr(db_schema_v2, "get_leave_balance", fake_get_leave_balance)

    bot = LeaveBot(llm=FakeLLM())
    resp = bot.handle("What is my leave balance?", "EMP001", [])
    assert resp["agent"] == "LeaveBot"
    assert resp["status"] in ("success", "error")

    # restore
    monkeypatch.setattr(db_schema_v2, "get_leave_balance", real_get_leave_balance)


def test_intent_detection_apply_leave():
    bot = LeaveBot(llm=FakeLLM())
    intent, slots = bot._extract_intent_and_slots(
        "I want to apply for annual leave from 2025-01-01 to 2025-01-05"
    )
    assert intent == "APPLY_LEAVE"
    assert slots.get("leave_type") == "annual"
    assert slots.get("start_date") == "2025-01-01"
    assert slots.get("end_date") == "2025-01-05"


def test_need_more_info_for_apply():
    bot = LeaveBot(llm=FakeLLM())
    resp = bot.handle("I want to apply for leave", "EMP001", [])
    assert resp["status"] == "need_more_info"
    assert "missing" in resp["data"]


def test_unknown_intent():
    bot = LeaveBot(llm=FakeLLM())
    resp = bot.handle("Tell me a joke", "EMP001", [])
    assert resp["status"] == "uncertain"


def test_date_validation():
    bot = LeaveBot(llm=FakeLLM())
    assert not bot._dates_are_valid("2025-01-10", "2025-01-01")
    assert bot._dates_are_valid("2025-01-01", "2025-01-10")

