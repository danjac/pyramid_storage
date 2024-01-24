# -*- coding: utf-8 -*-

import mimetypes
import os
import urllib

from pyramid.exceptions import ConfigurationError
from pyramid.settings import asbool
from zope.interface import implementer

from . import utils
from .exceptions import FileNotAllowed
from .extensions import resolve_extensions
from .interfaces import IFileStorage
from .registry import register_file_storage_impl


try:
    from google.cloud.exceptions import NotFound
    from google.cloud.storage.blob import Blob
    from google.cloud.storage.client import Client
except ImportError:
    raise RuntimeError(
        "Could not load Google Cloud Storage bindings.\n"
        "See https://github.com/GoogleCloudPlatform/gcloud-python"
    )


def includeme(config):
    impl = GoogleCloudStorage.from_settings(config.registry.settings, prefix="storage.")

    register_file_storage_impl(config, impl)


DEFAULT_BUCKET_ACL = "projectPrivate"
DEFAULT_FILE_ACL = "publicRead"


@implementer(IFileStorage)
class GoogleCloudStorage(object):
    @classmethod
    def from_settings(cls, settings, prefix):
        options = (
            ("gcloud.credentials", False, None),
            ("gcloud.project", False, None),
            ("gcloud.bucket_name", True, None),
            ("gcloud.acl", False, None),
            ("base_url", False, ""),
            ("extensions", False, "default"),
            # Gcloud Connection options.
            ("gcloud.auto_create_bucket", False, False),
            ("gcloud.auto_create_acl", False, None),
            ("gcloud.cache_control", False, None),
            ("gcloud.uniform_bucket_level_access", False, False),
        )
        kwargs = utils.read_settings(settings, options, prefix)
        kwargs = dict([(k.replace("gcloud.", ""), v) for k, v in kwargs.items()])
        return cls(**kwargs)

    def __init__(
        self,
        credentials,
        bucket_name,
        project=None,
        acl=None,
        base_url="",
        extensions="default",
        auto_create_bucket=False,
        auto_create_acl=None,
        cache_control=None,
        uniform_bucket_level_access=False,
    ):
        if (acl or auto_create_acl) and uniform_bucket_level_access:
            raise ConfigurationError(
                '"acl" and "auto_create_acl" \
                        should remain unset \
                        when "uniform_bucket_level_access" \
                        is enabled!'
            )

        if not uniform_bucket_level_access:
            self.acl = acl or DEFAULT_FILE_ACL
            self.auto_create_acl = auto_create_acl or DEFAULT_BUCKET_ACL

        else:
            self.acl = acl
            self.auto_create_acl = auto_create_acl

        self.credentials = credentials
        self.project = project
        self.bucket_name = bucket_name
        self.base_url = base_url
        self.extensions = resolve_extensions(extensions)
        self.auto_create_bucket = auto_create_bucket
        self.cache_control = cache_control
        self.uniform_bucket_level_access = asbool(uniform_bucket_level_access)

        self._client = None
        self._bucket = None

    def get_connection(self):
        if self._client is None:
            if self.credentials:
                self._client = Client.from_service_account_json(
                    json_credentials_path=self.credentials
                )

            else:
                # empty credentials, try ADC
                if self.project:
                    self._client = Client(project=self.project)

                else:
                    self._client = Client()

        return self._client

    def get_bucket(self, bucket_name=None):
        if self._bucket is None:
            self._bucket = self._get_or_create_bucket(self.bucket_name)
        if bucket_name and bucket_name != self.bucket_name:
            return self._get_or_create_bucket(bucket_name)
        return self._bucket

    def _get_or_create_bucket(self, name):
        """
        Retrieves a bucket if it exists, otherwise creates it.
        """
        try:
            return self.get_connection().get_bucket(name)
        except NotFound:
            if self.auto_create_bucket:
                bucket = self.get_connection().create_bucket(name)

                if not self.uniform_bucket_level_access:
                    bucket.acl.save_predefined(self.auto_create_acl)

                return bucket
            raise RuntimeError(
                "Bucket %s does not exist. Buckets "
                "can be automatically created by "
                "setting GS_AUTO_CREATE_BUCKET to "
                "``True``." % name
            )

    def url(self, filename):
        """Returns entire URL of the filename, joined to the base_url

        :param filename: base name of file
        """
        return urllib.parse.urljoin(self.base_url, filename)

    def exists(self, name, bucket_name=None):
        if not name:  # root element aka the bucket
            try:
                self.get_bucket(bucket_name)
                return True
            except RuntimeError:
                return False

        return bool(self.get_bucket(bucket_name).get_blob(name))

    def delete(self, filename, bucket_name=None):
        """Deletes the filename. Filename is resolved with the
        absolute path based on base_path. If file does not exist,
        returns **False**, otherwise **True**

        :param filename: base name of file
        :param bucket_name: name of bucket, if not default
        """
        self.get_bucket(bucket_name).delete_blob(filename)

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
        :returns: modified filename
        """
        extensions = extensions or self.extensions

        if not self.filename_allowed(filename, extensions):
            raise FileNotAllowed()

        filename = utils.secure_filename(os.path.basename(filename))

        if randomize:
            filename = utils.random_filename(filename)

        if folder:
            filename = folder + "/" + filename

        content_type, _ = mimetypes.guess_type(filename)
        content_type = content_type or "application/octet-stream"

        blob = self.get_bucket(bucket_name).get_blob(filename)

        # If the file exist and we explicitely asked not to replace it: ignore it.
        if blob and not replace:
            return filename

        # If the file doesn't exist: create it.
        if not blob:
            blob = Blob(filename, self.get_bucket(bucket_name))

        blob.cache_control = self.cache_control
        file.seek(0)

        kwargs = {
            "rewind": True,
            "content_type": content_type or "application/octet-stream",
        }

        if not self.uniform_bucket_level_access:
            kwargs["predefined_acl"] = acl or self.acl

        blob.upload_from_file(file, **kwargs)

        return filename
