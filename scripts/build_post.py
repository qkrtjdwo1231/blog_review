# 제품 폴더의 post-data.json을 읽어 블로그 글(post.md, post.html)과 대표 이미지(cover.html)를 만드는 스크립트
import json
import sys
import html
from pathlib import Path

STAR_ROWS = [
    ("s5", "⭐⭐⭐⭐⭐ 최고(5점)", 5),
    ("s4", "⭐⭐⭐⭐ 좋음(4점)", 4),
    ("s3", "⭐⭐⭐ 보통(3점)", 3),
    ("s2", "⭐⭐ 별로(2점)", 2),
    ("s1", "⭐ 나쁨(1점)", 1),
]

NOTICE_1 = "광고 안내｜ 이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다"
NOTICE_2 = "제조사로부터 제품 협찬이나 원고료는 일절 받지 않습니다. 구매 후 후회하지 않도록, 실구매자의 리뷰·평점 데이터를 바탕으로 이 제품이 잘 맞는 분과 맞지 않는 기준을 분석했습니다."


def fmt(n: int) -> str:
    return f"{n:,}"


def pct(part: int, total: int) -> str:
    return f"약 {part / total * 100:.1f}%"


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def rating_rows(r: dict) -> list[tuple[str, str, str]]:
    total = sum(r[k] for k, _, _ in STAR_ROWS)
    rows = [(label, f"{fmt(r[k])}개", pct(r[k], total)) for k, label, _ in STAR_ROWS]
    rows.append(("전체", f"{fmt(total)}개", "100%"))
    return rows


# ---------- markdown ----------
def md_table(rows: list[list[str]], header: list[str] | None = None) -> str:
    out = []
    if header:
        out.append("| " + " | ".join(header) + " |")
        out.append("|" + "---|" * len(header))
    else:
        out.append("| " + " | ".join(rows[0]) + " |")
        out.append("|" + "---|" * len(rows[0]))
        rows = rows[1:]
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


def build_md(d: dict) -> str:
    p = d["product_name"]
    parts = [f"# {d['title']}", "", f"{NOTICE_1}", "", NOTICE_2, "",
             f"[이미지: {d['cover_alt']}]", "", d["meta_intro"], "",
             "## 📊 쿠팡 별점 분포", "",
             md_table([list(r) for r in rating_rows(d["ratings"])], ["별점", "개수", "비율"]), "",
             d["rating_comment"], "",
             "## 📌 핵심 요약", "",
             md_table([[k, v] for k, v in d["summary_table"]], ["항목", "내용"]), "",
             f"## 🔍 {p} 상세 분석", ""]
    circ = "①②③④⑤⑥"
    for i, a in enumerate(d["analysis"]):
        parts.append(f"#### {circ[i]} **{a['name']}**: {a['desc']}")
        parts.append("")
    parts += [f"## ✅ {p} 실제 장점", ""]
    for x in d["pros"]:
        parts += [f"#### **{x['head']}**", "", x["body"], ""]
    parts += [f"## ❌ {p} 실제 단점", ""]
    for x in d["cons"]:
        parts += [f"#### **{x['head']}**", "", x["body"], ""]
    parts += ["## 📊 용도별 추천 점수 카드", "",
              md_table([list(r) for r in d["score_cards"]], ["용도", "점수", "한 줄 판단"]), ""]
    if d.get("option_guide"):
        parts += ["## 🧭 옵션별 선택 가이드", "",
                  md_table([list(r) for r in d["option_guide"]], ["옵션", "이런 분께", "확인할 점"]), ""]
    parts += ["## 🔑 구매 전 체크포인트 3가지", ""]
    for i, c in enumerate(d["checkpoints"]):
        parts += [f"#### {circ[i]} **{c['head']}**", "", c["body"], ""]
    parts += ["## 📌 최종 결론", ""]
    for para in d["conclusion"]:
        parts += [para, ""]
    parts += [f"> \"{d['closing_quote']}\"", "", f"👉 {p} 현재 가격 및 스펙 확인하기 [쿠팡 링크 삽입]", "",
              "태그: " + ", ".join(d["tags"])]
    return "\n".join(parts)


