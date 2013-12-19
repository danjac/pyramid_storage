import os


class DummyFileStorage(object):
    """A fake file storage object for testing. Instead of
    saving to file the filename is added to a list"""

    def __init__(self):
        self.saved = []

    def save(self, fs, folder=None, *args, **kwargs):
        """Performs a fake saved operation"""
        filename = fs.filename
        name = os.path.join(folder or '', filename)
        self.saved.append(name)
        return name
