import os

from pyramid import compat


class DummyFileStorage(object):
    """A fake file storage object for testing. Instead of
    saving to file the filename is added to a list"""

    def __init__(self, base_url="http://www.example.com"):
        self.saved = []
        self.base_url = base_url

    def save(self, fs, folder=None, *args, **kwargs):
        """Performs a fake saved operation"""
        filename = fs.filename
        name = os.path.join(folder or '', filename)
        self.saved.append(name)
        return name

    def url(self, filename):
        """Return a fake URL"""
        return compat.urlparse.urljoin(self.base_url, filename)
