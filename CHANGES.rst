=========
 Changes
=========


2.3.0 (2021-08-02)
==================

- Add a new base class, ``StandardInternalObjectExternalizer``. See
  `PR 120
  <https://github.com/NextThought/nti.externalization/pull/120>`_ and
  `issue 117 <https://github.com/NextThought/nti.externalization/issues/117>`_.
- Rename ``IExternalMappingDecorator`` to
  ``IExternalStandardDictionaryDecorator`` to emphasize that it is
  only used if you (directly or through a super class) call
  ``to_standard_external_dictionary``. A compatibility alias remains.
  See `PR 120
  <https://github.com/NextThought/nti.externalization/pull/120>`_ and
  `issue 118
  <https://github.com/NextThought/nti.externalization/issues/118>`_.
- Docs-deprecated aliases in ``nti.externalization.interfaces`` now also
  emit deprecation warnings at runtime.
- Other documentation improvements. Sphinx can now run all the
  doctests (on Python 3); many doctests are still run an Python 2.

2.2.0 (2021-04-14)
==================

- Add support for Python 3.9.

- Depend on BTrees 4.8 and above. This simplifies externalization
  checks. See `issue 111 <https://github.com/NextThought/nti.externalization/issues/111>`_.

2.1.0 (2020-08-03)
==================

- Add support for "externalization policies." These are instances of
  ``ExternalizationPolicy`` that can be used to tweak certain
  low-level details of externalization without replacing
  externalization objects wholesale. They are intended to have a very
  low performance impact.

  The only supported detail that can be changed right now is whether
  the standard created and last modified fields are externalized as
  Unix timestamps (the default) or as ISO 8601 strings.

  See https://github.com/NextThought/nti.externalization/issues/109


2.0.0 (2020-07-02)
==================

- Change ``ILocatedExternalMapping``: Previously it extended the
  legacy ``zope.interface.common.mapping.IFullMapping``. Now it
  extends the modern ``zope.interface.common.collections.IMapping``.
  Note that this does not require mutability unlike the older
  interface. (The ``LocatedExternalDict`` class provided by this
  package is fully mutable and implements ``IMutableMapping``. It also
  continues to implement ``IFullMapping``, but use of that interface
  is discouraged.)

- Change ``ILocatedExternalSequence``: Previously it extended the
  legacy ``zope.interface.common.sequence.ISequence``. Now it extends
  the modern ``zope.interface.common.collections.ISequence``.
  Note that this does not require mutability unlike the older
  interface. (The ``LocatedExternalList`` class provided by this
  package is fully mutable and implements ``IMutableSequence``.)

- Fix the interface resolution order for ``LocatedExternalList``.
  Previously, with zope.interface 5, it began implementing both
  ``IMutableSequence`` (the new interface from
  ``zope.interface.common.collections``) as well as the older
  interface ``ISequence`` (from ``zope.interface.common.sequence``);
  the two have inconsistent resolution orders. Now, it only implements
  ``IMutableSequence`` and a subset of the legacy interfaces that do
  not conflict. See `issue 105
  <https://github.com/NextThought/nti.externalization/issues/105>`_.


1.1.3 (2020-06-25)
==================

- Correctly fire ``IObjectWillUpdateFromExternalEvent`` events before
  updating an object.


1.1.2 (2020-04-07)
==================

- Adapt to a change in zope.container 4.4.0 that exposed unsafe
  assumptions that ``providedBy(obj)`` would return the exact same
  object with the exact same state on a subsequent call. This was
  always a bug in the case of concurrency (e.g., if a different thread
  called ``directlyProvides`` on the same object, or adjusted the
  ``__bases__`` of some interface in the IRO); the zope.container
  changes made it possible without concurrency. See
  https://github.com/zopefoundation/zope.container/issues/38 and
  https://github.com/NextThought/nti.externalization/issues/104.


1.1.1 (2020-03-27)
==================

- Fix a faulty assertion error. See `issue 102
  <https://github.com/NextThought/nti.externalization/issues/102>`_.


1.1.0 (2020-03-27)
==================

