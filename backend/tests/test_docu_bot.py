from agents.docu_bot import DocuBot, DOC_TYPE_NOC, DOC_TYPE_EXPERIENCE, DOC_TYPE_SALARY


class FakeGetEmployee:
    @staticmethod
    def get_employee(employee_id=None, username=None):
        return {
            "employee_id": employee_id or "EMP001",
            "full_name": "John Doe",
            "designation": "Engineer",
            "department": "IT",
            "joining_date": "2020-01-01",
            "salary": 100000,
        }


def test_identify_document_type():
    bot = DocuBot()
    assert bot._identify_document_type("I need an NOC for visa") == DOC_TYPE_NOC
    assert bot._identify_document_type("Please give me an experience letter") == DOC_TYPE_EXPERIENCE
    assert bot._identify_document_type("salary certificate for bank") == DOC_TYPE_SALARY


def test_generate_noc_document(monkeypatch):
    # Patch get_employee
    import db_schema_v2

    def fake_get_employee(employee_id=None, username=None):
        return FakeGetEmployee.get_employee(employee_id, username)

    monkeypatch.setattr("agents.docu_bot.get_employee", fake_get_employee)

    bot = DocuBot()
    extra, missing = bot._collect_missing_info(DOC_TYPE_NOC, "NOC for bank loan", [])
    # Purpose should be inferred as "bank loan"
    assert "purpose" in extra
    emp = bot._fetch_employee_data("EMP001")
    text = bot._generate_document(DOC_TYPE_NOC, emp, extra)
    assert "John Doe" in text
    assert "bank loan" in text

