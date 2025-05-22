import os
import sys
sys.path.insert(0, os.path.abspath('..'))

project = 'tracksuite'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinxcontrib.autoprogram',
]

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'alabaster'
