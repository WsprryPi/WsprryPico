"""Operator manual only. Engineering material is outside this source tree."""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "_ext"))

project = "WsprryPico"
author = "Lee C. Bussy and contributors"
copyright = "2026, Lee C. Bussy and contributors"
extensions = ["image_delivery", "myst_parser"]
templates_path = ["_templates"]
source_suffix = {".md": "markdown"}
master_doc = "index"
language = "en"
exclude_patterns = ["_build", ".venv", "requirements.txt", "Makefile", "make.bat",
                    "Thumbs.db", ".DS_Store"]
myst_enable_extensions = ["colon_fence", "deflist", "tasklist"]
myst_heading_anchors = 4
nitpicky = True
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "logo_only": False,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "navigation_depth": 3,
    "includehidden": True,
    "titles_only": True,
    "prev_next_buttons_location": "both",
    "style_external_links": True,
}
html_logo = "_static/WsprryPi_Logo.png"
html_favicon = "_static/favicon.ico"
html_static_path = ["_static"]
html_css_files = ["css/custom.css"]
html_js_files = ["js/accessibility.js"]
html_show_sourcelink = False
html_title = "WsprryPico operator manual"
html_context = {"display_github": False}
try:
    source_revision = subprocess.check_output(
        ["git", "rev-parse", "--short=12", "HEAD"], text=True
    ).strip()
except (OSError, subprocess.CalledProcessError):
    source_revision = "unknown"
version = os.environ.get("READTHEDOCS_VERSION", "devel")
release = f"{version} · {source_revision}"


def verify_contextual_help(app, exception):
    """A removed help target must fail local and published HTML builds."""
    if exception is None and app.builder.format == 'html':
        subprocess.run([sys.executable,
                        str(Path(__file__).resolve().parents[1] / 'scripts/check_contextual_help.py'),
                        '--site', str(app.outdir),
                        '--version', 'main' if version == 'main' else 'devel'], check=True)


def setup(app):
    app.connect('build-finished', verify_contextual_help)
