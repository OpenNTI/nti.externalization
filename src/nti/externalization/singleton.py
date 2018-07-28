# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
# -*- coding: utf-8 -*-
"""
Support for fast, memory efficient singleton objects.

Why is this here? The externalization system can use lots of objects
as it goes through its process. Many of those objects are adapters
(for example, the decorator objectes), meaning a factory callable is
called to (create and) return an object (given a particular context,
and possibly request).

But the API of many adapter objects accept all the information they
need to have in the functions defined in the interface. That is, the
constructor does nothing useful with the context (and request). The
objects are stateless, and so constructing a new one for each adapter
invocation can be a waste of time and memory.

By either using the `SingletonMetaclass` as your metaclass, or
subclassing `Singleton`, that cost is paid only once, replacing a call
to a constructor and an object allocation with a faster call to return
a constant object.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# This was originally based on code from sympy.core.singleton

__all__ = [
    'SingletonMetaclass',
    'Singleton',
]

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

    >>> class TopSingleton(Singleton):
    ...    def __init__(self):
    ...        print("I am never called")
    >>> inst = TopSingleton()
    >>> isinstance(inst, TopSingleton)
    True
    >>> TopSingleton() is inst
    True
    >>> class DerivedSingelton(TopSingleton):
    ...     pass
    >>> derived = DerivedSingelton()
    >>> isinstance(derived, DerivedSingelton)
    True
    >>> DerivedSingelton() is derived
    True
    >>> derived is inst
    False
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
