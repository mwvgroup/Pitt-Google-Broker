# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# -- Path setup --------------------------------------------------------------
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# -- Project information -----------------------------------------------------

project = 'Pitt-Google Broker'
copyright = '2021, The Pitt-Google Broker Team'
author = 'The Pitt-Google Broker Team'

# The full version, including alpha/beta/rc tags
release = 'v0.5.0'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'myst_parser',
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.autodoc',
    'sphinx.ext.coverage',
    'sphinx.ext.mathjax',
    'sphinx.ext.viewcode',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx_autodoc_typehints',
    'sphinx_copybutton'
]

# Make sure the target is unique
autosectionlabel_prefix_document = True
# now can reference pages with :ref:`{path/to/page}:{title-of-section}`

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
source_suffix = ['.md', '.rst']

# The master toctree document.
master_doc = 'index'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']


# Make list-tables wrap instead of forcing a scrollbar
# https://knowyourtoolset.com/2018/02/controlling-the-width-of-a-table-with-read-the-docs/
# but add_stylesheet() -> add_css_file()
def setup(app):
    app.add_css_file('css/custom.css')
