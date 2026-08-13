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
for marker in [
    "8.7 Dendrogram",
    "8.8 Data tables",
    "8.9 Manual",
    "11. Suggested build order",
]:
    i = text.find(marker)
    print("====", marker, "at", i, "====")
    if i >= 0:
        print(text[i : i + 5000])
        print()