# ---------- tistory html ----------
def h_table(rows: list[list[str]], bold_last: int = 0) -> str:
    trs = []
    for i, row in enumerate(rows):
        tds = []
        for c in row:
            c = esc(str(c))
            if bold_last and i >= len(rows) - bold_last:
                c = f"<b>{c}</b>"
            tds.append(f"<td>{c}</td>")
        trs.append("<tr>" + "".join(tds) + "</tr>")
    return ('<table style="border-collapse: collapse; width: 100%;" border="1" data-ke-align="alignLeft">'
            "<tbody>" + "".join(trs) + "</tbody></table>")


def h2(t: str) -> str:
    return f'<h2 data-ke-size="size26">{esc(t)}</h2>'


def h4(t_html: str) -> str:
    return f'<h4 data-ke-size="size20">{t_html}</h4>'


def p(t: str) -> str:
    return f'<p data-ke-size="size16">{esc(t)}</p>'


def build_html(d: dict) -> str:
    pn = d["product_name"]
    circ = "①②③④⑤⑥"
    out = [
        f'<p style="color: #888; font-size: 13px; margin-bottom: 8px;" data-nosnippet="" data-ke-size="size16">{esc(NOTICE_1[:6])}<b>{esc(NOTICE_1[6:])}</b></p>',
        f'<p style="color: #888; font-size: 13px;" data-nosnippet="" data-ke-size="size16"><b>{esc(NOTICE_2.split(". ")[0])}.</b> {esc(NOTICE_2.split(". ", 1)[1])}</p>',
        f'<p data-ke-size="size16">[대표 이미지 삽입. alt: {esc(d["cover_alt"])}]</p>',
        p(d["meta_intro"]),
        h2("📊 쿠팡 별점 분포"),
        h_table([list(r) for r in rating_rows(d["ratings"])]),
        p(d["rating_comment"]),
        h2("📌 핵심 요약"),
        h_table([[k, v] for k, v in d["summary_table"]], bold_last=2),
        h2(f"🔍 {pn} 상세 분석"),
    ]
    for i, a in enumerate(d["analysis"]):
        out.append(h4(f"{circ[i]} <b>{esc(a['name'])}</b>: {esc(a['desc'])}"))
    out.append(h2(f"✅ {pn} 실제 장점"))
    for x in d["pros"]:
        out += [h4(f"<b>{esc(x['head'])}</b>"), p(x["body"])]
    out.append(h2(f"❌ {pn} 실제 단점"))
    for x in d["cons"]:
        out += [h4(f"<b>{esc(x['head'])}</b>"), p(x["body"])]
    out += [h2("📊 용도별 추천 점수 카드"), h_table([list(r) for r in d["score_cards"]])]
    if d.get("option_guide"):
        out += [h2("🧭 옵션별 선택 가이드"), h_table([list(r) for r in d["option_guide"]])]
    out.append(h2("🔑 구매 전 체크포인트 3가지"))
    for i, c in enumerate(d["checkpoints"]):
        out += [h4(f"{circ[i]} <b>{esc(c['head'])}</b>"), p(c["body"])]
    out.append(h2("📌 최종 결론"))
    for para in d["conclusion"]:
        out.append(p(para))
    out.append('<blockquote data-ke-style="style1">'
               f'<p style="text-align: center;" data-ke-size="size16">"{esc(d["closing_quote"])}"</p>'
               '<p style="text-align: center;" data-ke-size="size16"><a href="[쿠팡 파트너스 링크]" target="_blank" rel="noopener">👉 '
               f'{esc(pn)} 현재 가격 및 스펙 확인하기</a></p></blockquote>')
    out.append(f'<!-- 태그: {esc(", ".join(d["tags"]))} -->')
    return "\n".join(out)


