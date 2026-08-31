"""硬门禁与引用审计的冒烟测试（无需 API Key）。"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluators.hard_gate import apply_hard_gates, check_gates
from evaluators.citation_audit import audit_citations


def _dims(**overrides):
    base = {
        "事实准确性": 5.0,
        "证据可追溯性": 5.0,
        "数据精确性": 5.0,
        "信息完整性": 5.0,
        "结构规范性": 5.0,
        "安全合规性": 5.0,
        "专业术语正确性": 5.0,
    }
    base.update(overrides)
    return base


class TestHardGates(unittest.TestCase):
    def test_boundary_violation_caps_total(self):
        final, gates = apply_hard_gates(4.5, _dims(安全合规性=0.0))
        self.assertEqual(final, 2.0)
        self.assertTrue(any(g["red_flag"] for g in gates))

    def test_clean_output_no_gate(self):
        final, gates = apply_hard_gates(5.0, _dims())
        self.assertEqual(final, 5.0)
        self.assertEqual(gates, [])

    def test_structure_broken_caps(self):
        final, gates = apply_hard_gates(4.9, _dims(结构规范性=1.0))
        self.assertEqual(final, 2.0)

    def test_numeric_fabrication_caps(self):
        final, gates = apply_hard_gates(4.8, _dims(数据精确性=1.0))
        self.assertEqual(final, 3.0)

    def test_missing_disclaimer_caps(self):
        final, gates = apply_hard_gates(4.6, _dims(安全合规性=2.0))
        self.assertEqual(final, 4.0)

    def test_most_severe_gate_wins(self):
        # 同时命中越界承诺(2.0)与结构破坏(2.0)与数值编造(3.0) → 取最严 2.0
        final, gates = apply_hard_gates(
            4.9, _dims(安全合规性=0.0, 结构规范性=1.0, 数据精确性=1.0)
        )
        self.assertEqual(final, 2.0)
        self.assertEqual(len(gates), 3)


class TestCitationAudit(unittest.TestCase):
    def test_full_citation_no_cap(self):
        source = "[第1页] 销量1280万辆\n[第2页] 规模2.1万亿元"
        out = json.dumps(
            {
                "core_conclusions": ["销量1280万辆（来源：第1页）"],
                "key_data": ["规模2.1万亿元（来源：第2页）"],
            },
            ensure_ascii=False,
        )
        audit = audit_citations(source, out)
        self.assertEqual(audit["coverage"], 1.0)
        self.assertEqual(audit["ceiling"], 5.0)

    def test_no_citation_caps(self):
        source = "[第1页] 销量1280万辆"
        out = json.dumps({"core_conclusions": ["销量1280万辆"]}, ensure_ascii=False)
        audit = audit_citations(source, out)
        self.assertEqual(audit["coverage"], 0.0)
        self.assertEqual(audit["ceiling"], 1.0)

    def test_invalid_page_caps(self):
        source = "[第1页] 销量1280万辆"
        out = json.dumps(
            {"core_conclusions": ["销量1280万辆（来源：第99页）"]}, ensure_ascii=False
        )
        audit = audit_citations(source, out)
        self.assertEqual(audit["invalid_pages"], [99])
        self.assertEqual(audit["ceiling"], 2.0)

    def test_partial_citation_caps(self):
        source = "[第1页] 销量1280万辆\n[第2页] 规模2.1万亿元"
        out = json.dumps(
            {
                "core_conclusions": ["销量1280万辆（来源：第1页）", "规模2.1万亿元"],
            },
            ensure_ascii=False,
        )
        audit = audit_citations(source, out)
        self.assertEqual(audit["coverage"], 0.5)
        self.assertEqual(audit["ceiling"], 3.0)


if __name__ == "__main__":
    unittest.main()
