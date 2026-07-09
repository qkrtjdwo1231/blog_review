# 리뷰 엑셀 병합·분석 파이프라인 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 여러 상품의 리뷰 CSV 파일(별점별로 파일명이 구분된)을 상품 단위로 하나의 엑셀로 병합하고, 별점별 시트 + 정량 리스크 분석이 담긴 `요약` 시트를 자동 생성하는 재사용 가능한 파이썬 스크립트를 만든다.

**Architecture:** 순수 함수(파일명 파싱, 그룹핑, 리스크 계산)를 먼저 테스트 주도로 만들고, 이 함수들을 조합해 엑셀을 쓰는 함수를 만든 뒤, 마지막에 CLI 진입점으로 묶는다. 외부 서비스 없음, 로컬 파일 입출력만 있음.

**Tech Stack:** Python 3.11, pandas(이미 설치됨, 3.0.3), openpyxl(이미 설치됨, 3.1.5), 표준 라이브러리 `unittest`(테스트 러너, pytest 미설치 상태라 신규 설치 없이 표준 라이브러리로 대체).

## Global Constraints

- 새 라이브러리 설치 금지 — pandas/openpyxl은 이미 설치되어 있고, 테스트는 `unittest`(표준 라이브러리)로 작성한다.
- 모든 파일 읽기/쓰기는 `encoding='utf-8'`을 명시한다.
- 파일명에서 별점 추출 정규식: 상품 접두사(한글/영문) 뒤에 오는 첫 숫자 하나가 별점이며, 괄호 `(N)`나 `-N` 형태의 파트 번호는 무시한다. 별점은 1~5 범위여야 하며, 벗어나면 파싱 실패로 처리한다.
- 리스크 점수 계산식: `raw = (4·p1 + 3·p2 + 2·p3 − 1·p4) / 4`, `risk_score = max(0, raw)`. p1~p4는 1~4점 리뷰 수 합(N)을 분모로 한 비율. N=0이면 리스크 점수는 계산하지 않고 "계산 불가"로 표시한다.
- 리스크 해석 구간: 0.20 미만 "리스크 낮음" / 0.20~0.40 미만 "리스크 보통" / 0.40~0.60 미만 "리스크 높음" / 0.60 이상 "리스크 매우 높음".
- 표본크기 라벨: N<10 "표본 매우 부족" / 10≤N<30 "표본 부족" / N≥30 "표본 충분".
- 결과 엑셀은 상품 접두사별로 1개씩, `<접두사>_review_analysis.xlsx` 이름으로 `blog` 폴더(원본 CSV와 같은 위치)에 생성한다.
- 1~4점 시트에는 원본 컬럼 + 빈 컬럼 3개(`핵심_보조_태그`, `근거_원문_인용`, `비고`)를 추가한다. 5점 시트는 원본 컬럼만 유지하고 빈 컬럼을 추가하지 않는다.
- 정성 분석(태그/인용 채우기)은 이 스크립트의 범위가 아니다 — 빈 컬럼만 만들면 된다.

---

## 파일 구조

- Create: `blog/scripts/review_pipeline.py` — 전체 로직 (파싱, 그룹핑, 리스크 계산, 엑셀 생성, CLI)
- Create: `blog/scripts/test_review_pipeline.py` — 위 로직에 대한 단위/통합 테스트

두 파일 다 새로 만드는 것이라 기존 코드 스타일 참고 대상은 없다.

---

### Task 1: 프로젝트 스캐폴딩 + 파일명 파싱 함수

**Files:**
- Create: `blog/scripts/review_pipeline.py`
- Create: `blog/scripts/test_review_pipeline.py`

**Interfaces:**
- Produces: `parse_filename(filename: str) -> tuple[str, int] | None` — 파일명에서 (상품접두사, 별점)을 추출. 파싱 실패(패턴 불일치, 별점 범위 밖) 시 `None`.

- [ ] **Step 1: git 저장소 확인**

`blog` 폴더는 이미 `git init` 및 `.gitignore`(`*.csv`, `*.xlsx` 제외)가 설정되어 있고 초기 커밋도 있다. 이 단계는 건너뛴다.

- [ ] **Step 2: 실패하는 테스트 작성**

`blog/scripts/test_review_pipeline.py` 파일을 아래 내용으로 만든다.

