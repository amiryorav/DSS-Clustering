from pathlib import Path
import zipfile
import re

p = Path("hebrew_stylometry_webapp_specification.docx")
with zipfile.ZipFile(p) as z:
    xml = z.read("word/document.xml").decode("utf-8")
text = re.sub(r"</w:p>", "\n", xml)
text = re.sub(r"<[^>]+>", "", text)
text = text.replace("&apos;", "'").replace("&quot;", '"').replace("&amp;", "&")
text = re.sub(r"\n{3,}", "\n\n", text)
Path("_spec_extracted.txt").write_text(text, encoding="utf-8")
print(f"Wrote {len(text)} chars to _spec_extracted.txt")
