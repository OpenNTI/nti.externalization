# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
# -*- coding: utf-8 -*-
"""
Functions for finding factory objects to create internal objects
given their external form. This is usually derived from mime type
and possibly class name values in the external form. Factories
are registered in the component manager.

"""

# There are a *lot* of fixme (XXX and the like) in this file.
# Turn those off in general so we can see through the noise.
# pylint:disable=fixme

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope import component
from zope import interface

from nti.externalization.interfaces import IClassObjectFactory
from nti.externalization.interfaces import IExternalizedObjectFactoryFinder
from nti.externalization.interfaces import IFactory
from nti.externalization.interfaces import IMimeObjectFactory

from .legacy_factories import search_for_external_factory

from .._base_interfaces import get_standard_external_fields


StandardExternalFields = get_standard_external_fields()
component_queryAdapter = component.queryAdapter
component_queryUtility = component.queryUtility

logger = __import__('logging').getLogger(__name__)

__all__ = [
    'default_externalized_object_factory_finder',
    'default_externalized_object_factory_finder_factory',
    'find_factory_for_class_name',
    'find_factory_for',
]

def _search_for_mime_factory(externalized_object, mime_type):
    if not mime_type:
        return None

    factory = component_queryAdapter(externalized_object,
                                     IMimeObjectFactory,
                                     mime_type)
    if factory is not None:
        return factory

    # What about a named utility?
    factory = component_queryUtility(IMimeObjectFactory,
                                     mime_type)

    if factory is not None:
        return factory

    # Is there a default?
    factory = component_queryAdapter(externalized_object,
                                     IMimeObjectFactory)

    return factory

def _search_for_class_factory(externalized_object, class_name):
    if not class_name:
        return None

    factory = component_queryAdapter(externalized_object,
                                     IClassObjectFactory,
                                     class_name)

    if factory is not None:
        return factory

    return find_factory_for_class_name(class_name)

def _find_factory_for_mime_or_class(externalized_object):
    # We use specialized interfaces instead of plain IFactory to make it clear
    # that these are being created from external data

    try:
        mime_type = externalized_object[StandardExternalFields.MIMETYPE]
    except TypeError:
        # Not subscriptable. We won't be able to work for
        # this object
        return None
    except KeyError:
        # sad trombone. Not present.
        pass
    else:
        factory = _search_for_mime_factory(externalized_object, mime_type)
        if factory is not None:
            return factory

    # Fallback to class
    try:
        class_name = externalized_object[StandardExternalFields.CLASS]
    except KeyError:
        # very sad trombone
        return None

    return _search_for_class_factory(externalized_object, class_name)


class _DefaultExternalizedObjectFactoryFinder(object):
    # This is an IFactory, declared below.
    # (Cython cdef classes cannot have decorators)
    __slots__ = ()

    def find_factory(self, externalized_object):
        return _find_factory_for_mime_or_class(externalized_object)

    # We are callable for BWC and because that's what an IFactory is
    def __call__(self, externalized_object):
        return self.find_factory(externalized_object)

interface.classImplements(_DefaultExternalizedObjectFactoryFinder,
                          IFactory)

default_externalized_object_factory_finder = _DefaultExternalizedObjectFactoryFinder()


@interface.implementer(IExternalizedObjectFactoryFinder)
def default_externalized_object_factory_finder_factory(unused_externalized_object):
    return default_externalized_object_factory_finder


def find_factory_for_class_name(class_name):
    factory = component_queryUtility(IClassObjectFactory, class_name)
    if factory is None:
        factory = search_for_external_factory(class_name)
    # Did we chop off an extra 's'?
    if factory is None and class_name and class_name.endswith('s'):
        factory = search_for_external_factory(class_name + 's')
    return factory


def find_factory_for(externalized_object, registry=component):
    """
    find_factory_for(externalized_object, registry=<zope.component>) -> factory

    Given a
    :class:`~nti.externalization.interfaces.IExternalizedObject`,
    locate and return a factory to produce a Python object to hold its
    contents.

    If there is a
    :class:`~nti.externalization.interfaces.IExternalizedObjectFactoryFinder`
    adapter registered for the externalized object, we return the
    results of its ``find_factory`` method. Note that since
    externalized objects are typically simple lists or dicts, such
    adapters have the capability to hijack all factory finding,
    probably unintentionally.

    Otherwise, we examine the contents of the object itself to find a
    registered factory based on MIME type (preferably) or class name.
    """
    factory_finder = registry.queryAdapter(
        externalized_object,
        IExternalizedObjectFactoryFinder)
    if factory_finder is not None:
        return factory_finder.find_factory(externalized_object)

    # We do it this way instead of using
    # ``default_externalized_object_factory_finder`` as the default in
    # queryAdapter so cython can optimize the call.
    return _find_factory_for_mime_or_class(externalized_object)


from nti.externalization._compat import import_c_accel # pylint:disable=wrong-import-position,wrong-import-order
import_c_accel(globals(), 'nti.externalization.internalization._factories')
