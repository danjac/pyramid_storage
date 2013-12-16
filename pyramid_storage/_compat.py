import sys

PY3 = sys.version >= '3'

if PY3:
    import urllib

    urlparse = urllib.parse
    text_type = str

else:
    import urlparse
    text_type = unicode
