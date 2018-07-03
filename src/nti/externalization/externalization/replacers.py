# -*- coding: utf-8 -*-
# NOT cython compiled. Not speed critical.
"""
Object replacers.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope import interface

from nti.externalization.interfaces import INonExternalizableReplacement
from nti.externalization.interfaces import INonExternalizableReplacementFactory

logger = __import__('logging').getLogger(__name__)

@interface.implementer(INonExternalizableReplacement)
class _NonExternalizableObject(dict):
    pass


def DefaultNonExternalizableReplacer(obj):
    logger.debug("Asked to externalize non-externalizable object %s, %s",
                 type(obj), obj)
    result = _NonExternalizableObject(Class='NonExternalizableObject',
                                      InternalType=str(type(obj)))
    return result


class NonExternalizableObjectError(TypeError):
    pass


@interface.implementer(INonExternalizableReplacementFactory)
class DevmodeNonExternalizableObjectReplacementFactory(object):
    """
    When devmode is active, non-externalizable objects raise an exception.
    """

    def __init__(self, obj):
        pass

    def __call__(self, obj):
        raise NonExternalizableObjectError(
            "Asked to externalize non-externalizable object %s, %s" %
            (type(obj), obj))