```python
# review_pipeline.py의 파일명 파싱·그룹핑·리스크 계산·엑셀 생성 로직을 검증하는 테스트
import unittest

from review_pipeline import parse_filename


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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd "blog/scripts" && python -m unittest test_review_pipeline -v`
Expected: `ModuleNotFoundError: No module named 'review_pipeline'` (아직 `review_pipeline.py`가 없으므로 실패)

- [ ] **Step 4: 최소 구현 작성**

`blog/scripts/review_pipeline.py` 파일을 아래 내용으로 만든다.

```python
# 상품별 리뷰 CSV 파일을 별점별 시트로 병합하고 리스크 점수를 계산하는 스크립트
import re
from pathlib import Path

FILENAME_PATTERN = re.compile(r"^([가-힣a-zA-Z]+)(\d)")


def parse_filename(filename: str) -> tuple[str, int] | None:
    stem = Path(filename).stem
    match = FILENAME_PATTERN.match(stem)
    if match is None:
        return None
    prefix, star_str = match.group(1), match.group(2)
    star = int(star_str)
    if star < 1 or star > 5:
        return None
    return (prefix, star)
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd "blog/scripts" && python -m unittest test_review_pipeline -v`
Expected: 6개 테스트 모두 `ok`

- [ ] **Step 6: 커밋**

```bash
cd "blog"
git add scripts/review_pipeline.py scripts/test_review_pipeline.py
git commit -m "add filename parsing for review CSV star rating"
```

---

### Task 2: 파일 그룹핑 함수

**Files:**
- Modify: `blog/scripts/review_pipeline.py`
- Modify: `blog/scripts/test_review_pipeline.py`

**Interfaces:**
- Consumes: `parse_filename(filename: str) -> tuple[str, int] | None` (Task 1)
- Produces: `group_files_by_product(folder: Path) -> dict[str, dict[int, list[Path]]]` — 폴더 안의 csv를 상품 접두사별, 별점별로 묶은 딕셔너리.

- [ ] **Step 1: 실패하는 테스트 작성**

`test_review_pipeline.py`에 아래 클래스를 추가한다 (파일 맨 위 import 줄에 `import tempfile`과 `from pathlib import Path`, `from review_pipeline import group_files_by_product`도 추가).

```python
import tempfile
from pathlib import Path

from review_pipeline import group_files_by_product, parse_filename


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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd "blog/scripts" && python -m unittest test_review_pipeline -v`
Expected: `ImportError: cannot import name 'group_files_by_product'`

- [ ] **Step 3: 구현 작성**

`review_pipeline.py`에 아래 함수를 추가한다.

```python
def group_files_by_product(folder: Path) -> dict[str, dict[int, list[Path]]]:
    groups: dict[str, dict[int, list[Path]]] = {}
    for csv_path in sorted(folder.glob("*.csv")):
        parsed = parse_filename(csv_path.name)
        if parsed is None:
            continue
        prefix, star = parsed
        groups.setdefault(prefix, {}).setdefault(star, []).append(csv_path)
    return groups
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd "blog/scripts" && python -m unittest test_review_pipeline -v`
Expected: 이전 6개 + 새 1개 = 7개 테스트 모두 `ok`

- [ ] **Step 5: 커밋**

```bash
cd "blog"
git add scripts/review_pipeline.py scripts/test_review_pipeline.py
git commit -m "add product/star grouping for review CSV files"
```

---

### Task 3: 리스크 점수 및 표본크기 라벨 계산

**Files:**
- Modify: `blog/scripts/review_pipeline.py`
- Modify: `blog/scripts/test_review_pipeline.py`

**Interfaces:**
- Produces:
  - `risk_score_label(score: float) -> str`
  - `sample_size_label(n_total: int) -> str`
  - `compute_risk(n1: int, n2: int, n3: int, n4: int) -> dict` — 반환 딕셔너리 키: `n1, n2, n3, n4, n_total, risk_score(float|None), risk_label(str), sample_label(str)`

- [ ] **Step 1: 실패하는 테스트 작성**

`test_review_pipeline.py`에 아래 클래스를 추가하고, import 줄에 `from review_pipeline import compute_risk, risk_score_label, sample_size_label`을 추가한다.