# ---------- cover html ----------
COVER_CSS = """
*{box-sizing:border-box;margin:0;padding:0;word-break:keep-all}
body{width:1536px;height:1024px;overflow:hidden;background:#f4f3f1;font-family:'Pretendard','Noto Sans KR',sans-serif;color:#222;position:relative}
.bg{position:absolute;inset:0;background:radial-gradient(circle at 20% 10%,#ffffff 0,#f4f3f1 55%,#eeece8 100%)}
.abs{position:absolute}
.logo{left:36px;top:8px;width:130px;height:130px;background:url(../_template/logo.png) center/contain no-repeat}
.brand{left:170px;top:52px;font-size:30px;font-weight:800;color:#2b2b2b;letter-spacing:-1px}
.brand::after{content:"";position:absolute;left:300px;top:22px;width:300px;height:2px;background:#d8d4cc}
.pulse{left:656px;top:14px;width:148px;height:122px;background:url(../_template/pulse.png) center/contain no-repeat}
.headline{left:50px;top:150px;width:600px;line-height:1.14;letter-spacing:-2px;font-weight:900}
.headline .gold{font-size:56px;color:#b8862f}
.headline .dark{font-size:56px;color:#2d2d2d}
.sub{left:50px;top:395px;width:600px;font-size:21px;line-height:1.55;color:#444;letter-spacing:-0.5px;font-weight:500}
.pill{left:50px;top:535px;height:64px;padding:0 28px 0 24px;border-radius:34px;background:#222;color:#fff;font-size:26px;font-weight:700;display:flex;align-items:center;gap:14px;box-shadow:0 6px 16px rgba(0,0,0,.25)}
.pill b{color:#f0a53a}
.feat{left:652px;width:240px;height:132px;background:#f3eee6;border-radius:16px;padding:16px 12px 12px 64px;box-shadow:0 2px 6px rgba(0,0,0,.06);display:flex;flex-direction:column;justify-content:center}
.feat .ic{position:absolute;left:14px;top:38px;font-size:36px;line-height:1}
.feat .t{font-size:17px;font-weight:800;color:#222;margin-bottom:5px;letter-spacing:-0.6px;line-height:1.25}
.feat .d{font-size:14px;line-height:1.35;color:#444;letter-spacing:-0.3px}
.card{background:#fff;border-radius:18px;box-shadow:0 4px 18px rgba(0,0,0,.08)}
.rating{left:906px;top:66px;width:594px;height:564px;padding:18px 16px}
.rating table{width:100%;border-collapse:separate;border-spacing:0;font-size:26px}
.rating th{background:#f3dcc0;color:#222;font-weight:700;padding:16px 0;font-size:26px}
.rating th:first-child{border-radius:12px 0 0 0}.rating th:last-child{border-radius:0 12px 0 0}
.rating td{text-align:center;padding:20px 0;border-bottom:1px solid #e9e4dc;font-size:28px;color:#222}
.rating tr.total td{background:#f7f4ee;font-weight:700;border-bottom:0}
.stars{letter-spacing:3px;font-size:28px}.stars .on{color:#c99545}.stars .off{color:#d9d6d0}
.box{top:660px;height:346px;padding:22px 24px}
.box .h{font-size:23px;font-weight:800;display:flex;align-items:center;gap:10px;margin-bottom:16px;letter-spacing:-0.5px}
.summary{left:36px;width:336px}
.summary li{list-style:none;font-size:17px;line-height:1.35;color:#333;margin-bottom:14px;padding-left:30px;position:relative}
.summary li::before{content:"✓";position:absolute;left:0;top:0;width:20px;height:20px;border:2px solid #444;border-radius:50%;font-size:12px;text-align:center;line-height:16px}
.summary li.key{color:#b8862f;font-weight:800;font-size:21px;margin-top:6px}
.summary li.key::before{content:"✓";background:#b8862f;border-color:#b8862f;color:#fff}
.info{left:382px;width:552px}
.info .cols{display:grid;grid-template-columns:1fr 1fr;column-gap:22px}
.info .cols>div+div{border-left:1px solid #e3dfd8;padding-left:22px}
.info .it{display:flex;gap:12px;margin-bottom:14px}
.info .it .ic{font-size:26px;width:34px;flex:none;line-height:1.2}
.info .it .l{font-size:16px;font-weight:800;color:#222}
.info .it .v{font-size:15px;color:#333;line-height:1.35;white-space:pre-line}
.fit{left:946px;width:258px}.fit .h{color:#1f8a3b}.fit{background:linear-gradient(#edf7ef,#fff 30%)}
.unfit{left:1216px;width:284px}.unfit .h{color:#d8322b}.unfit{background:linear-gradient(#fdeeee,#fff 30%)}
.use li{list-style:none;display:flex;align-items:center;gap:14px;font-size:17px;line-height:1.3;color:#222;margin-bottom:18px;font-weight:600}
.use li .ic{font-size:30px;width:40px;flex:none;text-align:center}
"""


def stars(n: int) -> str:
    return '<span class="stars">' + '<span class="on">' + "★" * n + '</span><span class="off">' + "★" * (5 - n) + "</span></span>"


