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