- Make instances of ``fractions.Fraction`` externalize as a string
  such as ``"1/3"``. When received by a schema field that can parse
  this format, such as ``zope.schema.Rational`` (or higher on the
  numeric tower), this means fractions can be round-tripped.
- Support externalizing ``decimal.Decimal`` objects in the YAML
  representation.


1.0.0 (2020-03-19)
==================

- Add compatibility with, and require, zope.interface 5.0.

- Document which tagged values are inherited and which are not.

- Stop inheriting ``_ext_is_marker_interface``.


1.0.0a14 (2019-11-13)
=====================

- Build with Cython 0.29.14 using '3str' as the language level.

- Add support for Python 3.8.

- Update PyYAML to 5.1 and change the default output style slightly.

- Fix tests with Persistent 4.4.3 and above.

- Support zope.interface 4.7, which lets tagged values on interfaces
  be inherited, when using ``<registerAutoPackageIO>`` on a module
  that had multiple objects implementing a derived interface. See `issue 97
  <https://github.com/NextThought/nti.externalization/issues/97>`_.

1.0.0a13 (2018-09-20)
=====================

- Support ``IFromBytes`` fields introduced by zope.schema 4.8.0. See
  `issue 92
  <https://github.com/NextThought/nti.externalization/issues/92>`_.

- Make ``validate_field_value`` (and by extension
  ``InterfaceObjectIO.update_from_external_object``) call
  ``fromObject`` defined by any fields for non-byte and non-text data.
  Previously, only if the field raised a ``WrongContainedTypeError``
  would ``fromObject`` be called.

1.0.0a12 (2018-09-11)
=====================

- Add support for zope.schema 4.7.0 and nti.schema 1.5.0. Drop support
  for older versions, which includes dropping support for
  ``dm.zope.schema.Object`` fields.


1.0.0a11 (2018-08-29)
=====================

- The ``@WithRepr`` decorator takes into account the updated default
  repr of Persistent objects with persistent 4.4 and doesn't hide it.

- Subclasses of ``ExternalizableInstanceDict`` that have non-str
  (unicode on Python 2, bytes on Python 3) keys in their ``__dict__``
  do not throw ``TypeError`` when externalizing. Instead, the non-str
  values are converted to strs (using ASCII encoding) and the
  ``_p_changed`` attribute, if any, is set.

1.0.0a10 (2018-08-21)
=====================

- The ``registry`` argument to most functions is deprecated and
  ignored. Instead of making calls to ``registry.queryAdapter``, we
  now invoke the interface directly. For example,
  ``IInternalObjectExternalizer(containedObject)``. This lets
  individual objects have a say if they already provide the interface
  without going through the legacy code paths (it also calls
  ``__conform__`` on the object if needed).


1.0.0a9 (2018-08-20)
====================

- Allow subclasses of ``InterfaceObjectIO`` to have non-frozenset
  values for ``_ext_primitive_out_ivars_``. This issues a warning and
  in the future will be a TypeError.


1.0.0a8 (2018-08-16)
====================

