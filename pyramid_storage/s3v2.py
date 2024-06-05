# -*- coding: utf-8 -*-

import os
import mimetypes
import tempfile
import uuid

from zope.interface import implementer

from .. import utils
from .exceptions import FileNotAllowed
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

def get_connection(self):
        raise NotImplementedError()

    def get_resource(self):

        try:
            import boto3
        except ImportError:
            raise RuntimeError("You must have boto3 installed to use s3v2")
        from botocore.client import Config
