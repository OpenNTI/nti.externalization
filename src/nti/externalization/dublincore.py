#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Externalization support for things that implement the interfaces
of :mod:`zope.dublincore.interfaces`.

.. note::
   We are "namespacing" the dublincore properties, since they have
   defined meanings we don't control. We are currently doing this by simply prefixing
   them with 'DC' for ease of access in JavaScript.

These objects are typically used as decorators, registered
from ZCML.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope import component
from zope import interface
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.dublincore.interfaces import IDCExtended

from nti.externalization.interfaces import IExternalMappingDecorator
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.singleton import Singleton

__all__ = [
    'DCExtendedExternalMappingDecorator',
    'DCDescriptivePropertiesExternalMappingDecorator',
]

# Note that its fairly common for things to claim to implement these interfaces,
# but only provide a subset of the properties. (mostly due to programming errors).
# Hence the use of getattr below, to protect against this.
@component.adapter(IDCExtended)
@interface.implementer(IExternalMappingDecorator)
class DCExtendedExternalMappingDecorator(Singleton):
    """
    Adds the extended properties of dublincore to external objects as
    defined by :class:`zope.dublincore.interfaces.IDCExtended`.

    .. note::

        We are currently only mapping 'Creator' since that's the
        only field that ever gets populated.

    Implements
    `~nti.externalization.interfaces.IExternalMappingDecorator` for
    :class:`zope.dublincore.interfaces.IDCExtended` objects.
    """

    def decorateExternalMapping(self, original, external):
        creators = getattr(original, 'creators', None)
        if 'DCCreator' not in external:
            external['DCCreator'] = creators
        if StandardExternalFields.CREATOR not in external and creators:
            external[StandardExternalFields.CREATOR] = creators[0]


@component.adapter(IDCDescriptiveProperties)
@interface.implementer(IExternalMappingDecorator)
class DCDescriptivePropertiesExternalMappingDecorator(Singleton):
    """
    Supports the 'DCTitle' and 'DCDescription' fields, as defined in
    :class:`zope.dublincore.interfaces.IDCDescriptiveProperties`.

    Implements
    `~nti.externalization.interfaces.IExternalMappingDecorator`.
    """

    def decorateExternalMapping(self, original, external):
        if 'DCTitle' not in external:
            external['DCTitle'] = getattr(original, 'title', None)
        if 'DCDescription' not in external:
            external['DCDescription'] = getattr(original, 'description', None)
