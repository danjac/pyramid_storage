# -*- coding: utf-8 -*-

import os
import mimetypes

from pyramid import compat
from pyramid.settings import asbool
from zope.interface import implementer

from . import utils
from .exceptions import FileNotAllowed
from .extensions import resolve_extensions
from .interfaces import IFileStorage
from .registry import register_file_storage_impl

try:
    import aioboto3 as boto3

    # aioboto3 uses aiobotocore, which uses botocore
    from aiobotocore.config import AioConfig
    from botocore import exceptions
except ImportError:
    # If any of the imports fail, set the globals
    boto3 = None
    AioConfig = None
    exceptions = None

try:
    # The aiofile library is needed if opening local files (when using
    # save_filename)
    from aiofile import async_open
except ImportError:
    async_open = None


def includeme(config):
    if boto3 is None:
        raise RuntimeError("You must have aioboto3 installed to use s3 async")

    impl = S3AsyncFileStorage.from_settings(
        config.registry.settings, prefix='storage.'
    )

    register_file_storage_impl(config, impl)


@implementer(IFileStorage)
class S3AsyncFileStorage(object):
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
            ('aws.num_retries', False, 5),
            ('aws.timeout', False, 5),
            ('aws.read_timeout', False, 10),
            # aiobotocore additional options
            # AWS has a 20 second idle timeout:
            # https://forums.aws.amazon.com/message.jspa?messageID=215367
            # and aiohttp default timeout is 30s so we set it to something
            # aiobotocore default is 12
            ('aws.keepalive_timeout', False, 12),
        )
        kwargs = utils.read_settings(settings, options, prefix)
        kwargs = dict([(k.replace('aws.', ''), v) for k, v in kwargs.items()])

        return cls(**kwargs)

    def __init__(
        self,
        bucket_name,
        acl=None,
        base_url='',
        extensions='default',
        **connection_parameters
    ):
        self.bucket_name = bucket_name
        self.acl = acl
        self.base_url = base_url
        self.extensions = resolve_extensions(extensions)
        self.connection_parameters = connection_parameters
        self._conn_options = None

    @property
    def conn_options(self):
        '''Lazily create the connection options.'''
        if not self._conn_options:
            self._conn_options = self._get_connection_options(
                **self.connection_parameters
            )

        return self._conn_options

    @classmethod
    def _make_aioconfig(
        cls,
        num_retries=None,
        timeout=None,
        read_timeout=None,
        region=None,
        use_dns_cache=None,
        keepalive_timeout=None,
        force_close=None,
        use_path_style=False,
    ):
        """Create an AioConfig object (derived from botocore.config.Config)
        for use with a client or resource for aioboto3.
        """
        if AioConfig is None:
            raise RuntimeError(
                "You must have aioboto3 installed to use s3 async"
            )

        num_retries = int(num_retries)
        timeout = float(timeout)
        read_timeout = float(read_timeout)

        keepalive_timeout = float(keepalive_timeout)
        addressing_style = 'path' if use_path_style else 'auto'

        return AioConfig(
            connect_timeout=timeout,
            read_timeout=read_timeout,
            region_name=region,
            connector_args={
                'keepalive_timeout': keepalive_timeout,
            },
            retries={
                'max_attempts': num_retries,
            },
            s3={
                'addressing_style': addressing_style,
            },
        )

    @classmethod
    def _get_connection_options(
        cls,
        is_secure=True,
        host=None,
        port=None,
        secret_key=None,
        access_key=None,
        **kwargs  # additional args are passed to the AioConfig
    ):
        """Parses the kwargs provided for the client and returns the kwargs
        the client or resource needs for boto3/aioboto3.
        """
        result = {
            'config': cls._make_aioconfig(**kwargs),
            'aws_access_key_id': access_key,
            'aws_secret_access_key': secret_key,
        }

        if host is not None and not kwargs.get('region'):
            protocol = 'https://' if asbool(is_secure) else 'http://'
            parts = [protocol, host]
            if port is not None:
                parts.append(':')
                parts.append(str(port))
            result['endpoint_url'] = ''.join(parts)

        return result

    def s3_resource(self):
        """Return an async context manager for interacting with S3.

        Use like:
            async with request.storage.s3_resource() as s3:
                # do stuff
                pass

        The connection is automatically closed at the end of the block.
        """
        if boto3 is None:
            raise RuntimeError(
                "You must have aioboto3 installed to use s3 async"
            )

        return boto3.resource('s3', **self.conn_options)

    def s3_client(self):
        """Return an async context manager for for a lower-level S3 client."""
        if boto3 is None:
            raise RuntimeError(
                "You must have aioboto3 installed to use s3 async"
            )

        return boto3.client('s3', **self.conn_options)

    async def get_bucket(self, s3_resource):
        """Given an s3 resource, returns the bucket.

        Use like:
            async with request.storage.s3_resource() as s3:
                bucket = await request.storage.get_bucket(s3)
                # do stuff

        :param s3_resource: an opened s3_resource
        """
        return await s3_resource.Bucket(self.bucket_name)

    def url(self, filename):
        """Returns entire URL of the filename, joined to the base_url

        :param filename: base name of file
        """
        return compat.urlparse.urljoin(self.base_url, filename)

    async def exists(self, filename):
        """Determine if a file exists.
        This uses the head_object call on an S3 client to keep the server
        costs as low as possible.

        :param filename: name of the file
        """
        if exceptions is None:
            raise RuntimeError(
                "You must have aioboto3 installed to use s3 async"
            )

        async with self.s3_client() as s3_client:
            try:
                await s3_client.head_object(
                    Bucket=self.bucket_name, Key=filename
                )
            except exceptions.ClientError as err:
                if int(err.response.get('Error', {}).get('Code')) == 404:
                    return False
                raise

            return True

    async def delete(self, filename):
        """Deletes the filename. Filename is resolved with the
        absolute path based on base_path.

        Always succeeds, even if file does not exist.

        :param filename: base name of file
        """
        async with self.s3_resource() as s3:
            file_object = await s3.Object(self.bucket_name, filename)
            await file_object.delete()

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

    async def save(self, fs, *args, **kwargs):
        """Saves contents of a **cgi.FieldStorage** object to the file system.
        Returns modified filename(including folder).

        Returns the resolved filename, i.e. the folder + (modified/randomized)
        filename.

        :param fs: **cgi.FieldStorage** object (or similar). Can be a coroutine
        :param folder: relative path of sub-folder
        :param randomize: randomize the filename
        :param extensions: iterable of allowed extensions, if not default
        :param acl: ACL policy (if None then uses default)
        :param replace: replace existing key
        :param headers: dict of s3 request headers
        :returns: modified filename
        """
        return await self.save_file(fs.file, fs.filename, *args, **kwargs)

    async def save_filename(self, filename, *args, **kwargs):
        """Saves a filename in local filesystem to the uploads location.
        Requires the aiofile library to be installed.

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
        if async_open is None:
            raise RuntimeError(
                "You must have aiofile installed to use S3 async save_filename"
            )

        return await self.save_file(
            async_open(filename, "rb"), filename, *args, **kwargs
        )

    async def save_file(
        self,
        file,
        filename,
        folder=None,
        randomize=False,
        extensions=None,
        acl=None,
        replace=False,
        headers=None,
    ):
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

        filename = utils.secure_filename(os.path.basename(filename))

        if randomize:
            filename = utils.random_filename(filename)

        if folder:
            filename = folder + "/" + filename

        content_type = headers.get('Content-Type')
        if content_type is None:
            content_type, _ = mimetypes.guess_type(filename)
            content_type = content_type or 'application/octet-stream'

        async with self.s3_resource() as s3:
            bucket = await self.get_bucket(s3)

            file.seek(0)

            await bucket.upload_fileobj(
                file,
                filename,
                ExtraArgs={
                    'ACL': acl,
                    'ContentType': content_type,
                },
            )

        return filename
