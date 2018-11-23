# -*- coding: utf-8 -*-

import mock
import pytest

from pyramid import compat
from pyramid import exceptions as pyramid_exceptions


class MockGCloudConnection(object):

    def get_bucket(self, bucket_name):
        return mock.Mock()


def _get_mock_gcloud_connection(self):
    return MockGCloudConnection()


def _mock_open_name():

    if compat.PY3:
        return 'builtins.open'
    else:
        return '__builtin__.open'


def _mock_open(name='test', mode='wb', encoding="utf-8"):

    obj = mock.Mock()
    obj.__enter__ = mock.Mock()
    obj.__enter__.return_value = mock.Mock()
    obj.__exit__ = mock.Mock()
    return obj


def test_extension_allowed_if_any():
    from pyramid_storage import gcloud
    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json",
        bucket_name="my_bucket",
        extensions="any"
    )
    assert g.extension_allowed(".jpg")


def test_extension_allowed_if_allowed_if_dotted():
    from pyramid_storage import gcloud
    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json",
        bucket_name="my_bucket",
        extensions="images"
    )
    assert g.extension_allowed(".jpg", ("jpg",))


def test_extension_not_allowed_if_allowed_if_dotted():
    from pyramid_storage import gcloud
    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json",
        bucket_name="my_bucket",
        extensions="images"
    )
    assert not g.extension_allowed("jpg", ("gif",))


def test_extension_not_allowed_if_allowed_if_not_dotted():
    from pyramid_storage import gcloud
    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json",
        bucket_name="my_bucket",
        extensions="images"
    )
    assert not g.extension_allowed("jpg", ("gif",))


def test_file_allowed():
    from pyramid_storage import gcloud

    fs = mock.Mock()
    fs.filename = "test.jpg"
    s = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json",
        bucket_name="my_bucket",
        extensions="images"
    )

    assert s.file_allowed(fs)


def test_file_not_allowed():
    from pyramid_storage import gcloud

    fs = mock.Mock()
    fs.filename = "test.jpg"
    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json",
        bucket_name="my_bucket",
        extensions="documents"
    )

    assert not g.file_allowed(fs)


def test_save_if_file_not_allowed():
    from pyramid_storage import gcloud
    from pyramid_storage.exceptions import FileNotAllowed

    fs = mock.Mock()
    fs.filename = "test.jpg"
    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json",
        bucket_name="my_bucket",
        extensions="documents"
    )

    with pytest.raises(FileNotAllowed):
        g.save(fs)


def test_save_if_file_allowed():
    from pyramid_storage import gcloud

    fs = mock.Mock()
    fs.filename = "test.jpg"

    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json",
        bucket_name="my_bucket",
        extensions="images")

    with mock.patch(
            'pyramid_storage.gcloud.GoogleCloudStorage.get_connection',
            _get_mock_gcloud_connection):
        name = g.save(fs)
    assert name == "test.jpg"


def test_save_file():
    from pyramid_storage import gcloud

    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json",
        bucket_name="my_bucket",
        extensions="images"
    )

    with mock.patch(
            'pyramid_storage.gcloud.GoogleCloudStorage.get_connection',
            _get_mock_gcloud_connection):
        name = g.save_file(mock.Mock(), "test.jpg")
    assert name == "test.jpg"


def test_save_filename():
    from pyramid_storage import gcloud

    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json",
        bucket_name="my_bucket",
        extensions="images"
    )

    patches = (
        mock.patch(_mock_open_name(), _mock_open),
        mock.patch(
            'pyramid_storage.gcloud.GoogleCloudStorage.get_connection',
            _get_mock_gcloud_connection
        )
    )

    for patch in patches:
        patch.start()

    name = g.save_filename("test.jpg")
    assert name == "test.jpg"

    for patch in patches:
        patch.stop()


def test_save_if_randomize():
    from pyramid_storage import gcloud

    fs = mock.Mock()
    fs.filename = "test.jpg"

    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json",
        bucket_name="my_bucket",
        extensions="images")

    with mock.patch(
            'pyramid_storage.gcloud.GoogleCloudStorage.get_connection',
            _get_mock_gcloud_connection):
        name = g.save(fs, randomize=True)
    assert name != "test.jpg"


def test_save_in_folder():

    from pyramid_storage import gcloud

    fs = mock.Mock()
    fs.filename = "test.jpg"

    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json",
        bucket_name="my_bucket",
        extensions="images")

    with mock.patch(
            'pyramid_storage.gcloud.GoogleCloudStorage.get_connection',
            _get_mock_gcloud_connection):
        name = g.save(fs, folder="my_folder")
    assert name == "my_folder/test.jpg"


def test_delete():

    from pyramid_storage import gcloud

    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json",
        bucket_name="my_bucket",
        extensions="images"
    )

    with mock.patch(
            'pyramid_storage.gcloud.GoogleCloudStorage.get_connection',
            _get_mock_gcloud_connection):

        g.delete("test.jpg")


def test_from_settings_with_defaults():
    from pyramid_storage import gcloud

    settings = {
        'storage.gcloud.credentials': '/secure/credentials.json',
        'storage.gcloud.bucket_name': 'Attachments',
    }
    inst = gcloud.GoogleCloudStorage.from_settings(settings, 'storage.')
    assert inst.base_url == ''
    assert inst.bucket_name == 'Attachments'
    assert inst.acl == 'publicRead'
    assert set(('jpg', 'txt', 'doc')).intersection(inst.extensions)

    with mock.patch.object(gcloud, "Client") as gcloud_mocked:
        inst.get_connection()
        _, gcloud_options = gcloud_mocked.from_service_account_json.call_args_list[0]
        assert 'json_credentials_path' in gcloud_options
        assert gcloud_options["json_credentials_path"] == '/secure/credentials.json'

        inst.get_bucket()
        bucket_options, _ = gcloud_mocked.from_service_account_json \
            .return_value.get_bucket.call_args_list[0]
        assert "Attachments" in bucket_options


def test_from_settings_if_base_path_missing():
    from pyramid_storage import gcloud
    with pytest.raises(pyramid_exceptions.ConfigurationError):
        gcloud.GoogleCloudStorage.from_settings({}, 'storage.')
