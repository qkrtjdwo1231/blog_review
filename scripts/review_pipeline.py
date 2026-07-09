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
