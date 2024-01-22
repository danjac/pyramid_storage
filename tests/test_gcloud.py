# -*- coding: utf-8 -*-
from io import BytesIO
from unittest import mock

import pytest
from pyramid import exceptions as pyramid_exceptions


class MockGCloudConnection(object):
    def get_bucket(self, bucket_name):
        bucket = mock.MagicMock()
        bucket.get_blob.return_value = None
        return bucket


def _get_mock_gcloud_connection(self):
    return MockGCloudConnection()


def _mock_open(name="test", mode="wb", encoding="utf-8"):
    obj = mock.Mock()
    obj.__enter__ = mock.Mock()
    obj.__enter__.return_value = BytesIO()
    obj.__exit__ = mock.Mock()
    return obj


def test_extension_allowed_if_any():
    from pyramid_storage import gcloud

    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json", bucket_name="my_bucket", extensions="any"
    )
    assert g.extension_allowed(".jpg")


def test_extension_allowed_if_allowed_if_dotted():
    from pyramid_storage import gcloud

    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json", bucket_name="my_bucket", extensions="images"
    )
    assert g.extension_allowed(".jpg", ("jpg",))


def test_extension_not_allowed_if_allowed_if_dotted():
    from pyramid_storage import gcloud

    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json", bucket_name="my_bucket", extensions="images"
    )
    assert not g.extension_allowed("jpg", ("gif",))


def test_extension_not_allowed_if_allowed_if_not_dotted():
    from pyramid_storage import gcloud

    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json", bucket_name="my_bucket", extensions="images"
    )
    assert not g.extension_allowed("jpg", ("gif",))


def test_file_allowed():
    from pyramid_storage import gcloud

    fs = mock.Mock()
    fs.filename = "test.jpg"
    s = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json", bucket_name="my_bucket", extensions="images"
    )

    assert s.file_allowed(fs)


def test_file_not_allowed():
    from pyramid_storage import gcloud

    fs = mock.Mock()
    fs.filename = "test.jpg"
    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json", bucket_name="my_bucket", extensions="documents"
    )

    assert not g.file_allowed(fs)


def test_save_if_file_not_allowed():
    from pyramid_storage import gcloud
    from pyramid_storage.exceptions import FileNotAllowed

    fs = mock.Mock()
    fs.filename = "test.jpg"
    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json", bucket_name="my_bucket", extensions="documents"
    )

    with pytest.raises(FileNotAllowed):
        g.save(fs)


def test_save_if_file_allowed():
    from pyramid_storage import gcloud

    fs = mock.Mock()
    fs.filename = "test.jpg"

    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json", bucket_name="my_bucket", extensions="images"
    )

    with mock.patch(
        "pyramid_storage.gcloud.GoogleCloudStorage.get_connection", _get_mock_gcloud_connection
    ):
        with mock.patch("pyramid_storage.gcloud.Blob") as mocked_new_blob:
            name = g.save(fs)
            assert mocked_new_blob.return_value.upload_from_file.called
    assert name == "test.jpg"


def test_save_file():
    from pyramid_storage import gcloud

    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json", bucket_name="my_bucket", extensions="images"
    )

    with mock.patch(
        "pyramid_storage.gcloud.GoogleCloudStorage.get_connection", _get_mock_gcloud_connection
    ):
        with mock.patch("pyramid_storage.gcloud.Blob") as mocked_new_blob:
            name = g.save_file(BytesIO(), "test.jpg")
            assert mocked_new_blob.return_value.upload_from_file.called

    assert name == "test.jpg"


def test_save_file_with_uniform_bucket_level_access_disabled():
    from pyramid_storage import gcloud

    g = gcloud.GoogleCloudStorage(None, "Attachments")

    with mock.patch(
        "pyramid_storage.gcloud.GoogleCloudStorage.get_connection", _get_mock_gcloud_connection
    ):
        with mock.patch("pyramid_storage.gcloud.Blob") as mocked_blob:
            g.save_file(mock.Mock(), "acme.txt")

            assert mocked_blob.return_value.upload_from_file.called
            assert (
                "predefined_acl"
                in mocked_blob.return_value.upload_from_file.call_args_list[0].kwargs
            )


