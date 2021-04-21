# -*- coding: utf-8 -*-

import os
import re
import uuid
import unicodedata

from pyramid import exceptions as pyramid_exceptions


_filename_ascii_strip_re = re.compile(r'[^A-Za-z0-9_.-]')
_windows_device_files = ('CON', 'AUX', 'COM1', 'COM2', 'COM3', 'COM4', 'LPT1',
                         'LPT2', 'LPT3', 'PRN', 'NUL')


def secure_filename(filename):
    """
    This is a port of :meth:`werkzeug.utils.secure_filename` with
    python 3.2 compatibility.

    :param filename: the filename to secure
    """
    if isinstance(filename, str):
        filename = unicodedata.normalize(
            'NFKD', filename).encode('ascii', 'ignore')
        filename = filename.decode('ascii')
    for sep in os.path.sep, os.path.altsep:
        if sep:
            filename = filename.replace(sep, ' ')
    filename = str(_filename_ascii_strip_re.sub('', '_'.join(
                   filename.split()))).strip('._')

    # on nt a couple of special files are present in each folder. We
    # have to ensure that the target file is not such a filename. In
    # this case we prepend an underline
    if (os.name == 'nt' and filename and filename.split('.')[0].upper() in _windows_device_files):
        filename = '_' + filename

    return filename


def random_filename(filename):
    """Generates a randomized (uuid4) filename,
    preserving the original extension.

    :param filename: the original filename
    """
    _, ext = os.path.splitext(filename)
    return str(uuid.uuid4()) + ext.lower()


def read_settings(settings, options, prefix=''):
    """Reads the `settings` dictionnary, and sets defaults using the
    provided list of tuples in `options`.

    :param settings: settings to read.
    :param options: a list of tuples (name, required, default).
    :param prefix: prefix for the settings keys.
    :returns: a dictionnary with defaults set.
    :raises: :exc:`~pyramid:pyramid.exceptions.ConfigurationError` if a
        required setting is not provided.
    """
    result = {}
    for name, required, default in options:
        setting = prefix + name
        try:
            result[name] = settings[setting]
        except KeyError:
            if required:
                error_msg = "%s is required" % setting
                raise pyramid_exceptions.ConfigurationError(error_msg)
            result[name] = default
    return result
