# -*- coding: utf-8 -*-

from . import local


def includeme(config):
    """Use local file storage by default"""
    local.includeme(config)
