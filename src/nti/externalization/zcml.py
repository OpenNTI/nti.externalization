#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Directives to be used in ZCML.


These directives are all in the ``http://nextthought.com/ntp/ext`` namespace,
and are loaded using the ``meta.zcml`` file.

Example (non-sensical) of all the directives:

.. code-block:: xml

    <configure xmlns:ext="http://nextthought.com/ntp/ext">
        <include package="nti.externalization" file="meta.zcml" />

        <ext:registerMimeFactories module="the.module" />

        <ext:registerAutoPackageIO
            root_interfaces="other_module.interfaces.IExtRoot"
            modules="other_module.factories"
            iobase="other_module.externalization.IOBase"
            register_legacy_search_module="yes" />

        <ext:classObjectFactory
            factory="third_module.Factory"
            name="AName" />

        <ext:anonymousObjectFactory
            factory="module3.Factory"
            for="interfaces.ISchema"
            field="field" />
        <ext:anonymousObjectFactoryInPlace
            for="interfaces.ISchema"
            field="field2" />
    </configure>

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from ZODB import loglevels
from zope import interface
from zope.component import zcml as component_zcml
from zope.configuration.fields import Bool
from zope.configuration.fields import GlobalInterface
from zope.configuration.fields import GlobalObject
from zope.configuration.fields import Tokens
from zope.configuration.fields import MessageID
from zope.configuration.fields import PythonIdentifier

from .interfaces import _ILegacySearchModuleFactory
from .autopackage import AutoPackageSearchingScopedInterfaceObjectIO
from .factory import MimeObjectFactory
from .factory import ClassObjectFactory
from .factory import AnonymousObjectFactory
from .interfaces import IMimeObjectFactory
from .interfaces import IClassObjectFactory
from .interfaces import IAnonymousObjectFactory
from .internalization.legacy_factories import find_factories_in_module

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# pylint: disable=protected-access,inherit-non-class

__all__ = [
    'IRegisterInternalizationMimeFactoriesDirective',
    'IAutoPackageExternalizationDirective',
    'IClassObjectFactoryDirective',
    'IBaseAnonymousObjectFactoryDirective',
    'IAnonymousObjectFactoryDirective',
    'IAnonymousObjectFactoryInPlaceDirective',
]


class IRegisterInternalizationMimeFactoriesDirective(interface.Interface):
    """
    Defines the ``ext:registerMimeFactories`` directive.

    Poke through the classes defined in *module*. If a class
    defines the ``mimeType`` attribute and can be created externally,
    (because it defines ``__external_can_create__`` to be true), registers
    a factory utility under the ``mimeType`` name. (For backwards compatibility,
    ``mime_type`` is accepted if there is no ``mimeType``.)

    Factories are discovered using `.find_factories_in_module`.

    See :func:`nti.externalization.internalization.find_factory_for`
    for how factories are used.

    """

    module = GlobalObject(
        title=u"Module to scan for Mime factories to add",
        required=True,
    )


def registerMimeFactories(_context, module):
    for object_name, value in find_factories_in_module(module, case_sensitive=True):
        __traceback_info__ = object_name, value

        try:
            mime_type = value.mimeType
        except AttributeError:
            try:
                mime_type = value.mime_type
            except AttributeError:
                continue

        if mime_type:
            logger.log(loglevels.TRACE,
                       "Registered mime factory utility %s = %s (%s)",
                       object_name, value, mime_type)
            factory = MimeObjectFactory(value,
                                        title=object_name,
                                        interfaces=list(interface.implementedBy(value)))
            component_zcml.utility(_context,
                                   provides=IMimeObjectFactory,
                                   component=factory,
                                   name=mime_type)


