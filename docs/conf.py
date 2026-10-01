"""Sphinx settings for the epiplot documentation."""

import epiplot

project = "epiplot"
author = "Lee Hart"
copyright = "2026, Lee Hart"
release = epiplot.__version__
version = release

extensions = [
    "myst_nb",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_design",
    "sphinxcontrib.mermaid",
]

# Pages are written in Markdown.
exclude_patterns = ["_build", "case-studies/data"]

# Docstrings use the NumPy style, with sections such as "Parameters".
napoleon_google_docstring = False
napoleon_numpy_docstring = True
autodoc_member_order = "bysource"
# Show types in the list of options, rather than in one long line at the top.
autodoc_typehints = "description"
autodoc_typehints_description_target = "documented"

html_theme = "pydata_sphinx_theme"
html_title = f"epiplot {release}"
html_theme_options = {
    "github_url": "https://github.com/leehart3000/epiplot",
    "navigation_with_keys": False,
    "logo": {"text": html_title},
}
html_sidebars = {"**": []}  # no left sidebar: epiplot's pages have no sub-pages yet
html_static_path = ["_static"]
html_logo = "_static/epiplot-logo.svg"
html_favicon = "_static/epiplot-logo.svg"
