# -*- coding: utf-8 -*-
"""
Implementations of object factories.

.. versionadded:: 1.0

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope import interface
from zope.component.factory import Factory

from nti.externalization.interfaces import IClassObjectFactory
from nti.externalization.interfaces import IMimeObjectFactory
from nti.externalization.interfaces import IAnonymousObjectFactory

_builtin_callable = callable

# pylint: disable=redefined-builtin, protected-access

__all__ = [
    'ObjectFactory',
    'MimeObjectFactory',
    'ClassObjectFactory',
    'AnonymousObjectFactory',
]

class ObjectFactory(Factory):
    """
    A convenient :class:`zope.component.interfaces.IFactory` meant to be
    registered as a named utility.

    The callable object SHOULD be a type/class object, because that's
    the only thing we base equality off of (class identity).

    This class can be subclassed and trivially instantiated by setting
    class properties :attr:`default_factory` and (optionally)
    :attr:`default_title` and :attr:`default_description`. Constructor
    arguments will override these, but if not given, the class values
    will be used.

    For example::

     >>> class MyObjectFactory(ObjectFactory):
     ...    default_factory = object
     ...    default_title = 'A Title'
     ...    default_description = 'A Description'
     >>> factory = MyObjectFactory()
     >>> factory # doctest: +ELLIPSIS
     <MyObjectFactory for <... 'object'>>
     >>> print(factory.title)
     A Title
     >>> print(factory.description)
     A Description
    """

    __external_factory_wants_arg__ = False

    #: The default callable argument, if none is given to the
    #: constructor.
    default_factory = None
    #: The default title, if none is given to the constructor.
    default_title = u''
    #: The default description, if none is given to the constructor.
    default_description = u''

    def __init__(self, callable=None, title='', description='', interfaces=None):
        callable = callable if callable is not None else self.default_factory
        if callable is None or not _builtin_callable(callable):
            raise ValueError("Must provide callable object, not %r" % (callable,))
        Factory.__init__(self,
                         callable,
                         title or self.default_title,
                         description or self.default_description,
                         interfaces)

    def __eq__(self, other):
        # Implementing equality is needed to prevent multiple inclusions
        # of the same module from different places from conflicting.
        try:
            return self._callable is other._callable
        except AttributeError: # pragma: no cover
            return NotImplemented

    def __hash__(self):
        return hash(self._callable)


@interface.implementer(IMimeObjectFactory)
class MimeObjectFactory(ObjectFactory):
    """
    Default implementation of
    :class:`~nti.externalization.interfaces.IMimeObjectFactory`.
    """

@interface.implementer(IClassObjectFactory)
class ClassObjectFactory(ObjectFactory):
    """
    Default implementation of
    :class:`~nti.externalization.interfaces.IClassObjectFactory`.
    """


@interface.implementer(IAnonymousObjectFactory)
class AnonymousObjectFactory(ObjectFactory):
    """
    Default implementation of
    :class:`~nti.externalization.interfaces.IAnonymousObjectFactory`.

    .. versionadded:: 1.0a3
    """
