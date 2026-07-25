import os
import sys
import django

sys.path.insert(0, os.path.abspath('..')) 


os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings' 
os.environ['USE_SQLITE'] = 'True'

django.setup()


project = 'wills_news'
copyright = '2026, Will'
author = 'Will'
release = '1.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'alabaster'
html_static_path = ['_static']
