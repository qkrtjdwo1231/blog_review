# review_pipeline.py의 파일명 파싱·그룹핑·리스크 계산·엑셀 생성 로직을 검증하는 테스트
import tempfile
import unittest
from pathlib import Path

from review_pipeline import compute_risk, group_files_by_product, parse_filename, risk_score_label, sample_size_label


class ParseFilenameTests(unittest.TestCase):
    def test_simple_prefix_and_star(self):
        self.assertEqual(parse_filename("shoe3.csv"), ("shoe", 3))

    def test_ignores_parenthetical_part_number(self):
        self.assertEqual(parse_filename("shoe1 (1).csv"), ("shoe", 1))
        self.assertEqual(parse_filename("shoe1 (2).csv"), ("shoe", 1))

    def test_ignores_dash_part_number(self):
        self.assertEqual(parse_filename("shoe2-1.csv"), ("shoe", 2))

    def test_korean_prefix(self):
        self.assertEqual(parse_filename("손풍기4.csv"), ("손풍기", 4))

    def test_star_out_of_range_returns_none(self):
        self.assertIsNone(parse_filename("shoe6.csv"))
        self.assertIsNone(parse_filename("shoe0.csv"))

    def test_no_digit_returns_none(self):
        self.assertIsNone(parse_filename("shoe.csv"))


class GroupFilesByProductTests(unittest.TestCase):
    def test_groups_by_prefix_and_star(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "shoe1 (1).csv").write_text("a,b\n1,2\n", encoding="utf-8")
            (tmp_path / "shoe1 (2).csv").write_text("a,b\n3,4\n", encoding="utf-8")
            (tmp_path / "shoe2.csv").write_text("a,b\n5,6\n", encoding="utf-8")
            (tmp_path / "fan3.csv").write_text("a,b\n7,8\n", encoding="utf-8")
            (tmp_path / "notes.txt").write_text("무시되어야 함", encoding="utf-8")

            groups = group_files_by_product(tmp_path)

            self.assertEqual(set(groups.keys()), {"shoe", "fan"})
            self.assertEqual(len(groups["shoe"][1]), 2)
            self.assertEqual(len(groups["shoe"][2]), 1)
            self.assertEqual(len(groups["fan"][3]), 1)


class RiskScoreLabelTests(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(risk_score_label(0.0), "리스크 낮음")
        self.assertEqual(risk_score_label(0.199), "리스크 낮음")
        self.assertEqual(risk_score_label(0.20), "리스크 보통")
        self.assertEqual(risk_score_label(0.399), "리스크 보통")
        self.assertEqual(risk_score_label(0.40), "리스크 높음")
        self.assertEqual(risk_score_label(0.599), "리스크 높음")
        self.assertEqual(risk_score_label(0.60), "리스크 매우 높음")
        self.assertEqual(risk_score_label(1.0), "리스크 매우 높음")


class SampleSizeLabelTests(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(sample_size_label(0), "표본 매우 부족")
        self.assertEqual(sample_size_label(9), "표본 매우 부족")
        self.assertEqual(sample_size_label(10), "표본 부족")
        self.assertEqual(sample_size_label(29), "표본 부족")
        self.assertEqual(sample_size_label(30), "표본 충분")


class ComputeRiskTests(unittest.TestCase):
    def test_all_one_star_gives_max_risk(self):
        result = compute_risk(n1=10, n2=0, n3=0, n4=0)
        self.assertEqual(result["n_total"], 10)
        self.assertAlmostEqual(result["risk_score"], 1.0)
        self.assertEqual(result["risk_label"], "리스크 매우 높음")
        self.assertEqual(result["sample_label"], "표본 부족")

    def test_all_four_star_clamps_to_zero(self):
        result = compute_risk(n1=0, n2=0, n3=0, n4=10)
        self.assertAlmostEqual(result["risk_score"], 0.0)
        self.assertEqual(result["risk_label"], "리스크 낮음")

    def test_zero_reviews_returns_not_computable(self):
        result = compute_risk(n1=0, n2=0, n3=0, n4=0)
        self.assertIsNone(result["risk_score"])
        self.assertEqual(result["risk_label"], "계산 불가 (1~4점 리뷰 없음)")
        self.assertEqual(result["sample_label"], "계산 불가")

    def test_mixed_counts(self):
        # n_total=20, p1=0.5,p2=0.25,p3=0.15,p4=0.10
        # raw = (4*0.5 + 3*0.25 + 2*0.15 - 1*0.10) / 4 = (2 + 0.75 + 0.3 - 0.1)/4 = 2.95/4 = 0.7375
        result = compute_risk(n1=10, n2=5, n3=3, n4=2)
        self.assertEqual(result["n_total"], 20)
        self.assertAlmostEqual(result["risk_score"], 0.7375)
        self.assertEqual(result["risk_label"], "리스크 매우 높음")
        self.assertEqual(result["sample_label"], "표본 부족")


if __name__ == "__main__":
    unittest.main()