class IAutoPackageExternalizationDirective(interface.Interface):
    """
    Defines the ``ext:registerAutoPackageIO`` directive.

    This directive combines the effects of
    `IRegisterInternalizationMimeFactoriesDirective` with that
    of :mod:`.autopackage`, removing all need to repeat root
    interfaces and module names.

    After this directive is complete, a new class that descends from
    :class:`~.AutoPackageSearchingScopedInterfaceObjectIO` will be
    registered as the :class:`~nti.externalization.interfaces.IInternalObjectIO` adapter for all of
    the *root_interface* objects, and the *modules* (or
    *factory_modules*) will be searched for object factories via
    `IRegisterInternalizationMimeFactoriesDirective`.

    .. versionchanged:: 1.0
       Add the *register_legacy_search_module* keyword argument, defaulting to
       False. Previously legacy search modules would always be registered, but
       now you must explicitly ask for it.
    """

    root_interfaces = Tokens(
        title=u"The root interfaces defined by the package.",
        value_type=GlobalInterface(),
        required=True)

    modules = Tokens(
        title=u"Module names that contain the implementations of the root_interfaces.",
        value_type=GlobalObject(),
        required=True)

    factory_modules = Tokens(
        title=u"If given, module names that should be searched for internalization factories.",
        description=(u"If not given, all *modules* will be examined. If given, "
                     u"**only** these modules will be searched."),
        value_type=GlobalObject(),
        required=False)

    iobase = GlobalObject(
        title=(u"If given, a base class that will be used. "
               u"You can customize aspects of externalization that way."),
        description=(u"This class should descend from `object`, and it should implement "
                     u"the extension methods documented to customize "
                     u"`.AutoPackageSearchingScopedInterfaceObjectIO`."),
        required=False)

    register_legacy_search_module = Bool(
        title=(u"Register found factories by their class name."),
        description=(u"If true (*not* the default), then, in addition to registering "
                     u"factories by their mime type, also register them all by their class name. "
                     u"This is not recommended; currently no conflicts are caught and the order "
                     u"is ill-defined. "
                     u"See https://github.com/NextThought/nti.externalization/issues/33"),
        default=False,
        required=False,
    )


def autoPackageExternalization(_context, root_interfaces, modules,
                               factory_modules=None, iobase=None,
                               register_legacy_search_module=False):
    ext_module_name = root_interfaces[0].__module__
    package_name = ext_module_name.rsplit('.', 1)[0]

    root_interfaces = frozenset(root_interfaces)
    @classmethod
    def _ap_enumerate_externalizable_root_interfaces(cls, unused_ifaces):
        return root_interfaces

    module_names = frozenset([m.__name__.split('.')[-1] for m in modules])
    @classmethod
    def _ap_enumerate_module_names(cls):
        return module_names

    @classmethod
    def _ap_find_package_name(cls):
        return package_name

    # Items in a class dict and its name need to be native strings
    # under both py2 and py3
    cls_dict = {
        '_ap_find_package_name': _ap_find_package_name,
        '_ap_enumerate_module_names': _ap_enumerate_module_names,
        '_ap_enumerate_externalizable_root_interfaces': _ap_enumerate_externalizable_root_interfaces
    }

    bases = (AutoPackageSearchingScopedInterfaceObjectIO,)
    if iobase:
        bases = (iobase,) + bases

    cls_iio = type('AutoPackageSearchingScopedInterfaceObjectIO',
                   bases,
                   cls_dict)
    # If we don't set the __module__, it defaults to this module,
    # which would be very confusing.
    cls_iio.__module__ = _context.package.__name__ if _context.package else '__dynamic__'

    for iface in root_interfaces:
        logger.log(loglevels.TRACE,
                   "Registering ObjectIO for %s as %s", iface, cls_iio)
        component_zcml.adapter(_context, factory=(cls_iio,), for_=(iface,))

    # Now init the class so that it can add the things that internalization
    # needs.

    # Unfortunately, we are doing this eagerly instead of when the
    # configuration executes its actions runs because it must be done
    # before ``registerMimeFactories`` is invoked in order to add the
    # mimeType fields if they are missing. If we deferred it, we would
    # have to defer registerMimeFactories---and one action cannot
    # invoke another action or add more actions to the list and still
    # have any conflicts detected. Using the `order` parameter doesn't help us
    # much with that, either.

    # The plus side is that now that we are using component_zcml.utility()
    # to register legacy class factories too, there's not much harm in
    # initing the class early.

    legacy_factories = cls_iio.__class_init__()

    # Now that it's initted, register the factories
    for module in (factory_modules or modules):
        logger.log(loglevels.TRACE,
                   "Examining module %s for mime factories", module)
        registerMimeFactories(_context, module)

    if register_legacy_search_module:
        for name, factory in find_factories_in_module(legacy_factories):
            component_zcml.utility(_context,
                                   provides=_ILegacySearchModuleFactory,
                                   component=factory,
                                   name=name)


class IClassObjectFactoryDirective(interface.Interface):
    """
    Defines the ``ext:classObjectFactory`` directive.

    This directive registers a single
    :class:`nti.externalization.interfaces.IClassObjectFactory`.

    The factory will be registered for a class object.
    """

    factory = GlobalObject(
        title=u'The class object that will be created.',
        description=u"This must define the ``__external_can_create__`` attribute to be true.",
        required=True
    )

    name = PythonIdentifier(
        title=u"The name for the factory.",
        description=(u"If not given, the ``__external_class_name__`` of the class will be used. "
                     u"If that's not available, the ``__name__`` will be used."),
        required=False,
    )

    trusted = Bool(
        title=u"Ignore any value for ``__external_can_create__`` on the factory.",
        required=False,
        default=False,
    )

    title = MessageID(
        title=u"Title",
        description=u"Provides a title for the object.",
        required=False,
    )

    description = MessageID(
        title=u"Description",
        description=u"Provides a description for the object.",
        required=False
    )


