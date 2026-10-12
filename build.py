import shutil
import sys
from pathlib import Path
import markdown
import os

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent

def gen_doc():
	header = """<!DOCTYPE html>
<html lang="es">
<head>
<title>Guía de usuario de Tor Manager</title>
<meta charset="utf-8">
</head>
<body>"""
	footer="""</body>
</html>"""
	source = open(os.path.join("docs", "guia-de-usuario.md"), "r", encoding="utf-8")
	md = source.read()
	source.close()
	target = open(os.path.join("docs", "guia-de-usuario.html"), "w", encoding="utf-8")
	html = header + markdown.markdown(md, extensions=["markdown.extensions.tables", "markdown.extensions.def_list"]) + footer
	target.write(html)
	target.close()

def main() -> int:
	gen_doc()
	args = [
		str(ROOT / "TorManager.spec"),
	]
	PyInstaller.__main__.run(args)
	dist = ROOT / "dist"
	for name in ("guia-de-usuario.html", "LICENSE"):
		if (ROOT / "docs" / name).exists():
			shutil.copy2(ROOT / "docs" / name, dist / name)
	shutil.copytree(ROOT / "resources", dist / "resources")
	print(f"\nVersión portable generada en {dist}")
	return 0


if __name__ == "__main__":
	sys.exit(main())
