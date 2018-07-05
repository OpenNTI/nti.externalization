=========
 Changes
=========


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
