import os
import sys
import django

sys.path.insert(0, os.path.abspath('..')) 
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings' 
os.environ['USE_SQLITE'] = 'True'

from sphinx.util import inspect as sphinx_inspect
original_object_description = sphinx_inspect.object_description

def safe_object_description(obj, *args, **kwargs):
    try:
        return original_object_description(obj, *args, **kwargs)
    except ValueError:
        return str(obj) 

sphinx_inspect.object_description = safe_object_description

django.setup()
from django.core.management import call_command
try:
    call_command('migrate', interactive=False)
except Exception:
    pass



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
