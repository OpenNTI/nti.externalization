#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Directives to be used in ZCML; helpers for registering factories
for mime types.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from ZODB import loglevels

from zope import interface
from zope.component import zcml as component_zcml
from zope.component.factory import Factory
from zope.configuration.fields import GlobalInterface
from zope.configuration.fields import GlobalObject
from zope.configuration.fields import Tokens

from nti.externalization.autopackage import AutoPackageSearchingScopedInterfaceObjectIO
from nti.externalization.interfaces import IMimeObjectFactory

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# pylint: disable=protected-access,inherit-non-class

@interface.implementer(IMimeObjectFactory)
class _MimeObjectFactory(Factory):
    """
    A factory meant to be registered as a named utility.
    The callable object SHOULD be a type/class object, because
    that's the only thing we base equality off of (class identity).
    """

    def __eq__(self, other):
        # Implementing equality is needed to prevent multiple inclusions
        # of the same module from different places from conflicting.
        try:
            return self._callable is other._callable
        except AttributeError: # pragma: no cover
            return NotImplemented

    def __hash__(self):
        return hash(self._callable)


class IRegisterInternalizationMimeFactoriesDirective(interface.Interface):
    """
    The arguments needed for registering factories.
    """

    module = GlobalObject(
        title=u"Module to scan for Mime factories to add",
        required=True,
    )


def registerMimeFactories(_context, module):
    """
    Poke through the classes defined in `module`. If a class
    defines the ``mimeType`` attribute and can be created externally,
    (because it defines ``__external_can_create__`` to be true), registers
    a factory utility under the ``mimeType`` name. (For backwards compatibility,
    ``mime_type`` is accepted if there is no ``mimeType``.)

    See :func:`nti.externalization.internalization.find_factory_for`.

    :param module module: The module to inspect.
    """
    # This is a pretty loose check. We can probably do better. For example,
    # pass an interface parameter and only register things that provide
    # that interface, or at least check to see if they are a ``type``
    mod_name = module.__name__
    for object_name, value in vars(module).items():
        __traceback_info__ = object_name, value

        try:
            ext_create = value.__external_can_create__
            v_mod_name = value.__module__
        except AttributeError:
            continue

        try:
            mime_type = value.mimeType
        except AttributeError:
            try:
                mime_type = value.mime_type
            except AttributeError:
                continue

        if mime_type and ext_create and mod_name == v_mod_name:
            logger.log(loglevels.TRACE,
                       "Registered mime factory utility %s = %s (%s)",
                       object_name, value, mime_type)
            factory = _MimeObjectFactory(value,
                                         title=object_name,
                                         interfaces=list(interface.implementedBy(value)))
            component_zcml.utility(_context,
                                   provides=IMimeObjectFactory,
                                   component=factory,
                                   name=mime_type)


class IAutoPackageExternalizationDirective(interface.Interface):
    """
    This directive combines the effects of :class:`.IRegisterInternalizationMimeFactoriesDirective`
    with that of :mod:`.autopackage`, removing all need to repeat root interfaces
    and module names.
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
        title=u"If given, module names that should be searched for internalization factories",
        description=u"If not given, all modules will be examined.",
        value_type=GlobalObject(),
        required=False)

    iobase = GlobalObject(
        title=(u"If given, a base class that will be used. "
               u"You can customize aspects of externalization that way."),
        required=False)




def autoPackageExternalization(_context, root_interfaces, modules,
                               factory_modules=None, iobase=None):

    ext_module_name = root_interfaces[0].__module__
    package_name = ext_module_name.rsplit('.', 1)[0]

    @classmethod
    def _ap_enumerate_externalizable_root_interfaces(cls, unused_ifaces):
        return root_interfaces

    @classmethod
    def _ap_enumerate_module_names(cls):
        return [m.__name__.split('.')[-1] for m in modules]

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
    # FIXME: We are doing this eagerly instead of when ZCML runs
    # because it must be done before ``registerMimeFactories``
    # is invoked in order to add the mimeType fields if they are missing.
    # Rewrite so that this can be done as an ZCML action.
    # _context.action( discriminator=('class_init', tuple(modules)),
    #                  callable=cls_iio.__class_init__,
    #                  args=() )
    cls_iio.__class_init__()

    # Now that it's initted, register the factories
    for module in (factory_modules or modules):
        logger.log(loglevels.TRACE,
                   "Examining module %s for mime factories", module)
        registerMimeFactories(_context, module)
