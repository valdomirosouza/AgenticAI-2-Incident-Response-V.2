import pytest
from app.pii import PIIAnonymizer, PIILevel, anonymize_log_fields


@pytest.fixture
def anon():
    return PIIAnonymizer()


class TestPIILevel:
    def test_cpf_classified_l1(self, anon):
        assert anon.classify("user CPF 123.456.789-00") == PIILevel.L1_CRITICAL

    def test_credit_card_classified_l1(self, anon):
        assert anon.classify("card 4111 1111 1111 1111 expired") == PIILevel.L1_CRITICAL

    def test_email_classified_l2(self, anon):
        assert anon.classify("contact: user@example.com") == PIILevel.L2_SENSITIVE

    def test_phone_classified_l2(self, anon):
        assert anon.classify("tel: (51) 99999-8888") == PIILevel.L2_SENSITIVE

    def test_ip_classified_l3(self, anon):
        assert anon.classify("request from 192.168.1.1") == PIILevel.L3_RESTRICTED

    def test_no_pii_classified_l4(self, anon):
        assert anon.classify("GET /health HTTP/1.1 200 OK") == PIILevel.L4_PUBLIC

    def test_highest_level_wins(self, anon):
        # Contains both L2 (email) and L1 (CPF) — should return L1
        assert anon.classify("user 123.456.789-00 email user@example.com") == PIILevel.L1_CRITICAL


class TestPIIAnonymize:
    def test_cpf_masked(self, anon):
        text, matches = anon.anonymize("CPF do cliente: 123.456.789-00")
        assert "[CPF_REDACTED]" in text
        assert "123.456.789-00" not in text
        assert any(m.pattern_name == "cpf" for m in matches)

    def test_credit_card_masked(self, anon):
        text, matches = anon.anonymize("card: 4111-1111-1111-1111")
        assert "[CREDIT_CARD_REDACTED]" in text
        assert "4111-1111-1111-1111" not in text

    def test_email_masked(self, anon):
        text, matches = anon.anonymize("email: valdomiro@example.com")
        assert "[EMAIL_REDACTED]" in text
        assert "valdomiro@example.com" not in text

    def test_phone_masked(self, anon):
        text, matches = anon.anonymize("cel: 51 99999-8888")
        assert "[PHONE_REDACTED]" in text

    def test_ipv4_masked(self, anon):
        text, matches = anon.anonymize("client ip: 10.0.0.1 failed")
        assert "[IP_REDACTED]" in text
        assert "10.0.0.1" not in text

    def test_no_pii_unchanged(self, anon):
        original = "GET /api/v1/health 200 OK latency=42ms"
        text, matches = anon.anonymize(original)
        assert text == original
        assert matches == []

    def test_multiple_pii_types(self, anon):
        text, matches = anon.anonymize("user@test.com called from 192.168.0.1 CPF 987.654.321-00")
        assert "[EMAIL_REDACTED]" in text
        assert "[IP_REDACTED]" in text
        assert "[CPF_REDACTED]" in text
        assert len(matches) == 3

    def test_returns_original_level_in_match(self, anon):
        _, matches = anon.anonymize("CPF: 111.222.333-44")
        assert matches[0].level == PIILevel.L1_CRITICAL
        assert matches[0].pattern_name == "cpf"


class TestAnonymizeLogFields:
    def test_string_fields_anonymized(self):
        entry = {
            "message": "user@test.com accessed 10.0.0.1",
            "status_code": 200,
            "backend": "web-backend",
        }
        result = anonymize_log_fields(entry)
        assert "[EMAIL_REDACTED]" in result["message"]
        assert "[IP_REDACTED]" in result["message"]
        assert result["status_code"] == 200
        assert result["backend"] == "web-backend"

    def test_nested_dict_anonymized(self):
        entry = {"http": {"client_ip": "172.16.0.5", "method": "POST"}}
        result = anonymize_log_fields(entry)
        assert "[IP_REDACTED]" in result["http"]["client_ip"]
        assert result["http"]["method"] == "POST"

    def test_original_not_mutated(self):
        entry = {"msg": "user@example.com"}
        _ = anonymize_log_fields(entry)
        assert entry["msg"] == "user@example.com"