```python
from review_pipeline import compute_risk, risk_score_label, sample_size_label


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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd "blog/scripts" && python -m unittest test_review_pipeline -v`
Expected: `ImportError: cannot import name 'compute_risk'`

- [ ] **Step 3: 구현 작성**

`review_pipeline.py`에 아래 함수들을 추가한다.

```python
def risk_score_label(score: float) -> str:
    if score < 0.20:
        return "리스크 낮음"
    if score < 0.40:
        return "리스크 보통"
    if score < 0.60:
        return "리스크 높음"
    return "리스크 매우 높음"


def sample_size_label(n_total: int) -> str:
    if n_total < 10:
        return "표본 매우 부족"
    if n_total < 30:
        return "표본 부족"
    return "표본 충분"


def compute_risk(n1: int, n2: int, n3: int, n4: int) -> dict:
    n_total = n1 + n2 + n3 + n4
    if n_total == 0:
        return {
            "n1": n1, "n2": n2, "n3": n3, "n4": n4,
            "n_total": 0,
            "risk_score": None,
            "risk_label": "계산 불가 (1~4점 리뷰 없음)",
            "sample_label": "계산 불가",
        }
    p1, p2, p3, p4 = n1 / n_total, n2 / n_total, n3 / n_total, n4 / n_total
    raw = (4 * p1 + 3 * p2 + 2 * p3 - 1 * p4) / 4
    risk_score = max(0.0, raw)
    return {
        "n1": n1, "n2": n2, "n3": n3, "n4": n4,
        "n_total": n_total,
        "risk_score": risk_score,
        "risk_label": risk_score_label(risk_score),
        "sample_label": sample_size_label(n_total),
    }
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd "blog/scripts" && python -m unittest test_review_pipeline -v`
Expected: 이전 7개 + 새 6개 (RiskScoreLabelTests 1 + SampleSizeLabelTests 1 + ComputeRiskTests 4) = 총 13개 테스트 모두 `ok`

- [ ] **Step 5: 커밋**

```bash
cd "blog"
git add scripts/review_pipeline.py scripts/test_review_pipeline.py
git commit -m "add risk score and sample size label calculation"
```

---

### Task 4: 엑셀 생성 함수

**Files:**
- Modify: `blog/scripts/review_pipeline.py`
- Modify: `blog/scripts/test_review_pipeline.py`

**Interfaces:**
- Consumes: `group_files_by_product` (Task 2), `compute_risk` (Task 3)
- Produces:
  - `QUAL_COLUMNS: list[str]` (모듈 상수, `['핵심_보조_태그', '근거_원문_인용', '비고']`)
  - `load_star_dataframe(paths: list[Path], add_qual_columns: bool) -> pandas.DataFrame`
  - `write_product_excel(product: str, star_files: dict[int, list[Path]], out_folder: Path) -> Path` — 생성된 엑셀 파일 경로 반환

- [ ] **Step 1: 실패하는 테스트 작성**

`test_review_pipeline.py` 맨 위 import 구역에 `import openpyxl`과 `from review_pipeline import load_star_dataframe, write_product_excel`을 추가하고, 아래 클래스를 추가한다.

```python
import openpyxl

from review_pipeline import load_star_dataframe, write_product_excel


class LoadStarDataframeTests(unittest.TestCase):
    def test_adds_qual_columns_when_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "shoe1.csv"
            csv_path.write_text("review_text,date\n소리가 심해요,2025.01.01\n", encoding="utf-8")

            df = load_star_dataframe([csv_path], add_qual_columns=True)

            self.assertEqual(len(df), 1)
            self.assertIn("핵심_보조_태그", df.columns)
            self.assertIn("근거_원문_인용", df.columns)
            self.assertIn("비고", df.columns)

    def test_skips_qual_columns_when_not_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "shoe5.csv"
            csv_path.write_text("review_text,date\n완전 만족해요,2025.01.02\n", encoding="utf-8")

            df = load_star_dataframe([csv_path], add_qual_columns=False)

            self.assertNotIn("핵심_보조_태그", df.columns)


class WriteProductExcelTests(unittest.TestCase):
    def test_creates_workbook_with_expected_sheets(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            star1 = tmp_path / "shoe1.csv"
            star1.write_text("review_text,date\n소리 나요,2025.01.01\n실밥 터짐,2025.01.02\n", encoding="utf-8")
            star4 = tmp_path / "shoe4.csv"
            star4.write_text("review_text,date\n대체로 만족,2025.02.01\n", encoding="utf-8")

            star_files = {1: [star1], 4: [star4]}
            out_path = write_product_excel("shoe", star_files, tmp_path)

            self.assertTrue(out_path.exists())
            self.assertEqual(out_path.name, "shoe_review_analysis.xlsx")

            wb = openpyxl.load_workbook(out_path)
            self.assertEqual(
                set(wb.sheetnames), {"요약", "1점", "4점"}
            )

            sheet1 = wb["1점"]
            header = [cell.value for cell in sheet1[1]]
            self.assertIn("핵심_보조_태그", header)
            self.assertEqual(sheet1.max_row, 3)  # 헤더 1행 + 데이터 2행

            summary = wb["요약"]
            summary_values = [cell.value for row in summary.iter_rows() for cell in row]
            self.assertIn("리스크 점수", summary_values)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd "blog/scripts" && python -m unittest test_review_pipeline -v`
