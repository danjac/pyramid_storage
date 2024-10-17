# -*- coding: utf-8 -*-

import mimetypes
import os
import urllib

from pyramid.settings import asbool
from zope.interface import implementer

from . import utils
from .exceptions import FileNotAllowed
from .extensions import resolve_extensions
from .interfaces import IFileStorage
from .registry import register_file_storage_impl


def includeme(config):
    impl = S3FileStorage.from_settings(config.registry.settings, prefix="storage.")

    register_file_storage_impl(config, impl)


@implementer(IFileStorage)
class S3FileStorage(object):
    @classmethod
    def from_settings(cls, settings, prefix):
        options = (
            ("aws.bucket_name", True, None),
            ("aws.acl", False, "public-read"),
            ("base_url", False, ""),
            ("extensions", False, "default"),
            # S3 Connection options.
            ("aws.access_key", False, None),
            ("aws.secret_key", False, None),
            ("aws.use_path_style", False, False),
            ("aws.is_secure", False, True),
            ("aws.host", False, None),
            ("aws.port", False, None),
            ("aws.region", False, None),
            ("aws.num_retries", False, 1),
            ("aws.timeout", False, 5),
        )
        kwargs = utils.read_settings(settings, options, prefix)
        kwargs = dict([(k.replace("aws.", ""), v) for k, v in kwargs.items()])
        kwargs["aws_access_key_id"] = kwargs.pop("access_key")
        kwargs["aws_secret_access_key"] = kwargs.pop("secret_key")
        return cls(**kwargs)

    def __init__(self, bucket_name, acl=None, base_url="", extensions="default", **conn_options):
        self.bucket_name = bucket_name
        self.acl = acl
        self.base_url = base_url
        self.extensions = resolve_extensions(extensions)
        self.conn_options = conn_options

    @property
    def s3_client(self):
        try:
            import boto3
        except ImportError:
            raise RuntimeError("You must have boto3 installed to use s3")
        from botocore.config import Config
        from botocore.exceptions import NoCredentialsError

        timeout = float(self.conn_options.pop("timeout"))
        conn_config = {"connect_timeout": timeout}

        num_retries = int(self.conn_options.pop("num_retries"))
        if num_retries > 1:
            conn_config["retries"] = {"max_attempts": num_retries, "mode": "standard"}
        if asbool(self.conn_options.get("use_path_style")):
            conn_config["s3"] = {"addressing_style": "path"}

        client_kwargs = {
            "aws_access_key_id": self.conn_options.get("aws_access_key_id"),
            "aws_secret_access_key": self.conn_options.get("aws_secret_access_key"),
        }
        if self.conn_options["region"] is not None:
            client_kwargs["region_name"] = self.conn_options.get("region")
        else:
            protocol = "http" if self.conn_options.get("is_secure") else "https"
            host = self.conn_options["host"]
            port = self.conn_options["port"]
            client_kwargs["endpoint"] = f"{protocol}://{host}:{port}"

        try:
            return boto3.client(
                "s3",
                config=Config(**conn_config),
                **client_kwargs,
            )
        except NoCredentialsError:
            raise RuntimeError("AWS credentials are missing or incorrect")

    def url(self, filename):
        """Returns entire URL of the filename, joined to the base_url

        :param filename: base name of file
        """
        return urllib.parse.urljoin(self.base_url, filename)

    def exists(self, filename, bucket_name=None):
        try:
            self.s3_client.head_object(Bucket=bucket_name or self.bucket_name, Key=filename)
            return True
        except self.s3_client.exceptions.ClientError:
            return False

    def delete(self, filename, bucket_name=None):
        """Deletes the filename. Filename is resolved with the
        absolute path based on base_path. If file does not exist,
        returns **False**, otherwise **True**

        :param filename: base name of file
        :param bucket_name: name of the bucket, if not default
        """
        self.s3_client.delete_object(Bucket=bucket_name or self.bucket_name, Key=filename)

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
        if ext.startswith("."):
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

    def save_file(
        self,
        file,
        filename,
        folder=None,
        bucket_name=None,
        randomize=False,
        extensions=None,
        acl=None,
        replace=False,
        headers=None,
    ):
        """
        :param filename: local filename
        :param folder: relative path of sub-folder
        :param bucket_name: name of the bucket, if not default
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

        content_type = headers.get("Content-Type")
        if content_type is None:
            content_type, _ = mimetypes.guess_type(filename)
        content_type = content_type or "application/octet-stream"

        file.seek(0)

        self.s3_client.put_object(
            Bucket=bucket_name or self.bucket_name,
            Key=filename,
            Body=file,
            ACL=acl,
            ContentType=content_type,
        )
        return filename
