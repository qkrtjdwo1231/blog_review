# 상품별 리뷰 CSV 파일을 별점별 시트로 병합하고 리스크 점수를 계산하는 스크립트
import pandas as pd
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


def group_files_by_product(folder: Path) -> dict[str, dict[int, list[Path]]]:
    groups: dict[str, dict[int, list[Path]]] = {}
    for csv_path in sorted(folder.glob("*.csv")):
        parsed = parse_filename(csv_path.name)
        if parsed is None:
            continue
        prefix, star = parsed
        groups.setdefault(prefix, {}).setdefault(star, []).append(csv_path)
    return groups


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
            "p1": None, "p2": None, "p3": None, "p4": None,
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
        "p1": p1, "p2": p2, "p3": p3, "p4": p4,
        "risk_score": risk_score,
        "risk_label": risk_score_label(risk_score),
        "sample_label": sample_size_label(n_total),
    }


QUAL_COLUMNS = ["핵심_보조_태그", "근거_원문_인용", "비고"]


def load_star_dataframe(paths: list[Path], add_qual_columns: bool) -> pd.DataFrame:
    df = pd.concat(
        [pd.read_csv(p, encoding="utf-8") for p in paths], ignore_index=True
    )
    df = df.drop(columns=[c for c in df.columns if c.startswith("web_scraper")])
    if add_qual_columns:
        for col in QUAL_COLUMNS:
            df[col] = ""
    return df


def _ratio_display(p: float | None) -> str:
    if p is None:
        return "계산 불가"
    return f"{p * 100:.1f}%"


def build_summary_df(risk: dict, n5: int) -> pd.DataFrame:
    rows = [
        ("1점 리뷰 수", risk["n1"]),
        ("1점 비율", _ratio_display(risk["p1"])),
        ("2점 리뷰 수", risk["n2"]),
        ("2점 비율", _ratio_display(risk["p2"])),
        ("3점 리뷰 수", risk["n3"]),
        ("3점 비율", _ratio_display(risk["p3"])),
        ("4점 리뷰 수", risk["n4"]),
        ("4점 비율", _ratio_display(risk["p4"])),
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