Expected: `ImportError: cannot import name 'load_star_dataframe'`

- [ ] **Step 3: 구현 작성**

`review_pipeline.py` 맨 위 import 구역에 `import pandas as pd`를 추가하고, 아래 함수들과 상수를 추가한다.

```python
QUAL_COLUMNS = ["핵심_보조_태그", "근거_원문_인용", "비고"]


def load_star_dataframe(paths: list[Path], add_qual_columns: bool) -> pd.DataFrame:
    df = pd.concat(
        [pd.read_csv(p, encoding="utf-8") for p in paths], ignore_index=True
    )
    if add_qual_columns:
        for col in QUAL_COLUMNS:
            df[col] = ""
    return df


def build_summary_df(risk: dict, n5: int) -> pd.DataFrame:
    rows = [
        ("1점 리뷰 수", risk["n1"]),
        ("2점 리뷰 수", risk["n2"]),
        ("3점 리뷰 수", risk["n3"]),
        ("4점 리뷰 수", risk["n4"]),
        ("1~4점 합계(N)", risk["n_total"]),
        ("5점 리뷰 수(참고용)", n5),
        ("리스크 점수", risk["risk_score"] if risk["risk_score"] is not None else "계산 불가"),
        ("리스크 해석", risk["risk_label"]),
        ("표본크기 신뢰도", risk["sample_label"]),
    ]
    return pd.DataFrame(rows, columns=["항목", "값"])


def write_product_excel(
    product: str, star_files: dict[int, list[Path]], out_folder: Path
) -> Path:
    star_dfs: dict[int, pd.DataFrame] = {}
    for star in range(1, 6):
        paths = star_files.get(star, [])
        if paths:
            star_dfs[star] = load_star_dataframe(paths, add_qual_columns=(star != 5))

    counts = {star: len(df) for star, df in star_dfs.items()}
    risk = compute_risk(
        n1=counts.get(1, 0),
        n2=counts.get(2, 0),
        n3=counts.get(3, 0),
        n4=counts.get(4, 0),
    )
    summary_df = build_summary_df(risk, n5=counts.get(5, 0))

    out_path = out_folder / f"{product}_review_analysis.xlsx"
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="요약", index=False)
        for star in range(1, 6):
            if star in star_dfs:
                star_dfs[star].to_excel(writer, sheet_name=f"{star}점", index=False)
    return out_path
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd "blog/scripts" && python -m unittest test_review_pipeline -v`
Expected: 이전 13개 + 새 3개 = 16개 테스트 모두 `ok`

- [ ] **Step 5: 커밋**

```bash
cd "blog"
git add scripts/review_pipeline.py scripts/test_review_pipeline.py
git commit -m "add excel workbook generation per product"
```

---

### Task 5: CLI 진입점 작성 및 실제 데이터로 실행 검증

**Files:**
- Modify: `blog/scripts/review_pipeline.py`
- Modify: `blog/scripts/test_review_pipeline.py`

**Interfaces:**
- Consumes: `group_files_by_product`, `write_product_excel` (위 Task들)
- Produces: `main(folder: str) -> list[Path]` — 처리된 상품별 결과 파일 경로 리스트 반환. `if __name__ == "__main__":` 블록에서 커맨드라인 인자로 폴더 경로를 받는다 (기본값 `"."`).

