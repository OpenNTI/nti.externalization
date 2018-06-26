# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
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

    The class is instantiated immediately at the point where it is
    defined by calling ``cls.__new__(cls)``. This instance is cached and
    ``cls.__new__`` is rebound to return it directly.

    The original constructor is also cached to allow subclasses to access it
    and have their own instance.
    """

    def __new__(mcs, name, bases, cls_dict):
        cls_dict['__slots__'] = ()  # no ivars
        cls_dict['__init__'] = lambda *args: None

        cls = type.__new__(mcs, name, bases, cls_dict)

        ancestor = object
        for ancestor in cls.mro():
            if '__new__' in ancestor.__dict__:
                break
        if isinstance(ancestor, SingletonMetaclass) and ancestor is not cls:
            ctor = ancestor._new_instance
        else:
            ctor = cls.__new__
        cls._new_instance = staticmethod(ctor)

        the_instance = ctor(cls)

        cls.__new__ = staticmethod(lambda *args: the_instance)

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


from nti.externalization._compat import import_c_accel
import_c_accel(globals(), 'nti.externalization._singleton')
