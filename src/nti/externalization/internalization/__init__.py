# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
# -*- coding: utf-8 -*-
"""
Functions for taking externalized objects and creating application
model objects.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope.interface.interfaces import ComponentLookupError

__all__ = [
    'update_from_external_object',
    'new_from_external_object',
    'LEGACY_FACTORY_SEARCH_MODULES',
    'register_legacy_search_module',
    'default_externalized_object_factory_finder',
    'default_externalized_object_factory_finder_factory',
    'find_factory_for_class_name',
    'find_factory_for',
    'notifyModified',
    'validate_field_value',
    'validate_named_field_value',
]

#: .. deprecated:: 1.0
#: This is legacy functionality, please do not access directly.
#: The public interface is through :func:`register_legacy_search_module`
from .legacy_factories import LEGACY_FACTORY_SEARCH_MODULES
from .legacy_factories import register_legacy_search_module


from .factories import default_externalized_object_factory_finder
from .factories import default_externalized_object_factory_finder_factory
from .factories import find_factory_for_class_name
from .factories import find_factory_for

from .events import notifyModified

from .updater import update_from_external_object

from .fields import validate_field_value
from .fields import validate_named_field_value

def new_from_external_object(external_object, *args, **kwargs):
    """
    Like `update_from_external_object`, but creates a new object to
    update using `find_factory_for`.

    All remaining arguments are passed to
    `update_from_external_object`.

    If no factory can be found, raises a
    :exc:`zope.interface.interfaces.ComponentLookupError`.

    Returns the new object.

    .. versionadded:: 1.0a3
    """

    factory = find_factory_for(external_object)
    if factory is None:
        raise ComponentLookupError("No factory for object", external_object)
    return update_from_external_object(factory(), external_object, *args, **kwargs)