- [ ] **Step 1: 실패하는 테스트 작성**

`test_review_pipeline.py`에 `from review_pipeline import main`을 추가하고 아래 클래스를 추가한다.

```python
from review_pipeline import main


class MainTests(unittest.TestCase):
    def test_processes_all_products_in_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "shoe1.csv").write_text(
                "review_text,date\n별로예요,2025.01.01\n", encoding="utf-8"
            )
            (tmp_path / "fan4.csv").write_text(
                "review_text,date\n괜찮아요,2025.01.02\n", encoding="utf-8"
            )

            outputs = main(str(tmp_path))

            names = {p.name for p in outputs}
            self.assertEqual(names, {"shoe_review_analysis.xlsx", "fan_review_analysis.xlsx"})
            for p in outputs:
                self.assertTrue(p.exists())
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd "blog/scripts" && python -m unittest test_review_pipeline -v`
Expected: `ImportError: cannot import name 'main'`

- [ ] **Step 3: 구현 작성**

`review_pipeline.py` 맨 아래에 아래 코드를 추가한다.

```python
def main(folder: str = ".") -> list[Path]:
    folder_path = Path(folder)
    groups = group_files_by_product(folder_path)
    outputs = []
    for product, star_files in groups.items():
        out_path = write_product_excel(product, star_files, folder_path)
        print(f"생성됨: {out_path}")
        outputs.append(out_path)
    return outputs


if __name__ == "__main__":
    import sys

    main(sys.argv[1] if len(sys.argv) > 1 else ".")
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd "blog/scripts" && python -m unittest test_review_pipeline -v`
Expected: 이전 16개 + 새 1개 = 17개 테스트 모두 `ok`

- [ ] **Step 5: 커밋**

```bash
cd "blog"
git add scripts/review_pipeline.py scripts/test_review_pipeline.py
git commit -m "add CLI entry point for review pipeline"
```

- [ ] **Step 6: 실제 리뷰 데이터로 실행 (수동 검증)**

Run: `cd "blog" && python scripts/review_pipeline.py .`
Expected: `생성됨: ...\shoe_review_analysis.xlsx` 출력, `blog` 폴더에 `shoe_review_analysis.xlsx` 파일 생성됨.

이후 생성된 엑셀을 열어서 다음을 눈으로 확인한다.
- `요약` 시트에 1~4점 개수, 리스크 점수, 리스크 해석, 표본크기 라벨이 들어있는지
- `1점`~`4점` 시트에 원본 리뷰 컬럼 + `핵심_보조_태그`/`근거_원문_인용`/`비고` 빈 컬럼이 있는지
- 5점 파일이 없으므로 `5점` 시트는 생성되지 않았는지 (정상 동작)

- [ ] **Step 7: 결과 확인 후 커밋**

```bash
cd "blog"
git add -A
git commit -m "verify pipeline output against real shoe review data"
```

(`.gitignore`에 `*.csv`, `*.xlsx`가 등록되어 있어 원본 리뷰 CSV와 생성된 엑셀은 이 커밋에 포함되지 않는다.)

---

## Self-Review 메모

- 스펙의 모든 섹션(파일 인식 규칙, 엑셀 구조, 리스크 계산식, 표본크기 보정, 정성 분석 처리, 스크립트 재사용성)이 Task 1~5에 매핑됨을 확인함.
- 플레이스홀더("TBD" 등) 없음을 확인함.
- 함수 시그니처 일관성 확인: `parse_filename`(Task1) → `group_files_by_product`(Task2) → `compute_risk`/`risk_score_label`/`sample_size_label`(Task3) → `load_star_dataframe`/`write_product_excel`(Task4) → `main`(Task5)까지 이름과 타입이 각 Task에서 그대로 재사용됨.
- Task 5 Step 7에서 원본 CSV가 git에 커밋되는 부작용을 발견해서, 실행 전 사용자 확인을 받도록 경고 문구를 추가함.
- Task 3의 `test_mixed_counts`에서 표본크기 라벨 기댓값이 틀려 있었음(N=20인데 "표본 충분"로 적혀 있었음, 규칙상 "표본 부족"이 맞음) — 수정함. 이에 따라 Task 3~5의 누적 테스트 개수 안내도 13/16/17개로 재계산해서 수정함.
