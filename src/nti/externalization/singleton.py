#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for singleton objects that are used as external object decorators.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# This was originally based on code from sympy.core.singleton


class SingletonMetaclass(type):
    """
    Metaclass for singleton classes most commonly used as external object
    decorators (adapters). These objects accept one or two context arguments to
    their ``__init__`` function, but they do not actually use them (because the same
    object is passed to their decoration method). Thus they can usefully
    be constructed just once and shared. This metaclass ensures the singleton
    property, ensures that the ``__init__`` method is a no-op, and ensures
    that the instance has no dictionary or instance variable.

    A singleton class has only one instance which is returned every time the
    class is instantiated.

    .. caution::
       We cannot be used with :func:`six.with_metaclass` because it introduces
       temporary classes. You'll need to use the metaclass constructor directly::

            AClass = SingletonMetaclass('AClass', (object,), {})

       Alternatively, you can inherit from :class:`Singleton`.

    **Implementation Notes**

    Performance tests show that the approach used to create singletons
    (constructing an instance when the class was created and rebinding ``__new__`` to
    return it) is actually slower than letting the interpreter do its thing. Since
    these are small objects that are typically short lived, allowing them to be allocated
    on demand may reduce cache pressure as well. So this class no longer actually guarantees
    the true singleton property.

    .. versionchanged:: 1.0a2
       No longer actually enforce the singleton property.
    .. versionchanged:: 1.0a2
       This metaclass always provides definitions for ``__eq__`` and ``__ne__``
       and ``__hash__``.
    """

    def __new__(mcs, name, bases, cls_dict):
        cls_dict['__slots__'] = ()  # no ivars
        cls_dict['__init__'] = lambda self, context=None, request=None: None
        cls_dict['__eq__'] = lambda self, other: type(self) is type(other)
        cls_dict['__hash__'] = lambda self: hash(type(self))
        cls_dict['__ne__'] = lambda self, other: type(self) is not type(other)

        cls = type.__new__(mcs, name, bases, cls_dict)

        return cls

SingletonDecorator = SingletonMetaclass # BWC

Singleton = SingletonMetaclass(
    'Singleton', (object,),
    {
        '__doc__':
        "A base class for singletons. "
        "Can be more convenient than a metaclass for Python2/Python3 compatibility."
    }
)