def test_save_file_with_uniform_bucket_level_access_enabled():
    from pyramid_storage import gcloud

    g = gcloud.GoogleCloudStorage(None, "Attachments", uniform_bucket_level_access=True)

    with mock.patch(
        "pyramid_storage.gcloud.GoogleCloudStorage.get_connection", _get_mock_gcloud_connection
    ):
        with mock.patch("pyramid_storage.gcloud.Blob") as mocked_blob:
            g.save_file(mock.Mock(), "acme.txt")

            assert mocked_blob.return_value.upload_from_file.called
            assert (
                "predefined_acl"
                not in mocked_blob.return_value.upload_from_file.call_args_list[0].kwargs
            )


def test_save_filename():
    from pyramid_storage import gcloud

    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json", bucket_name="my_bucket", extensions="images"
    )

    patches = (
        mock.patch("builtins.open", _mock_open),
        mock.patch(
            "pyramid_storage.gcloud.GoogleCloudStorage.get_connection", _get_mock_gcloud_connection
        ),
    )

    for patch in patches:
        patch.start()

    with mock.patch("pyramid_storage.gcloud.Blob") as mocked_new_blob:
        name = g.save_filename("test.jpg", replace=True)
        assert name == "test.jpg"
        assert mocked_new_blob.return_value.upload_from_file.called

    for patch in patches:
        patch.stop()


def test_save_if_randomize():
    from pyramid_storage import gcloud

    fs = mock.Mock()
    fs.filename = "test.jpg"

    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json", bucket_name="my_bucket", extensions="images"
    )

    with mock.patch(
        "pyramid_storage.gcloud.GoogleCloudStorage.get_connection", _get_mock_gcloud_connection
    ):
        with mock.patch("pyramid_storage.gcloud.Blob") as mocked_new_blob:
            name = g.save(fs, randomize=True)
            assert mocked_new_blob.return_value.upload_from_file.called
    assert name != "test.jpg"


def test_save_in_folder():
    from pyramid_storage import gcloud

    fs = mock.MagicMock()
    fs.filename = "test.jpg"
    fs.file = BytesIO()

    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json", bucket_name="my_bucket", extensions="images"
    )

    with mock.patch(
        "pyramid_storage.gcloud.GoogleCloudStorage.get_connection", _get_mock_gcloud_connection
    ):
        with mock.patch("pyramid_storage.gcloud.Blob") as mocked_new_blob:
            name = g.save(fs, folder="my_folder")
            assert mocked_new_blob.return_value.upload_from_file.called
    assert name == "my_folder/test.jpg"


def test_delete():
    from pyramid_storage import gcloud

    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json", bucket_name="my_bucket", extensions="images"
    )

    with mock.patch(
        "pyramid_storage.gcloud.GoogleCloudStorage.get_connection", _get_mock_gcloud_connection
    ):
        g.delete("test.jpg")


def test_from_settings_with_defaults():
    from pyramid_storage import gcloud

    settings = {
        "storage.gcloud.bucket_name": "Attachments",
    }

    inst = gcloud.GoogleCloudStorage.from_settings(settings, "storage.")

    assert inst.base_url == ""
    assert inst.bucket_name == settings["storage.gcloud.bucket_name"]
    assert inst.acl == "publicRead"
    assert set(("jpg", "txt", "doc")).intersection(inst.extensions)

    with mock.patch.object(gcloud, "Client") as gcloud_mocked:
        inst.get_connection()

        assert gcloud_mocked.call_count == 1

        inst.get_bucket()

        bucket_options, _ = gcloud_mocked.return_value.get_bucket.call_args_list[0]

        assert settings["storage.gcloud.bucket_name"] in bucket_options


def test_from_settings_with_defaults_and_uniform_bucket_level_access_enabled():
    from pyramid_storage import gcloud

    settings = {
        "storage.gcloud.bucket_name": "Attachments",
        "storage.gcloud.uniform_bucket_level_access": True,
    }

    inst = gcloud.GoogleCloudStorage.from_settings(settings, "storage.")

    assert inst.bucket_name == settings["storage.gcloud.bucket_name"]
    assert (
        inst.uniform_bucket_level_access == settings["storage.gcloud.uniform_bucket_level_access"]
    )
    assert inst.acl is None
    assert inst.auto_create_acl is None


def test_from_settings_with_defaults_and_uniform_bucket_level_access_enabled_as_string():
    from pyramid_storage import gcloud

    settings = {
        "storage.gcloud.bucket_name": "Attachments",
        "storage.gcloud.uniform_bucket_level_access": "true",
    }

    inst = gcloud.GoogleCloudStorage.from_settings(settings, "storage.")

    assert inst.bucket_name == settings["storage.gcloud.bucket_name"]
    assert inst.uniform_bucket_level_access
    assert inst.acl is None
    assert inst.auto_create_acl is None


