"""Operator manual only. Engineering material is outside this source tree."""
import os
import subprocess

project = "WsprryPico"
author = "Lee C. Bussy and contributors"
copyright = "2026, Lee C. Bussy and contributors"
extensions = ["myst_parser"]
source_suffix = {".md": "markdown"}
master_doc = "index"
language = "en"
exclude_patterns = ["_build", ".venv", "requirements.txt", "Thumbs.db", ".DS_Store"]
myst_enable_extensions = ["colon_fence", "deflist"]
myst_heading_anchors = 4
nitpicky = True
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "collapse_navigation": False,
    "navigation_depth": 3,
    "includehidden": True,
    "titles_only": True,
    "prev_next_buttons_location": "both",
    "style_external_links": True,
}
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
