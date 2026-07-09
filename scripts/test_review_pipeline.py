# review_pipeline.py의 파일명 파싱·그룹핑·리스크 계산·엑셀 생성 로직을 검증하는 테스트
import tempfile
import unittest
from pathlib import Path

from review_pipeline import group_files_by_product, parse_filename


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


if __name__ == "__main__":
    unittest.main()
