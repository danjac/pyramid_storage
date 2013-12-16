# -*- coding: utf-8 -*-

from pyramid.testing import testConfig, DummyRequest


class DummyRegistry(object):
    def __init__(self, result=None):
        self.result = result
        self.registered = {}

    def getUtility(self, iface):
        return self.result

    def queryUtility(self, iface):
        return self.getUtility(iface)

    def registerUtility(self, impl, interface):
        self.registered[interface] = impl


def test_get_file_storage():
    from pyramid_storage import includeme, get_file_storage
    from pyramid_storage.storage import FileStorage

    settings = {
        'storage.base_path': 'uploads',
    }

    with testConfig(settings=settings) as config:
        fs = FileStorage('')
        config.registry.settings = settings
        includeme(config)
        req = DummyRequest()
        req.registry = config.registry
        storage = get_file_storage(req)
        assert isinstance(storage, FileStorage)
