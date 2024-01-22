# -*- coding: utf-8 -*-

from pyramid.testing import DummyRequest, testConfig
from zope.interface import implementer


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
    from pyramid_storage import registry
    from pyramid_storage.interfaces import IFileStorage

    @implementer(IFileStorage)
    class DummyFileStorage(object):
        pass

    settings = {
        "storage.base_path": "uploads",
    }

    with testConfig(settings=settings) as config:
        fs = DummyFileStorage()
        req = DummyRequest()
        req.registry = config.registry

        registry.register_file_storage_impl(config, fs)
        impl = registry.get_file_storage_impl(req)
        assert impl == fs