def test_from_settings_with_defaults_and_uniform_bucket_level_access_enabled_and_acl_set():
    from pyramid_storage import gcloud

    settings = {
        "storage.gcloud.bucket_name": "Attachments",
        "storage.gcloud.uniform_bucket_level_access": True,
        "storage.gcloud.acl": "publicRead",
    }

    with pytest.raises(pyramid_exceptions.ConfigurationError):
        gcloud.GoogleCloudStorage.from_settings(
            settings, "storage."
        ) == pyramid_exceptions.ConfigurationError


def test_from_settings_with_defaults_and_uniform_bucket_level_access_enabled_and_auto_create_acl_set():
    from pyramid_storage import gcloud

    settings = {
        "storage.gcloud.bucket_name": "Attachments",
        "storage.gcloud.uniform_bucket_level_access": True,
        "storage.gcloud.auto_create_acl": "projectPrivate",
    }

    with pytest.raises(pyramid_exceptions.ConfigurationError):
        gcloud.GoogleCloudStorage.from_settings(
            settings, "storage."
        ) == pyramid_exceptions.ConfigurationError


def test_from_settings_with_credentials():
    from pyramid_storage import gcloud

    settings = {
        "storage.gcloud.credentials": "credentials.json",
        "storage.gcloud.bucket_name": "Attachments",
    }

    inst = gcloud.GoogleCloudStorage.from_settings(settings, "storage.")

    assert inst.base_url == ""
    assert inst.bucket_name == settings["storage.gcloud.bucket_name"]
    assert inst.acl == "publicRead"
    assert set(("jpg", "txt", "doc")).intersection(inst.extensions)

    with mock.patch.object(gcloud, "Client") as gcloud_mocked:
        inst.get_connection()

        _, gcloud_options = gcloud_mocked.from_service_account_json.call_args_list[0]

        assert "json_credentials_path" in gcloud_options
        assert gcloud_options["json_credentials_path"] == settings["storage.gcloud.credentials"]

        inst.get_bucket()

        (
            bucket_options,
            _,
        ) = gcloud_mocked.from_service_account_json.return_value.get_bucket.call_args_list[0]

        assert "Attachments" in bucket_options


def test_from_settings_if_base_path_missing():
    from pyramid_storage import gcloud

    with pytest.raises(pyramid_exceptions.ConfigurationError):
        gcloud.GoogleCloudStorage.from_settings({}, "storage.")


def test_get_bucket():
    from pyramid_storage import gcloud

    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json", bucket_name="my_bucket", extensions="images"
    )

    with mock.patch("pyramid_storage.gcloud.GoogleCloudStorage.get_connection") as mocked:
        _my_bucket = g.get_bucket()
        _other_bucket = g.get_bucket("other_bucket")
    assert mocked.return_value.get_bucket.call_args_list[0][0][0] == "my_bucket"
    assert mocked.return_value.get_bucket.call_args_list[1][0][0] == "other_bucket"


def test_save_file_to_bucket():
    from pyramid_storage import gcloud

    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json", bucket_name="my_bucket", extensions="images"
    )

    with mock.patch("pyramid_storage.gcloud.GoogleCloudStorage.get_connection") as mocked:
        g.save_file(mock.Mock(), "test.jpg")
        g.save_file(mock.Mock(), "test.jpg", bucket_name="other_bucket")
    assert mocked.return_value.get_bucket.call_args_list[0][0][0] == "my_bucket"
    assert mocked.return_value.get_bucket.call_args_list[1][0][0] == "other_bucket"
    # make sure saving to another bucket doesn't change the default
    assert g.bucket_name == "my_bucket"


def test_delete_from_bucket():
    from pyramid_storage import gcloud

    g = gcloud.GoogleCloudStorage(
        credentials="/secrets/credentials.json", bucket_name="my_bucket", extensions="images"
    )

    with mock.patch("pyramid_storage.gcloud.GoogleCloudStorage.get_connection") as mocked:
        g.delete("test.jpg")
        g.delete("test.jpg", bucket_name="other_bucket")
    assert mocked.return_value.get_bucket.call_args_list[0][0][0] == "my_bucket"
    assert mocked.return_value.get_bucket.call_args_list[1][0][0] == "other_bucket"