def build_cover(d: dict) -> str:
    c = d["cover"]
    r = d["ratings"]
    total = sum(r[k] for k, _, _ in STAR_ROWS)
    rows = "".join(
        f"<tr><td>{stars(n)}</td><td>{fmt(r[k])}개</td><td>{pct(r[k], total)}</td></tr>" for k, _, n in STAR_ROWS)
    rows += f'<tr class="total"><td>전체</td><td>{fmt(total)}개</td><td>100%</td></tr>'
    feats = "".join(
        f'<div class="abs feat" style="top:{156 + i * 148}px"><div class="ic">{f["icon"]}</div><div class="t">{esc(f["title"])}</div><div class="d">{esc(f["desc"])}</div></div>'
        for i, f in enumerate(c["features"][:3]))
    summ = "".join(f"<li>{esc(s)}</li>" for s in c["summary"][:3]) + f'<li class="key">{esc(c["key_line"])}</li>'
    infos = c["info"]
    half = (len(infos) + 1) // 2
    def col(items):
        return "".join(f'<div class="it"><div class="ic">{i["icon"]}</div><div><div class="l">{esc(i["label"])}</div><div class="v">{esc(i["value"])}</div></div></div>' for i in items)
    info_html = f'<div class="cols"><div>{col(infos[:half])}</div><div>{col(infos[half:])}</div></div>'
    fit = "".join(f'<li><span class="ic">{x["icon"]}</span><span>{esc(x["text"])}</span></li>' for x in c["fit"][:3])
    unfit = "".join(f'<li><span class="ic">{x["icon"]}</span><span>{esc(x["text"])}</span></li>' for x in c["unfit"][:3])
    gold = "<br>".join(esc(x) for x in c["headline_gold"])
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{esc(d['product_name'])} 대표 이미지</title>
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
<style>{COVER_CSS}</style></head><body><div class="bg"></div>
<div class="abs logo"></div><div class="abs brand">별점 이면의 목소리</div><div class="abs pulse"></div>
<div class="abs headline"><div class="gold">{gold}</div><div class="dark">{esc(c['headline_dark'])}</div></div>
<div class="abs sub">{esc(c['sub'])}</div>
<div class="abs pill">🗄️ 총 리뷰 <b>{fmt(total)}</b>개 데이터 팩트 체크 🔍</div>
{feats}
<div class="abs card rating"><table><thead><tr><th>별점</th><th>개수</th><th>전체</th></tr></thead><tbody>{rows}</tbody></table></div>
<div class="abs card box summary"><div class="h">📋 핵심 요약</div><ul>{summ}</ul></div>
<div class="abs card box info"><div class="h">🏷️ 제품 정보</div>{info_html}</div>
<div class="abs card box fit"><div class="h">✅ 이 제품에 맞는 용도</div><ul class="use">{fit}</ul></div>
<div class="abs card box unfit"><div class="h">⛔ 이 제품에 안 맞는 용도</div><ul class="use">{unfit}</ul></div>
</body></html>"""


CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def render_png(fp: Path) -> str:
    # 헤드리스 크롬으로 cover.html을 1536x1024 PNG로 저장한다
    import os
    import subprocess
    import tempfile
    html_path = (fp / "cover.html").resolve()
    png_path = (fp / "cover.png").resolve()
    profile = Path(tempfile.mkdtemp(prefix="claude-headless-"))  # 동시 실행 시 프로필 잠김 방지
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1536,1024",
           f"--user-data-dir={profile}", "--virtual-time-budget=5000", f"--screenshot={png_path}",
           html_path.as_uri()]
    r = subprocess.run(cmd, capture_output=True, timeout=120)
    return "cover.png" if png_path.exists() and r.returncode == 0 else f"cover.png 실패({r.returncode})"


def main(folder: str) -> None:
    fp = Path(folder)
    d = json.loads((fp / "post-data.json").read_text(encoding="utf-8"))
    (fp / "post.md").write_text(build_md(d), encoding="utf-8")
    (fp / "post.html").write_text(build_html(d), encoding="utf-8")
    (fp / "cover.html").write_text(build_cover(d), encoding="utf-8")
    body = build_md(d)
    chars = len("".join(ch for ch in body if not ch.isspace()))
    png = render_png(fp)
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"{fp.name}: post.md {chars}자(공백 제외), post.html, cover.html, {png} 생성")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        main(arg)
