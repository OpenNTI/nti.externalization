#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for handling the IO for all the objects in a *package*,
typically via a ZCML directive.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from ZODB.loglevels import TRACE
from zope import interface

from zope.dottedname import resolve as dottedname
from zope.mimetype.interfaces import IContentTypeAware

from nti.externalization.datastructures import ModuleScopedInterfaceObjectIO


logger = __import__('logging').getLogger(__name__)

# If we extend ExtensionClass.Base, __class_init__ is called automatically
# for each subclass. But we also start participating in acquisition, which
# is probably not what we want
# import ExtensionClass


class _ClassNameRegistry(object):
    __name__ = ''

class AutoPackageSearchingScopedInterfaceObjectIO(ModuleScopedInterfaceObjectIO):
    """
    A special, magic, type of interface-driven input and output, one designed
    for the common use case of a *package* that provides the common pattern:

    * interfaces.py
    * externalization.py (where a subclass of this object lives)
    * configure.zcml (where the subclass is registered as an adapter for each object;
      you may also then provide mime-factories as well)
    * other modules, where types are defined for the external interfaces.

    Once you derive from this class and implement the abstract methods, you
    need to call :meth:`__class_init__` (exactly once) on your subclass.

    You do not have to derive from this class; the common case is
    handled via the ZCML directive ``<ext:registerAutoPackageIO>``
    (:class:`nti.externalization.zcml.IAutoPackageExternalizationDirective`).
    You can still customize the behaviour by providing the ``iobase`` argument.
    """

    @classmethod
    def _ap_compute_external_class_name_from_interface_and_instance(cls, unused_iface, impl):
        """
        Assigned as the tagged value ``__external_class_name__`` to each
        interface. This will be called on an instance implementing iface.

        .. seealso:: :class:`~.InterfaceObjectIO`
        """
        # Use the __class__, not type(), to work with proxies
        return cls._ap_compute_external_class_name_from_concrete_class(impl.__class__)

    @classmethod
    def _ap_compute_external_class_name_from_concrete_class(cls, a_type):
        """
        Return the string value of the external class name.

        By default this will be either the value of
        ``__external_class_name__`` or, if not found, the value of
        ``__name__``.

        Subclasses may override.
        """
        return getattr(a_type, '__external_class_name__', a_type.__name__)

    @classmethod
    def _ap_compute_external_mimetype(cls, package_name, unused_a_type, ext_class_name):
        """
        Return the string value of the external mime type for the given
        type in the given package having the given external name (probably
        derived from :meth:`_ap_compute_external_class_name_from_concrete_class`).

        For example, given the arguments ('nti.assessment', FooBar, 'FooBar'), the
        result will be 'application/vnd.nextthought.assessment.foobar'.

        Subclasses may override.
        """
        # 'nti.assessment', FooBar, 'FooBar' => vnd.nextthought.assessment.foobar
        # Recall that mimetypes should be byte strings
        local = package_name.rsplit('.', 1)[-1]
        return str('application/vnd.nextthought.' + local + '.' + ext_class_name.lower())

    @classmethod
    # TODO: We can probably do something with this
    def _ap_enumerate_externalizable_root_interfaces(cls, interfaces):
        """
        Return an iterable of the root interfaces in this package that should be
        externalized.

        Subclasses must implement.
        """
        raise NotImplementedError()

    @classmethod
    def _ap_enumerate_module_names(cls):
        """
        Return an iterable of module names in this package that should be searched to find
        factories.

        Subclasses must implement.
        """
        raise NotImplementedError()

    @classmethod
    def _ap_find_factories(cls, package_name):
        """
        Return a namespace object whose attribute names are external class
        names and whose attribute values are classes that can be
        created externally.

        For each module returned by
        :meth:`_ap_enumerate_module_names`, we will resolve it against
        the value of *package_name* (normally that given by
        :meth:`_ap_find_package_name`). The module is then searched for classes
        that live in that module. If a class implements an interface that has a
        tagged value of ``__external_class_name__``, it is added to the return value.
        The external class name (the name of the attribute) is computed by
        :meth:`_ap_compute_external_class_name_from_concrete_class`.

        Each class that is found has an appropriate ``mimeType`` added
        to it (derived by :meth:`_ap_compute_external_mimetype`), if
        it does not already have one; these classes also have the
        attribute ``__external_can_create__`` set to true on them if
        they do not have a value for it at all. This makes the classes
        ready to be used with
        :func:`~nti.externalization.zcml.registerMimeFactories`, which
        is done automatically by the ZCML directive
        :class:`~nti.externalization.zcml.IAutoPackageExternalizationDirective`.

        Each class that is found is also marked as implementing
        :class:`zope.mimetype.interfaces.IContentTypeAware`.
        """

        registry = _ClassNameRegistry()
        registry.__name__ = package_name

        for mod_name in cls._ap_enumerate_module_names():
            mod = dottedname.resolve(package_name + '.' + mod_name)
            for _, v in mod.__dict__.items():
                # ignore imports and non-concrete classes
                # NOTE: using issubclass to properly support metaclasses
                if getattr(v, '__module__', None) != mod.__name__ \
                    or not issubclass(type(v), type):
                    continue
                cls._ap_handle_one_potential_factory_class(registry, package_name, v)
        return registry

    @classmethod
    def _ap_handle_one_potential_factory_class(cls, namespace, package_name, implementation_class):
        # Private helper function
        # Does this implement something that should be externalizable?
        check_ext = any(iface.queryTaggedValue('__external_class_name__')
                        for iface in interface.implementedBy(implementation_class))
        if not check_ext:
            return

        ext_class_name = cls._ap_compute_external_class_name_from_concrete_class(implementation_class)
        # XXX: Checking for duplicates
        setattr(namespace,
                ext_class_name,
                implementation_class)

        if not implementation_class.__dict__.get('mimeType', None):
            # NOT hasattr. We don't use hasattr because inheritance would
            # throw us off. It could be something we added, and iteration order
            # is not defined (if we got the subclass first we're good, we fail if we
            # got superclass first).
            # Also, not a simple 'in' check. We want to allow for setting mimeType = None
            # in the dict for static analysis purposes

            # legacy check
            if 'mime_type' in implementation_class.__dict__:
                implementation_class.mimeType = implementation_class.mime_type
            else:
                implementation_class.mimeType = cls._ap_compute_external_mimetype(
                    package_name,
                    implementation_class,
                    ext_class_name)
                implementation_class.mime_type = implementation_class.mimeType

            if not IContentTypeAware.implementedBy(implementation_class):
                # well it does now
                interface.classImplements(implementation_class,
                                          IContentTypeAware)

        # Opt in for creating, unless explicitly disallowed
        if not hasattr(implementation_class, '__external_can_create__'):
            implementation_class.__external_can_create__ = True

            # Let them have containers
            if not hasattr(implementation_class, 'containerId'):
                implementation_class.containerId = None

    @classmethod
    def _ap_find_package_name(cls):
        """
        Return the package name to search for modules.

        By default we look at the module name of the *cls* object
        given.

        Subclasses may override.
        """
        ext_module_name = cls.__module__
        package_name = ext_module_name.rsplit('.', 1)[0]
        return package_name

    @classmethod
    def _ap_find_package_interface_module(cls):
        """
        Return the module that should be searched for interfaces.

        By default, this will be the ``interfaces`` sub-module of the package
        returned from :meth:`_ap_find_package_name`.

        Subclasses may override.
        """
        # First, get the correct working module
        package_name = cls._ap_find_package_name()

        # Now the interfaces
        return dottedname.resolve(package_name + '.interfaces')

    @classmethod
    def __class_init__(cls):  # ExtensionClass.Base class initializer
        """
        Class initializer. Should be called exactly *once* on each
        distinct subclass.

        First, makes all interfaces returned by
        :func:`_ap_enumerate_externalizable_root_interfaces`
        externalizable by setting the ``__external_class_name__``
        tagged value (to :func:`_ap_compute_external_class_name_from_interface_and_instance`).
        (See :class:`~.InterfaceObjectIO`.)

        Then, find all of the object factories and initialize them
        using :func:`_ap_find_factories`. A namespace object representing these
        factories is returned.

        .. versionchanged:: 1.0
            Registering the factories using :func:`~.register_legacy_search_module`
            is no longer done by default. If you are using this class outside of ZCML,
            you will need to subclass and override this method to make that call
            yourself. If you are using ZCML, you will need to set the appropriate
            attribute to True.
        """
        # Do nothing when this class itself is initted
        if cls.__name__ == 'AutoPackageSearchingScopedInterfaceObjectIO' \
            and cls.__module__ == __name__:
            return False

        # First, get the correct working module
        package_name = cls._ap_find_package_name()

        # Now the interfaces
        package_ifaces = cls._ap_find_package_interface_module()
        cls._ext_search_module = package_ifaces
        logger.log(TRACE, "Autopackage tagging interfaces in %s",
                   package_ifaces)
        # Now tag them
        for iface in cls._ap_enumerate_externalizable_root_interfaces(package_ifaces):
            iface.setTaggedValue('__external_class_name__',
                                 cls._ap_compute_external_class_name_from_interface_and_instance)

        # Now find the factories
        factories = cls._ap_find_factories(package_name)
        return factories