def _validate_factory(factory, trusted):
    if not callable(factory):
        raise TypeError("Object %r must be callable" % factory)

    if not getattr(factory, '__external_can_create__', False) and not trusted:
        raise TypeError("Object %r must set __external_can_create__ to true" % factory)


def classObjectFactoryDirective(_context, factory, name='',
                                trusted=False,
                                title='', description=''):
    _validate_factory(factory, trusted)

    name = name or getattr(factory, '__external_class_name__', factory.__name__)

    factory = ClassObjectFactory(factory, title, description)
    component_zcml.utility(_context,
                           provides=IClassObjectFactory,
                           component=factory,
                           name=name)

class IBaseAnonymousObjectFactoryDirective(interface.Interface):
    """
    The common parts of anonymous object factory directives.

    .. versionadded:: 1.0a3
    """

    for_ = GlobalInterface(
        title=u"The interface that is the *parent* object this will be used for",
        required=True,
    )

    field = PythonIdentifier(
        title=u'The name of the schema field',
        description=u'The factory results will be assigned to this field.',
        required=True,
    )

class IAnonymousObjectFactoryDirective(IBaseAnonymousObjectFactoryDirective):
    """
    Defines the ``ext:anonymousObjectFactory`` directive.

    This directive registers a single
    :class:`nti.externaliaztion.interfaces.IAnonymousObjectFactory`
    for a single field used within a single object.

    .. versionadded:: 1.0a3
    """
    factory = GlobalObject(
        title=u'The class object that will be created.',
        required=True,
    )

    pass_external_object_to_factory = Bool(
        title=(u"Pass the external object to the factory."),
        description=(u"If true (*not* the default), then, the factory will recieve "
                     u"one argument, the anonymous external data. "
                     u'Otherwise, it gets no arguments.'),
        default=False,
        required=False,
    )

    trusted = Bool(
        title=u"Ignore any value for ``__external_can_create__`` on the factory.",
        required=False,
        default=False,
    )

    title = MessageID(
        title=u"Title",
        description=u"Provides a title for the object.",
        required=False,
    )

    description = MessageID(
        title=u"Description",
        description=u"Provides a description for the object.",
        required=False
    )


def anonymousObjectFactoryDirective(_context, factory, for_, field,
                                    pass_external_object_to_factory=False,
                                    trusted=False,
                                    title=u'', description=u''):
    _validate_factory(factory, trusted)

    field_name = str(field)
    field = for_[field]
    if field.interface is not for_:
        raise TypeError("Field %r is not directly part of the interface %r (it is %r)"
                        % (field_name, for_, field.interface))

    factory = AnonymousObjectFactory(factory, title, description)
    factory.__external_factory_wants_arg__ = pass_external_object_to_factory

    name = '%s.%s:%s' % (for_.__module__, for_.__name__, field_name)
    assert isinstance(name, str)
    component_zcml.utility(_context,
                           provides=IAnonymousObjectFactory,
                           component=factory,
                           name=name)

    _context.action(
        discriminator=('anonymousObjectFactory', for_, field_name),
        callable=field.setTaggedValue,
        args=('__external_factory__', name)
    )


class IAnonymousObjectFactoryInPlaceDirective(IBaseAnonymousObjectFactoryDirective):
    """
    Defines the ``anonymousObjectFactoryInPlace`` directive.

    This directive causes the external object itself to be
    used and updated in place. This is helpful when the
    object itself is not modelled, but its values are.

    Such data might look like this::

        {'home': {'MimeType': 'Address', ...},
         'work': {'MimeType': "Address', ...}}

    And it might have a schema field that looks like this:

    .. code-block:: python

        class IAddress(Interface):
            pass

        class IHasAddresses(Interface):

            addresses = Dict(
                     title=u"A mapping of address objects.",
                     key_type=TextLine(title=u"Adresss key"),
                     value_type=Object(IAddress))

    The ZCML would then look like this:

    .. code-block:: xml

         <ext:anonymoustObjectFactoryInPlace
              for="IHasAddresses"
              field="addresses" />

    .. versionadded:: 1.0a3

    """

def _in_place(data):
    return data

def anonymousObjectFactoryInPlaceDirective(_context, for_, field):
    anonymousObjectFactoryDirective(
        _context, _in_place, for_, field,
        pass_external_object_to_factory=True,
        trusted=True,
    )
