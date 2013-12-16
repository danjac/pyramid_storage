# -*- coding: utf-8 -*-

import os
import re
import shutil
import uuid
import unicodedata


from zope.interface import implementer

from . import _compat
from .exceptions import FileNotAllowed
from .interfaces import IFileStorage


TEXT = ('txt',)
DOCUMENTS = tuple('rtf odf ods gnumeric abw doc docx xls xls'.split())
IMAGES = tuple('jpg jpe jpeg png gif svg bmp tiff'.split())
AUDIO = tuple('wav mp3 aac ogg oga flac'.split())
VIDEO = tuple('mpeg 3gp avi divx dvr flv mp4 wmv'.split())
DATA = tuple('csv ini json plist xml yaml yml'.split())
SCRIPTS = tuple('js php pl py rb sh'.split())
ARCHIVES = tuple('gz bz2 zip tar tgz txz 7z'.split())
EXECUTABLES = tuple('so exe dll'.split())
DEFAULT = DOCUMENTS + TEXT + IMAGES + DATA

GROUPS = dict((
    ('documents', DOCUMENTS),
    ('text', TEXT),
    ('images', IMAGES),
    ('audio', AUDIO),
    ('video', VIDEO),
    ('data', DATA),
    ('scripts', SCRIPTS),
    ('archives', ARCHIVES),
    ('executables', EXECUTABLES),
    ('default', DEFAULT)
))

_filename_ascii_strip_re = re.compile(r'[^A-Za-z0-9_.-]')
_windows_device_files = ('CON', 'AUX', 'COM1', 'COM2', 'COM3', 'COM4', 'LPT1',
                         'LPT2', 'LPT3', 'PRN', 'NUL')


def secure_filename(filename):
    """
    This is a port of :meth:`werkzeug.utils.secure_filename` with
    python 3.2 compatibility.

    :param filename: the filename to secure
    """
    if isinstance(filename, _compat.text_type):
        filename = unicodedata.normalize(
            'NFKD', filename).encode('ascii', 'ignore')
        if _compat.PY3:
            filename = filename.decode('ascii')
    for sep in os.path.sep, os.path.altsep:
        if sep:
            filename = filename.replace(sep, ' ')
    filename = str(_filename_ascii_strip_re.sub('', '_'.join(
                   filename.split()))).strip('._')

    # on nt a couple of special files are present in each folder. We
    # have to ensure that the target file is not such a filename. In
    # this case we prepend an underline
    if (os.name == 'nt' and filename and
       filename.split('.')[0].upper() in _windows_device_files):
        filename = '_' + filename

    return filename


def resolve_extensions(extensions):
    """
    Splits extensions string into a set of extensions
    ("jpg", "png" etc). If extensions string contains
    a known group e.g. "images" then fetches extensions
    for that group. Separate groups with "+".

    :param extensions: a string of extensions and/or group names
    """
    rv = set()
    groups = extensions.split('+')
    for group in groups:
        if group in GROUPS:
            rv.update(GROUPS[group])
        else:
            for ext in group.split():
                rv.add(ext.lower())
    return rv


def random_filename(filename):
    """Generates a randomized (uuid4) filename,
    preserving the original extension.

    :param filename: the original filename
    """
    _, ext = os.path.splitext(filename)
    return str(uuid.uuid4()) + ext.lower()


@implementer(IFileStorage)
class FileStorage(object):

    """Manages storage and retrieval of file uploads.

    :param base_path: the absolute base path where uploads are stored
    :param base_url: absolute or relative base URL for uploads
    :param extensions: extensions string
    """

    @classmethod
    def from_settings(cls, settings, prefix):
        """Returns a new instance from config settings.

        :param settings: dict(-like) of settings
        :param prefix: prefix separating these settings
        """
        options = (
            ('base_path', True, None),
            ('base_url', False, ''),
            ('extensions', False, 'default'),
        )

        kwargs = {}

        for name, required, default in options:
            try:
                kwargs[name] = settings[prefix + name]
            except KeyError:
                if required:
                    raise ValueError("%s%s is required" % (prefix, name))
                kwargs[name] = default

        return cls(**kwargs)

    def __init__(self, base_path, base_url='', extensions='default'):
        self.base_path = base_path
        self.base_url = base_url
        self.extensions = resolve_extensions(extensions)

    def url(self, filename):
        """Returns entire URL of the filename, joined to the base_url

        :param filename: base name of file
        """
        return _compat.urlparse.urljoin(self.base_url, filename)

    def path(self, filename):
        """Returns absolute file path of the filename, joined to the
        base_path.

        :param filename: base name of file
        """
        return os.path.join(self.base_path, filename)

    def delete(self, filename):
        """Deletes the filename. Filename is resolved with the
        absolute path based on base_path. If file does not exist,
        returns **False**, otherwise **True**

        :param filename: base name of file
        """
        if self.exists(filename):
            os.remove(self.path(filename))
            return True
        return False

    def exists(self, filename):
        """Checks if file exists. Resolves filename's absolute
        path based on base_path.

        :param filename: base name of file
        """
        return os.path.exists(self.path(filename))

    def file_allowed(self, fs, extensions=None):
        """Checks if a file can be saved, based on extensions

        :param fs: **cgi.FileStorage** object or similar
        :param extensions: iterable of extensions (or self.extensions)
        """
        _, ext = os.path.splitext(fs.filename)
        return self.extension_allowed(ext, extensions)

    def extension_allowed(self, ext, extensions=None):
        """Checks if an extension is permitted. Both e.g. ".jpg" and
        "jpg" can be passed in. Extension lookup is case-insensitive.

        :param extensions: iterable of extensions (or self.extensions)
        """

        extensions = extensions or self.extensions
        if ext.startswith('.'):
            ext = ext[1:]
        return ext.lower() in extensions

    def save(self, fs, folder=None, randomize=False, extensions=None):
        """Saves contents of a **cgi.FileStorage** object to the file system.
        Returns modified filename(including folder). If there is a clash
        with an existing filename then filename
        will be resolved accordingly. If path directories do not exist
        they will be created.

        Returns the resolved filename, i.e. the folder +
        the (randomized/incremented) base name.

        :param fs: **cgi.FileStorage** object (or similar)
        :param folder: relative path of sub-folder
        :param randomize: randomize the filename
        :param extensions: iterable of allowed extensions, if not default
        """

        extensions = extensions or self.extensions

        if not self.file_allowed(fs, extensions):
            raise FileNotAllowed()

        filename = secure_filename(
            os.path.basename(fs.filename)
        )

        if folder:
            dest_folder = os.path.join(self.base_path, folder)
        else:
            dest_folder = self.base_path

        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)

        if randomize:
            filename = random_filename(filename)

        filename, path = self.resolve_name(filename, dest_folder)

        fs.file.seek(0)

        with open(path, "wb") as dest:
            shutil.copyfileobj(fs.file, dest)

        if folder:
            filename = os.path.join(folder, filename)

        return filename

    def resolve_name(self, name, folder):
        """Resolves a unique name and the correct path. If a filename
        for that path already exists then a numeric prefix will be
        added, for example test.jpg -> test-1.jpg etc.
        :param name: base name of file
        :param folder: absolute folder path
        """
        basename, ext = os.path.splitext(name)
        counter = 0
        while True:
            path = os.path.join(folder, name)
            if not os.path.exists(path):
                return name, path
            counter += 1
            name = '%s-%d%s' % (basename, counter, ext)


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
