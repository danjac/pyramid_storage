# -*- coding: utf-8 -*-

from .storage import FileStorage
from .interfaces import IFileStorage


def get_file_storage(request):
    """
    Retrieves **FileStorage** instance from the registry.

    :param request: Pyramid Request instance
    """
    registry = getattr(request, 'registry', None)
    if registry is None:
        registry = request
    return registry.getUtility(IFileStorage)


def includeme(config):
    factory = FileStorage.from_settings(
        config.registry.settings, prefix='storage.'
    )
    config.registry.registerUtility(factory, IFileStorage)
    name = config.registry.settings.get('storage.name', 'storage')
    config.add_request_method(get_file_storage, name, True)
