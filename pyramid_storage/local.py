# -*- coding: utf-8 -*-

import os
import shutil
import uuid

from pyramid import compat
from zope.interface import implementer

from . import utils
from .extensions import resolve_extensions
from .exceptions import FileNotAllowed
from .interfaces import IFileStorage
from .registry import register_file_storage_impl


def includeme(config):

    impl = LocalFileStorage.from_settings(
        config.registry.settings, prefix='storage.'
    )

    register_file_storage_impl(config, impl)


@implementer(IFileStorage)
class LocalFileStorage(object):

    """Manages storage and retrieval of file uploads to local
    filesystem on server.

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
        kwargs = utils.read_settings(settings, options, prefix)
        return cls(**kwargs)

    def __init__(self, base_path, base_url='', extensions='default'):
        self.base_path = base_path
        self.base_url = base_url
        self.extensions = resolve_extensions(extensions)

    def url(self, filename):
        """Returns entire URL of the filename, joined to the base_url

        :param filename: base name of file
        """
        return compat.urlparse.urljoin(self.base_url, filename)

    def path(self, filename):
        """Returns absolute file path of the filename, joined to the
        base_path.

        :param filename: base name of file
        """
        return os.path.join(self.base_path, filename)

    def open(self, filename, *args):
        """Return filelike object stored
        """
        return open(self.path(filename), *args)

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

    def filename_allowed(self, filename, extensions=None):
        """Checks if a filename has an allowed extension

        :param filename: base name of file
        :param extensions: iterable of extensions (or self.extensions)
        """
        _, ext = os.path.splitext(filename)
        return self.extension_allowed(ext, extensions)

    def file_allowed(self, fs, extensions=None):
        """Checks if a file can be saved, based on extensions

        :param fs: **cgi.FieldStorage** object or similar
        :param extensions: iterable of extensions (or self.extensions)
        """
        return self.filename_allowed(fs.filename, extensions)

    def extension_allowed(self, ext, extensions=None):
        """Checks if an extension is permitted. Both e.g. ".jpg" and
        "jpg" can be passed in. Extension lookup is case-insensitive.

        :param extensions: iterable of extensions (or self.extensions)
        """

        extensions = extensions or self.extensions
        if not extensions:
            return True
        if ext.startswith('.'):
            ext = ext[1:]
        return ext.lower() in extensions

    def save(self, fs, *args, **kwargs):
        """Saves contents of a **cgi.FieldStorage** object to the file system.
        Returns modified filename(including folder). If there is a clash
        with an existing filename then filename
        will be resolved accordingly. If path directories do not exist
        they will be created.

        Returns the resolved filename, i.e. the folder +
        the (randomized/incremented) base name.

        :param fs: **cgi.FieldStorage** object (or similar)
        :param folder: relative path of sub-folder
        :param randomize: randomize the filename
        :param extensions: iterable of allowed extensions, if not default
        :returns: modified filename
        """
        return self.save_file(fs.file, fs.filename, *args, **kwargs)

    def save_filename(self, filename, *args, **kwargs):
        """Saves a filename in local filesystem to the uploads location.

        Returns the resolved filename, i.e. the folder +
        the (randomized/incremented) base name.

        :param filename: local filename
        :param folder: relative path of sub-folder
        :param randomize: randomize the filename
        :param extensions: iterable of allowed extensions, if not default
        :returns: modified filename
        """

        return self.save_file(open(filename, "rb"), filename, *args, **kwargs)

    def save_file(self, file, filename, folder=None, randomize=False,
                  extensions=None, partition_sub_dir=False, **kwargs):
        """Saves a file object to the uploads location.
        Returns the resolved filename, i.e. the folder +
        the (randomized/incremented) base name.

        :param fs: **cgi.FieldStorage** object (or similar)
        :param filename: original filename
        :param folder: relative path of sub-folder
        :param randomize: randomize the filename
        :param extensions: iterable of allowed extensions, if not default
        :returns: modified filename
        """

        extensions = extensions or self.extensions

        if not self.filename_allowed(filename, extensions):
            raise FileNotAllowed()

        filename = utils.secure_filename(
            os.path.basename(filename)
        )

        if folder:
            if partition_sub_dir:
                # This is a generic way to create sub directories. Using just the 3 first characters of an uuid is just an
                # alternative like using part of the epoch time...
                # As this is not a final solution, we are using it as simple as possible...
                folder = '{}/{}'.format(folder, uuid.uuid4().hex[0:3])
            dest_folder = os.path.join(self.base_path, folder)
        else:
            dest_folder = self.base_path

        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)

        if randomize:
            filename = utils.random_filename(filename)

        filename, path = self.resolve_name(filename, dest_folder)

        file.seek(0)

        with open(path, "wb") as dest:
            shutil.copyfileobj(file, dest)

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

    def get_files_list(self, folder):
        """
        Get a list of files from current folder
        :param folder:
        :return:
        """

        if folder:
            dest_folder = os.path.join(self.base_path, folder)
        else:
            dest_folder = self.base_path

        if not os.path.exists(dest_folder):
            return

        return os.listdir(dest_folder)
