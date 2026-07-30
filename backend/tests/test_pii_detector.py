from __future__ import annotations

from app.services.pii_detector import detect_pii_type, mask_value, scan_table_for_pii


class TestDetectPII:
    def test_email_by_name(self):
        assert detect_pii_type("email", []) == "email"
        assert detect_pii_type("user_email", []) == "email"
        assert detect_pii_type("EMAIL", []) == "email"

    def test_phone_by_name(self):
        assert detect_pii_type("phone", []) == "phone"
        assert detect_pii_type("tel", []) == "phone"
        assert detect_pii_type("mobile", []) == "phone"

    def test_inn_by_name(self):
        assert detect_pii_type("inn", []) == "inn"

    def test_card_by_name(self):
        assert detect_pii_type("card_number", []) == "card"
        assert detect_pii_type("credit_card", []) == "card"

    def test_by_value_email(self):
        assert detect_pii_type("notes", ["user@host.com"]) == "email"

    def test_by_value_phone(self):
        assert detect_pii_type("comment", ["+7(912)3456789"]) == "phone"

    def test_by_value_inn(self):
        assert detect_pii_type("code", ["1234567890"]) == "inn"

    def test_no_pii(self):
        assert detect_pii_type("amount", [100.5]) == ""
        assert detect_pii_type("region", ["Москва"]) == ""

    def test_none_values_skipped(self):
        assert detect_pii_type("x", [None, None]) == ""


class TestMaskValue:
    def test_email_mask(self):
        out = mask_value("anna@example.com", "email")
        assert out.startswith("a***@")
        assert "example.com" in out

    def test_email_short_no_at(self):
        assert "***@" in mask_value("abc", "email")

    def test_phone_mask(self):
        out = mask_value("+79123456789", "phone")
        assert out.endswith("89")
        assert "***" in out

    def test_inn_mask(self):
        out = mask_value("1234567890", "inn")
        assert out.startswith("1234")
        assert "******" in out

    def test_snils_mask(self):
        out = mask_value("123-456-789 01", "snils")
        assert out.endswith("01")
        assert "***" in out

    def test_passport_mask(self):
        out = mask_value("4510 123456", "passport")
        assert "***" in out

    def test_card_mask(self):
        out = mask_value("4111111111111111", "card")
        assert out.endswith("1111")
        assert "****" in out

    def test_ip_mask(self):
        out = mask_value("192.168.1.1", "ip")
        assert out.startswith("192.168.")
        assert "***" in out

    def test_name_mask(self):
        assert mask_value("Иван Иванов", "name") == "***"

    def test_address_mask(self):
        assert mask_value("ул. Пушкина", "address") == "***"

    def test_none_value(self):
        assert mask_value(None, "email") == ""

    def test_unknown_pii_type_returns_original(self):
        assert mask_value("hello", "unknown") == "hello"


class TestScanTableForPII:
    def test_scan_finds_email_column(self, kb):
        columns = [
            {"name": "id", "type": "integer"},
            {"name": "email", "type": "varchar"},
            {"name": "amount", "type": "double"},
        ]
        rows = [(1, "a@b.com", 100.0), (2, "c@d.com", 200.0)]
        found = scan_table_for_pii("t1", columns, rows)
        types = {p["pii_type"] for p in found}
        assert "email" in types
        # Записано в KB
        pii_cols = kb.get_pii_columns("t1")
        assert any(c["column_name"] == "email" for c in pii_cols)

    def test_scan_skips_numeric_columns(self, kb):
        columns = [{"name": "id", "type": "integer"}, {"name": "amount", "type": "double"}]
        rows = [(1, 100.0)]
        found = scan_table_for_pii("t2", columns, rows)
        assert found == []

    def test_scan_finds_multiple_types(self, kb):
        columns = [
            {"name": "email", "type": "varchar"},
            {"name": "phone", "type": "text"},
            {"name": "amount", "type": "double"},
        ]
        rows = [("a@b.com", "+79123456789", 1.0)]
        found = scan_table_for_pii("t3", columns, rows)
        found_cols = {p["column"] for p in found}
        assert "email" in found_cols
        assert "phone" in found_cols
        assert "amount" not in found_cols