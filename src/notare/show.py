"""Render scores using OSMD (OpenSheetMusicDisplay)."""

from __future__ import annotations

from pathlib import Path
import json
import tempfile
import webbrowser

from .utils import load_score, write_score

OSMD_VERSION = "https://unpkg.com/opensheetmusicdisplay@1.9.2/build/opensheetmusicdisplay.min.js"

OSMD_TEMPLATE = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{title}</title>
  <style>
    body {{
      margin: 0;
      padding: 0;
    }}
    #osmd-container {{
      width: 100%;
      height: 100vh;
    }}
  </style>
  <script src=\"{osmd_version}\"></script>
  <script>
    window.addEventListener('DOMContentLoaded', function() {{
      const osmd = new opensheetmusicdisplay.OpenSheetMusicDisplay('osmd-container');
      const data = {xml_json};
      osmd.setOptions({{
        drawTitle: {draw_title},
        drawComposer: {draw_composer},
        drawSubtitle: false,
        drawLyricist: {draw_author},
        drawMeasureNumbers: true
      }});
      osmd.load(data).then(function() {{ osmd.render(); }});
    }});
  </script>
</head>
<body>
  <div id=\"osmd-container\"></div>
</body>
</html>
"""


def show_score(
    *,
    source: str | None = None,
    hide_title: bool = False,
    hide_author: bool = False,
    hide_composer: bool = False,
    hide_part_names: bool = False,
    stdin_data: bytes | None = None,
) -> str:
    """Render a score using OSMD and open it in the browser."""
    score = load_score(source, stdin_data=stdin_data)

    if hide_part_names:
        for part in score.parts:
            part.partName = " "

    with tempfile.NamedTemporaryFile(suffix=".musicxml", delete=False) as xml_file:
      xml_path = Path(xml_file.name)
      score.write("musicxml", fp=str(xml_path))
    xml_content = xml_path.read_text(encoding="utf-8")
    try:
      xml_path.unlink(missing_ok=True)
    except Exception:
      pass

    page_title = (score.metadata.title if score.metadata else "") or "Score Preview"
    html_content = OSMD_TEMPLATE.format(
        title=page_title,
        osmd_version=OSMD_VERSION,
      xml_json=json.dumps(xml_content),
        draw_title=str(not hide_title).lower(),
        draw_composer=str(not hide_composer).lower(),
        draw_author=str(not hide_author).lower(),
    )

    html_path = Path(tempfile.mkstemp(suffix=".html")[1])
    html_path.write_text(html_content, encoding="utf-8")
    webbrowser.open(html_path.as_uri())
    return f"Opened score preview in browser: {html_path}"
