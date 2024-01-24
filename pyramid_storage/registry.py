from .interfaces import IFileStorage


def register_file_storage_impl(config, impl):
    config.registry.registerUtility(impl, IFileStorage)
    name = config.registry.settings.get("storage.name", "storage")
    config.add_request_method(get_file_storage_impl, name, True)


def get_file_storage_impl(request):
    """
    Retrieves correct **IFileStorage** instance from the registry.

    :param request: Pyramid Request instance
    """
    registry = getattr(request, "registry", None)
    if registry is None:
        registry = request
    return registry.getUtility(IFileStorage)