- Better support for internalizing anonymous value objects discovered
  in a ``Dict`` value. Now, they won't raise a
  ``ComponentLookupError`` when ``require_updater`` is True, and they
  will be given a ``MimeType`` based on the schema (if they don't have one).


1.0.0a7 (2018-07-31)
====================

- Avoid a ``TypeError`` from ``validate_named_field_value`` when
  external objects have unicode keys.

- ``LocatedExternalDict`` objects accept more constructor arguments
  and allow arbitrary attributes.

1.0.0a6 (2018-07-31)
====================

- ``InterfaceObjectIO`` only returns an anonymous factory for ``IDict``
  fields when it wants objects for the value.

- ``StandardExternalFields`` and ``StandardInternalFields`` are
  deprecated aliases in ``nti.externalization.externalization``.

- ``update_from_external_object`` properly handles the case where
  ``INamedExternalizedObjectFactoryFinder`` and
  ``IInternalObjectUpdater`` are registered with different levels of
  specificity, and the finder also implements
  ``IInternalObjectUpdater``. Before, the finder would, perhaps
  incorrectly, be used as the updater.

1.0.0a5 (2018-07-30)
====================

- Objects inheriting from ``InterfaceObjectIO`` and registered with
  the component registry (in ZCML) for ``IInternalObjectIO`` can still
  be found and used as ``INamedExternalizedObjectFactoryFinder``, an
  interface implemented by ``InterfaceObjectIO`` through
  ``IInternalObjectIOFinder``. A warning will be issued to update the
  registration (which generally means removing the ``provides`` line
  in ZCML).

- ``ExternalizableInstanceDict`` no longer inherits from
  ``AbstractDynamicIO``, it just implements the same interface (with
  the exception of many of the ``_ext`` methods). This class is deprecated.

- Formally document the ``notify_modified`` member of
  ``nti.externalization.internalization``. ``notifyModified`` is a
  deprecated alias.

1.0.0a4 (2018-07-30)
====================

- Make ``InterfaceObjectIO._ext_self`` readable from Python, even
  though that is not documented (and may change again in the future).
  Document the intended API, ``_ext_replacement()``. See `issue 73
  <https://github.com/NextThought/nti.externalization/issues/73>`_.

- Make ``AbstractDynamicObjectIO._ext_getattr`` handle a default
  value, and add ``_ext_replacement_getattr``  for when it will only
  be called once. See `issue 73
  <https://github.com/NextThought/nti.externalization/issues/73>`_.

1.0.0a3 (2018-07-28)
====================

- The ``@NoPickle`` decorator also works with ``Persistent``
  subclasses (and may or may not work with multiple-inheritance
  subclasses of ``Persistent``, depending on the MRO,
  but that's always been the case for regular objects). A
  ``Persistent`` subclass being decorated with ``@NoPickle`` doesn't
  make much sense, so a ``RuntimeWarning`` is issued. A warning is
  also issued if the class directly implements one of the pickle
  protocol methods.

- Updating objects that use ``createFieldProperties`` or otherwise
  have ``FieldProperty`` objects in their type is at least 10% faster
  thanks to avoiding double-validation due to a small monkey-patch on
  ``FieldProperty``. See `issue 67
  <https://github.com/NextThought/nti.externalization/issues/67>`_.

- Proxies around objects that implement ``toExternalObject`` are
  allowed again; the proxied object's ``toExternalObject`` will be called.

- The signature for ``updateFromExternalObject()`` has been tightened.
  It should be ``(self, external_object, context, **kwargs)``, where
  ``**kwargs`` is optional, as is context. ``**kwargs`` currently
  contains nothing useful. Uses of ``dataserver=None`` in the
  signature will generate a warning. This may be tightened further in
  the future. See `issue 30
  <https://github.com/NextThought/nti.externalization/issues/30>`_.

- ``__ext_ignore_updateFromExternalObject__`` is officially
  deprecated and generates a warning.

- ``update_from_external_object`` caches certain information about the
  types of the updater objects, making it 8-25% faster.

- ``update_from_external_object`` mutates sequences contained in a
  dict in-place instead of overwriting with a new list.

- ``update_from_external_object`` mutates sequences at the top level
  instead of returning a new list.

- Add support for finding factories for incoming data which do not
  specify a MIME type or class field based on the key they are
  assigned to. This aids in consuming data produced by foreign systems
  or using ``Dict`` schema fields that require modelled
  values. See `issue 51
  <https://github.com/NextThought/nti.externalization/issues/51>`_ and
  `PR 68
  <https://github.com/NextThought/nti.externalization/pull/68>`_.

- Schemas that use ``InterfaceObjectIO`` (including through the ZCML
  directive ``registerAutoPackageIO``) can use ``Dict`` fields more
  easily on internalization (externalization has always worked): They
  automatically internalize their values by treating the ``Dict`` as
  anonymous external data.

- Strings can automatically be adapted into ``ITimeDelta`` objects.


1.0.0a2 (2018-07-05)
====================

- The low levels of externalization no longer catch and hide
  POSKeyError. This indicates a problem with the database. See
  https://github.com/NextThought/nti.externalization/issues/60

- Remove support for ``object_hook`` in
  ``update_from_external_object``. See
  https://github.com/NextThought/nti.externalization/issues/29.

- A number of deprecated aliases for moved functions have been
  removed.

- On CPython, some of the modules are compiled as extension modules
  using Cython for a 10-30% increase in speed. Set the ``PURE_PYTHON``
  environment variable to disable this at runtime.

- The unused, undocumented method
  ``stripSyntheticKeysFromExternalDictionary`` was removed from
  instances of ``ExternalizableDictionaryMixin``. Use the import instead.

- Unused keyword arguments for ``to_standard_external_dictionary``
  and ``to_minimal_standard_external_dictionary`` now produce a warning.
  In the future, extra keyword arguments will be an error.

- ``notifyModified`` no longer accepts the ``eventFactory`` argument.

- The ``notify_modified`` alias for ``notifyModified`` has been removed.

- Decorating external mappings and external objects handled
  ``decorate_callback`` differently. This argument is only used when
  ``decorate`` is false. This argument is also confusing and should be
  considered deprecated.

- ``choose_field`` no longer has the undocumented conversion behaviour for the
  CREATOR external field name.

1.0.0a1 (2017-09-29)
====================

- First PyPI release.
- Add support for Python 3.
- Drop support for externalizing to plists. See
  https://github.com/NextThought/nti.externalization/issues/21
- Reach 100% test coverage and ensure we remain there through CI.
- Introduce ``nti.externalization.extension_points`` to hold hook
  functions. Move the Pyramid integration there (and deprecate that).
  Also move the NTIID support there (but the old name works too).
  See https://github.com/NextThought/nti.externalization/issues/27
- Deprecate
  ``nti.externalization.internalization.register_legacy_search_module``.
  See https://github.com/NextThought/nti.externalization/issues/35
- Stop ``ext:registerAutoPackageIO`` from registering the legacy
  class-name based factories by default. If you need class-name based
  factories, there are two options. The first is to explicitly
  register ``IClassObjectFactory`` objects in ZCML (we could add a
  scanning directive to make that more convenient for large numbers of
  classes), and the second is to set ``register_legacy_search_module``
  to a true value in the ZCML directive for
  ``ext:registerAutoPackageIO``. Note that we expect the behaviour of
  this attribute to change in the near future.
  See https://github.com/NextThought/nti.externalization/issues/33
- Make ``ext:registerAutoPackageIO`` perform legacy class
  registrations when the configuration context executes, not when the
  directive runs. This means that conflicts in legacy class names will be
  detected at configuration time. It also means that legacy class names can
  be registered locally with ``z3c.baseregistry`` (previously they
  were always registered in the global site manager).
  See https://github.com/NextThought/nti.externalization/issues/28
- Drop dependency on ``zope.preference`` and ``zope.annotation``. They
  were not used by this package, although our ``configure.zcml`` did
  include them. If you use ``zope.preference`` or ``zope.annotation``,
  please include them in your own ZCML file.
- Drop hard dependency on Acquisition. It is still used if available
  and is used in test mode.
- Add public implementations of ``IMimeObjectFactory`` and
  ``IClassObjectFactory`` in ``nti.externalization.factory``.
- Drop dependency on ``nti.zodb`` and its
  ``PersistentPropertyHolder``. The datastructures in
  ``nti.externalization.persistence`` no longer extend that class; if
  you have further subclasses that add
  ``nti.zodb.peristentproperty.PropertyHoldingPersistent`` properties,
  you'll need to be sure to mixin this class now.
  See https://github.com/NextThought/nti.externalization/issues/43
- Add the ``<ext:classObjectFactory>`` directive for registering
  ``Class`` based factories. (Note: MIME factories are preferred.)
- Callers of ``to_standard_external_dictionary`` (which includes
  AutoPackageScopedInterfaceIO) will now automatically get a
  ``MimeType`` value if one can be found. Previously only callers of
  ``to_minimal_standard_external_dictionary`` would.
