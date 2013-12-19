# -*- coding: utf-8 -*-

import os
import mimetypes

from pyramid import compat
from zope.interface import implementer

from . import utils
from .exceptions import FileNotAllowed
from .extensions import resolve_extensions
from .interfaces import IFileStorage
from .registry import register_file_storage_impl


def includeme(config):

    impl = S3FileStorage.from_settings(
        config.registry.settings, prefix='storage.'
    )

    register_file_storage_impl(config, impl)


@implementer(IFileStorage)
class S3FileStorage(object):

    @classmethod
    def from_settings(cls, settings, prefix):
        return cls(access_key=settings[prefix + 'aws.access_key'],
                   secret_key=settings[prefix + 'aws.secret_key'],
                   bucket_name=settings[prefix + 'aws.bucket'],
                   acl=settings.get(prefix + 'aws.default_acl', 'public-read'),
                   base_url=settings.get('base_url', ''),
                   extensions=settings.get(prefix + 'extensions', 'default'))

    def __init__(self, access_key, secret_key, bucket_name,
                 acl=None, base_url='', extensions='default'):
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.acl = acl
        self.extensions = resolve_extensions(extensions)

    def get_connection(self):
        try:
            from boto.s3.connection import S3Connection
        except ImportError:
            raise RuntimeError("You must have boto installed to use s3")
        return S3Connection(self.access_key, self.secret_key)

    def get_bucket(self):
        return self.get_connection().get_bucket(self.bucket_name)

    def url(self, filename):
        """Returns entire URL of the filename, joined to the base_url

        :param filename: base name of file
        """
        return compat.urlparse.urljoin(self.base_url, filename)

    def exists(self, filename):
        return self.get_bucket().new_key(filename).exists()

    def delete(self, filename):
        """Deletes the filename. Filename is resolved with the
        absolute path based on base_path. If file does not exist,
        returns **False**, otherwise **True**

        :param filename: base name of file
        """
        self.get_bucket().delete_key(filename)

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

    def save(self, fs, folder=None, randomize=False, extensions=None,
             acl=None, replace=False, headers=None):
        """Saves contents of a **cgi.FileStorage** object to the file system.
        Returns modified filename(including folder).

        Returns the resolved filename, i.e. the folder + (modified/randomized)
        filename.

        :param fs: **cgi.FileStorage** object (or similar)
        :param folder: relative path of sub-folder
        :param randomize: randomize the filename
        :param extensions: iterable of allowed extensions, if not default
        :param acl: ACL policy (if None then uses default)
        :param replace: replace existing key
        :param headers: dict of s3 request headers
        """

        acl = acl or self.acl
        headers = headers or {}
        extensions = extensions or self.extensions

        if not self.file_allowed(fs, extensions):
            raise FileNotAllowed()

        filename = utils.secure_filename(
            os.path.basename(fs.filename)
        )

        if randomize:
            filename = utils.random_filename(filename)

        if folder:
            filename = folder + "/" + filename

        content_type, _ = mimetypes.guess_type(filename)

        headers.update({
            'Content-Type': content_type,
        })

        key = self.get_bucket().get_key(
            filename) or self.bucket.new_key(filename)
        key.set_metadata('Content-Type', content_type)

        fs.file.seek(0)

        key.set_contents_from_file(fs.file,
                                   headers=headers,
                                   policy=acl,
                                   rewind=True)

        return filename
