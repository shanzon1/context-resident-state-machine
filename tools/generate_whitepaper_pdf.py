from __future__ import annotations

import argparse
import html
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MD = ROOT / "docs" / "resident_state_machine_white_paper.md"
DEFAULT_PDF = ROOT / "docs" / "resident_state_machine_white_paper.pdf"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


def inline_markdown(text: str, base_dir: Path) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)

    def image(match: re.Match[str]) -> str:
        alt = html.escape(match.group(1))
        src = match.group(2)
        path = (base_dir / src).resolve()
        return f'<img src="{path.as_uri()}" alt="{alt}" />'

    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", image, text)
    return text


def flush_paragraph(lines: list[str], out: list[str], base_dir: Path) -> None:
    if not lines:
        return
    paragraph = " ".join(line.strip() for line in lines)
    out.append(f"<p>{inline_markdown(paragraph, base_dir)}</p>")
    lines.clear()


def table_to_html(lines: list[str], base_dir: Path) -> str:
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows.append(cells)
    header = rows[0]
    body = rows[2:]
    parts = ["<table>", "<thead><tr>"]
    parts.extend(f"<th>{inline_markdown(cell, base_dir)}</th>" for cell in header)
    parts.append("</tr></thead><tbody>")
    for row in body:
        parts.append("<tr>")
        parts.extend(f"<td>{inline_markdown(cell, base_dir)}</td>" for cell in row)
        parts.append("</tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


def markdown_to_html(markdown: str, base_dir: Path) -> str:
    out: list[str] = []
    paragraph: list[str] = []
    code: list[str] | None = None
    list_mode: str | None = None
    table: list[str] = []

    def close_list() -> None:
        nonlocal list_mode
        if list_mode:
            out.append(f"</{list_mode}>")
            list_mode = None

    def close_table() -> None:
        if table:
            out.append(table_to_html(table, base_dir))
            table.clear()

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()

        if code is not None:
            if line.startswith("```"):
                out.append(f"<pre><code>{html.escape(chr(10).join(code))}</code></pre>")
                code = None
            else:
                code.append(line)
            continue

        if line.startswith("```"):
            flush_paragraph(paragraph, out, base_dir)
            close_list()
            close_table()
            code = []
            continue

        if line.startswith("|") and line.endswith("|"):
            flush_paragraph(paragraph, out, base_dir)
            close_list()
            table.append(line)
            continue
        close_table()

        if not line.strip():
            flush_paragraph(paragraph, out, base_dir)
            close_list()
            continue

        heading = re.match(r"^(#{1,4})\s+(.*)$", line)
        if heading:
            flush_paragraph(paragraph, out, base_dir)
            close_list()
            level = len(heading.group(1))
            out.append(f"<h{level}>{inline_markdown(heading.group(2), base_dir)}</h{level}>")
            continue

        unordered = re.match(r"^-\s+(.*)$", line)
        ordered = re.match(r"^\d+\.\s+(.*)$", line)
        if unordered or ordered:
            flush_paragraph(paragraph, out, base_dir)
            target = "ul" if unordered else "ol"
            if list_mode != target:
                close_list()
                out.append(f"<{target}>")
                list_mode = target
            item = unordered.group(1) if unordered else ordered.group(1)
            out.append(f"<li>{inline_markdown(item, base_dir)}</li>")
            continue

        paragraph.append(line)

    flush_paragraph(paragraph, out, base_dir)
    close_list()
    close_table()
    return "\n".join(out)


def build_html(markdown_path: Path) -> str:
    body = markdown_to_html(markdown_path.read_text(encoding="utf-8"), markdown_path.parent)
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Resident State Machine White Paper</title>
  <style>
    @page {{ size: letter; margin: 0.72in; }}
    body {{
      font-family: "Segoe UI", Arial, sans-serif;
      color: #111827;
      font-size: 10.8pt;
      line-height: 1.45;
    }}
    h1 {{
      font-size: 24pt;
      line-height: 1.15;
      margin: 0 0 14pt;
      page-break-after: avoid;
    }}
    h2 {{
      font-size: 15.5pt;
      margin: 24pt 0 8pt;
      page-break-after: avoid;
    }}
    h3 {{
      font-size: 12.5pt;
      margin: 18pt 0 6pt;
      page-break-after: avoid;
    }}
    p {{ margin: 0 0 9pt; }}
    ul, ol {{ margin-top: 0; padding-left: 22pt; }}
    li {{ margin-bottom: 4pt; }}
    code {{
      font-family: Consolas, Menlo, monospace;
      font-size: 9.4pt;
      background: #f3f4f6;
      padding: 1pt 3pt;
      border-radius: 3pt;
    }}
    pre {{
      border: 0.8pt solid #cbd5e1;
      background: #f8fafc;
      padding: 8pt;
      white-space: pre-wrap;
      page-break-inside: avoid;
    }}
    pre code {{ background: transparent; padding: 0; }}
    img {{
      display: block;
      max-width: 100%;
      margin: 12pt auto 8pt;
      page-break-inside: avoid;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 10pt 0 14pt;
      font-size: 8.6pt;
    }}
    th, td {{
      border: 0.7pt solid #cbd5e1;
      padding: 5pt;
      vertical-align: top;
    }}
    th {{ background: #f1f5f9; text-align: left; }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def find_browser() -> Path:
    for candidate in (CHROME, EDGE):
        if candidate.exists():
            return candidate
    raise SystemExit("Could not find Chrome or Edge for PDF generation.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--output", type=Path, default=DEFAULT_PDF)
    args = parser.parse_args()

    markdown_path = args.markdown.resolve()
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    html_text = build_html(markdown_path)
    with tempfile.NamedTemporaryFile("w", suffix=".html", encoding="utf-8", delete=False) as temp:
        temp.write(html_text)
        html_path = Path(temp.name)

    browser = find_browser()
    subprocess.run(
        [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={output_path}",
            html_path.as_uri(),
        ],
        check=True,
    )
    print(output_path)


if __name__ == "__main__":
    main()
