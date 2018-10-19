# -*- coding: utf-8 -*-

import os
import mimetypes
import tempfile
import uuid

from pyramid import compat
from pyramid.settings import asbool
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
        options = (
            ('aws.bucket_name', True, None),
            ('aws.acl', False, 'public-read'),
            ('base_url', False, ''),
            ('extensions', False, 'default'),
            # S3 Connection options.
            ('aws.access_key', False, None),
            ('aws.secret_key', False, None),
            ('aws.use_path_style', False, False),
            ('aws.is_secure', False, True),
            ('aws.host', False, None),
            ('aws.port', False, None),
            ('aws.region', False, None),
            ('aws.num_retries', False, 1),
            ('aws.timeout', False, 5),
        )
        kwargs = utils.read_settings(settings, options, prefix)
        kwargs = dict([(k.replace('aws.', ''), v) for k, v in kwargs.items()])
        kwargs['aws_access_key_id'] = kwargs.pop('access_key')
        kwargs['aws_secret_access_key'] = kwargs.pop('secret_key')
        return cls(**kwargs)

    def __init__(self, bucket_name, acl=None, base_url='',
                 extensions='default', **conn_options):
        self.bucket_name = bucket_name
        self.acl = acl
        self.base_url = base_url
        self.extensions = resolve_extensions(extensions)
        self.conn_options = conn_options

    def get_connection(self):
        try:
            import boto
        except ImportError:
            raise RuntimeError("You must have boto installed to use s3")

        from boto.s3.connection import OrdinaryCallingFormat
        from boto.s3 import connect_to_region

        options = self.conn_options.copy()
        options['is_secure'] = asbool(options['is_secure'])

        if options['port']:
            options['port'] = int(options['port'])
        else:
            del options['port']

        if not options['host']:
            del options['host']

        if asbool(options.pop('use_path_style')):
            options['calling_format'] = OrdinaryCallingFormat()

        num_retries = int(options.pop('num_retries'))
        timeout = float(options.pop('timeout'))

        region = options.pop('region')
        if region:
            del options['host']
            del options['port']
            conn = connect_to_region(region, **options)
        else:
            conn = boto.connect_s3(**options)

        conn.num_retries = num_retries
        conn.http_connection_kwargs['timeout'] = timeout
        return conn

    def get_resource(self):

        try:
            import boto3
        except ImportError:
            raise RuntimeError("You must have boto3 installed to use s3 with boto3 support")
        from botocore.client import Config

        options = self.conn_options.copy()

        resource = boto3.resource('s3',
                                  endpoint_url='{}:{}'.format(options['host'], options['port']),
                                  aws_access_key_id=options['aws_access_key_id'],
                                  aws_secret_access_key=options['aws_secret_access_key'],
                                  config=Config(signature_version=options['signature_version']),
                                  region_name=options['region'])

        return resource

    def get_bucket(self):
        if self.conn_options.get('boto3'):
            return self.get_resource().Bucket(self.bucket_name)

        return self.get_connection().get_bucket(self.bucket_name)

    def url(self, filename):
        """Returns entire URL of the filename, joined to the base_url

        :param filename: base name of file
        """
        return compat.urlparse.urljoin(self.base_url, filename)

    def open(self, filename, *args):
        """Return filelike object stored
        """

        bucket = self.get_bucket()
        key = bucket.get_key(filename) or bucket.new_key(filename)

        f = tempfile.NamedTemporaryFile(delete=False)
        f.close()
        key.get_contents_to_filename(f.name)

        return open(f.name, *args)

    def exists(self, filename):
        return self.get_bucket().new_key(filename).exists()

    def delete(self, filename):
        """Deletes the filename. Filename is resolved with the
        absolute path based on base_path. If file does not exist,
        returns **False**, otherwise **True**

        :param filename: base name of file
        """
        self.get_bucket().delete_key(filename)

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
        Returns modified filename(including folder).

        Returns the resolved filename, i.e. the folder + (modified/randomized)
        filename.

        :param fs: **cgi.FieldStorage** object (or similar)
        :param folder: relative path of sub-folder
        :param randomize: randomize the filename
        :param extensions: iterable of allowed extensions, if not default
        :param acl: ACL policy (if None then uses default)
        :param replace: replace existing key
        :param headers: dict of s3 request headers
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
        :param acl: ACL policy (if None then uses default)
        :param replace: replace existing key
        :param headers: dict of s3 request headers
        :returns: modified filename
        """

        return self.save_file(open(filename, "rb"), filename, *args, **kwargs)

    def save_file(self, file, filename, folder=None, randomize=False,
                  extensions=None, acl=None, replace=False, headers=None, partition_sub_dir=False):
        """
        :param filename: local filename
        :param folder: relative path of sub-folder
        :param randomize: randomize the filename
        :param extensions: iterable of allowed extensions, if not default
        :param acl: ACL policy (if None then uses default)
        :param replace: replace existing key
        :param headers: dict of s3 request headers
        :returns: modified filename
        """
        acl = acl or self.acl
        headers = headers or {}
        extensions = extensions or self.extensions

        if not self.filename_allowed(filename, extensions):
            raise FileNotAllowed()

        filename = utils.secure_filename(
            os.path.basename(filename)
        )

        if randomize:
            filename = utils.random_filename(filename)

        if folder:
            if partition_sub_dir:
                # This is a generic way to create sub directories. Using just the 3 first characters of an uuid is just
                # an alternative like using part of the epoch time...
                # As this is not a final solution, we are using it as simple as possible...
                folder = '{}/{}'.format(folder, uuid.uuid4().hex[0:3])
            filename = folder + "/" + filename

        content_type, _ = mimetypes.guess_type(filename)
        content_type = content_type or 'application/octet-stream'

        headers.update({
            'Content-Type': content_type,
        })

        bucket = self.get_bucket()

        key = bucket.get_key(filename) or bucket.new_key(filename)
        key.set_metadata('Content-Type', content_type)

        file.seek(0)

        key.set_contents_from_file(file,
                                   headers=headers,
                                   policy=acl,
                                   replace=replace,
                                   rewind=True)

        return filename

    def path(self, filename):
        """Returns absolute file path of the filename, joined to the
        base_path.

        :param filename: base name of file
        """
        raise NotImplementedError()

    def resolve_name(self, name, folder):
        """Resolves a unique name and the correct path. If a filename
        for that path already exists then a numeric prefix will be
        added, for example test.jpg -> test-1.jpg etc.

        :param name: base name of file
        :param folder: absolute folder path
        """
        raise NotImplementedError()

    def get_files_list(self, folder):
        """
        Get a list of files from current folder
        :param folder:
        :return:
        """
        bucket = self.get_bucket()
        files_list = [key.name for key in bucket.list(prefix='{}/'.format(folder), delimiter='/')]

        return files_list
