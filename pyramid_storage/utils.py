# -*- coding: utf-8 -*-

import os
import re
import uuid
import unicodedata

from pyramid import compat


_filename_ascii_strip_re = re.compile(r'[^A-Za-z0-9_.-]')
_windows_device_files = ('CON', 'AUX', 'COM1', 'COM2', 'COM3', 'COM4', 'LPT1',
                         'LPT2', 'LPT3', 'PRN', 'NUL')


def secure_filename(filename):
    """
    This is a port of :meth:`werkzeug.utils.secure_filename` with
    python 3.2 compatibility.

    :param filename: the filename to secure
    """
    if isinstance(filename, compat.text_type):
        filename = unicodedata.normalize(
            'NFKD', filename).encode('ascii', 'ignore')
        if compat.PY3:
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


def random_filename(filename):
    """Generates a randomized (uuid4) filename,
    preserving the original extension.

    :param filename: the original filename
    """
    _, ext = os.path.splitext(filename)
    return str(uuid.uuid4()) + ext.lower()
