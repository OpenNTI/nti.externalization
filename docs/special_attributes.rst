====================
 Special Attributes
====================

This document covers some of the special attributes used by this
module.

When we discuss interfaces or the contents of attributes, we are
referring to `tagged values <zope.interface.taggedValue>`.

* ``__external_class_name__``

Used an a class or interface to determine the value of the ``Class``
standard external value. Usually this is a string, but when using
`.InterfaceObjectIO` (including ``ext:registerAutoPackageIO``) it can
be a callable.

.. seealso:: `.AutoPackageSearchingScopedInterfaceObjectIO._ap_compute_external_class_name_from_interface_and_instance`
   and `.AutoPackageSearchingScopedInterfaceObjectIO._ap_find_factories`

* ``__external_can_create__``

This boolean value is set to true on factory functions (e.g.,
classes). ``ext:registerAutoPackageIO`` sets it to true automatically.

* ``mimeType``

Part of the :class:`zope.mimetype.interfaces.IContentTypeAware`
interface. This is read from :ref:`factories` when creating factory
registrations. It also forms one of the :ref:`standard external fields
<standard_fields>`.


* ``_ext_excluded_out``

A tagged value on individual attributes of an interface to prevent
them from being externalized. See `.InterfaceObjectIO`.

* ``__external_factory_wants_arg__``

(Provisional). Attribute of a :ref:`factory <factories>`. When creating
sub-objects and invoking a factory, should we pass the external object
to the factory? If not true or not set, the factory receives no
arguments.

.. versionadded:: 1.0a3

* ``__external_default_implementation__``

(Provisional). Tagged value of an interface implemented by one of the
factories discovered by ``ext:registerAutoPackageIO`` holding the
primary factory discovered for that interface. Used when internalizing
anonymous external data.

.. versionadded:: 1.0a8
