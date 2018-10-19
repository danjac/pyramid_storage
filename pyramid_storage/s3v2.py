# -*- coding: utf-8 -*-

import os
import mimetypes
import tempfile
import uuid

from zope.interface import implementer

from . import utils
from .exceptions import FileNotAllowed
from .extensions import resolve_extensions
from .interfaces import IFileStorage
from .registry import register_file_storage_impl

from pyramid_storage.s3 import S3FileStorage


def includeme(config):

    impl = S3V2FileStorage.from_settings(
        config.registry.settings, prefix='storage.'
    )

    register_file_storage_impl(config, impl)


@implementer(IFileStorage)
class S3V2FileStorage(S3FileStorage):

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
            ('aws.signature_version', False, None),
        )
        kwargs = utils.read_settings(settings, options, prefix)
        kwargs = dict([(k.replace('aws.', ''), v) for k, v in kwargs.items()])
        kwargs['aws_access_key_id'] = kwargs.pop('access_key')
        kwargs['aws_secret_access_key'] = kwargs.pop('secret_key')
        return cls(**kwargs)

    # def __init__(self, bucket_name, acl=None, base_url='',
    #              extensions='default', **conn_options):
    #     self.bucket_name = bucket_name
    #     self.acl = acl
    #     self.base_url = base_url
    #     self.extensions = resolve_extensions(extensions)
    #     self.conn_options = conn_options

    def get_connection(self):
        raise NotImplementedError()

    def get_resource(self):

        try:
            import boto3
        except ImportError:
            raise RuntimeError("You must have boto3 installed to use s3v2")
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
        return self.get_resource().Bucket(self.bucket_name)

    def open(self, filename, *args):
        """Return filelike object stored
        """

        bucket = self.get_bucket()
        stream = bucket.Object(filename).get()['Body']

        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(stream.read())
        f.close()

        return open(f.name, *args)

    def exists(self, filename):
        """
        Test if a file exists
        :param filename:
        :return:
        """
        file_object = self.get_bucket().Object(filename)
        try :
            file_object.get()
            return True
        except file_object.meta.client.exceptions.NoSuchKey:
            return False

    def delete(self, filename):
        """Deletes the filename. Filename is resolved with the
        absolute path based on base_path. If file does not exist,
        returns **False**, otherwise **True**

        :param filename: base name of file
        """
        file_object = self.get_bucket().Object(filename)
        file_object.delete()

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

        file_object = bucket.Object(filename)

        if acl:
            file_object.upload_fileobj(file,  ExtraArgs={'ACL': acl})
        else:
            file_object.upload_fileobj(file)

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
        Get a list of files from a given folder
        :param folder:
        :return:
        """
        bucket = self.get_bucket()
        files_list = [file.key for file in bucket.objects.all() if folder in file.key]

        return files_list

    def copy_file(self, src, dst):
        """
        Copy a file to a new location in the same bucket
        :param src: key for source file
        :param dst: key for destination file
        :return:
        """

        bucket = self.get_bucket()
        src_copy = {
            'Bucket': bucket.name,
            'Key': src
        }
        bucket.copy(src_copy, dst)

    def move_file(self, src, dst):
        """
        Move a file from a location to another (A copy followed by a delete of the source file
        :param src: key for source file
        :param dst: key for destination file
        :return:
        """
        self.copy_file(src, dst)
        self.delete(src)

