# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
# -*- coding: utf-8 -*-
"""
Support for magically finding factories given class names.

.. deprecated:: 1.0
"""
## Implementation of legacy search modules.

# We go through the global component registry, using a local
# interface. We treat the registry as a cache and we will only
# look at any given module object one time. We can detect duplicates
# in this fashion. (For cython compilation, this lives in interfaces.)


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import types
import warnings

from zope import component

from zope.dottedname.resolve import resolve

from nti.externalization.interfaces import _ILegacySearchModuleFactory
from nti.externalization._base_interfaces import NotGiven


logger = __import__('logging').getLogger(__name__)

__all__ = [
    'register_legacy_search_module',
]

#: .. deprecated:: 1.0
#: This is legacy functionality, please do not access directly.
#: The public interface is through :func:`register_legacy_search_module`
LEGACY_FACTORY_SEARCH_MODULES = set()

try:
    from zope.testing.cleanup import addCleanUp # pylint: disable=ungrouped-imports
except ImportError: # pragma: no cover
    pass
else:
    addCleanUp(LEGACY_FACTORY_SEARCH_MODULES.clear)


def register_legacy_search_module(module_name):
    """
    The legacy creation search routines will use the modules
    registered by this method.

    Note that there are no order guarantees about how
    the modules will be searched. Duplicate class names are thus
    undefined.

    :param module_name: Either the name of a module to look for
        at runtime in :data:`sys.modules`, or a module-like object
        having a ``__dict__``.

    .. deprecated:: 1.0
        Use explicit mime or class factories instead.
        See https://github.com/NextThought/nti.externalization/issues/35
    """
    warnings.warn("This function is deprecated", FutureWarning)
    if module_name:
        LEGACY_FACTORY_SEARCH_MODULES.add(module_name)

_ext_factory_warnings = set()

def search_for_external_factory(typeName):
    """
    Deprecated, legacy functionality. Given the name of a type,
    optionally ending in 's' for plural, attempt to locate that type.

    For every string package name we find in ``LEGACY_FACTORY_SEARCH_MODULES``, we will
    resolve the module and mutate the set to replace it.
    """
    if not typeName:
        return None

    # First, register anything that needs to be registered still.
    # Note that there are potential race conditions here.
    if LEGACY_FACTORY_SEARCH_MODULES:
        register_factories_from_search_set()


    # Now look for a factory, using both the given name and its
    # lower case version.
    className = typeName[0:-1] if typeName.endswith('s') else typeName

    gsm = component.getGlobalSiteManager()
    factory = gsm.queryUtility(_ILegacySearchModuleFactory, name=className)
    if factory is None and className.lower() != className:
        factory = gsm.queryUtility(_ILegacySearchModuleFactory, name=className.lower())

    if factory is not None and typeName not in _ext_factory_warnings:
        # Previously we used the `warnings` module to produce a
        # FutureWarning for each distinct typeName. This had the
        # problem that it would result in an ever growing
        # __warningregistry__ in this module. We worked around that by
        # periodically clearing it (which could sometimes result in
        # duplicate warnings).

        # However, if we're compiled into an extension module, it won't be
        # this module that gets the __warningregistry__, it will be whatever
        # the last Python caller was, which is unpredictable.

        # Therefore, to control this, we instead switch to logging a warning
        # and managing our own cache.
        _ext_factory_warnings.add(typeName)
        logger.debug("Deprecated: Using runtime legacy class finder for %r", typeName)
        if len(_ext_factory_warnings) > 4096:
            _ext_factory_warnings.clear() # pragma: no cover

    return factory

def count_legacy_classes_found():
    # For testing.
    return len(_ext_factory_warnings)

def _name_key(obj):
    return getattr(obj, '__name__', '')

def register_factories_from_search_set():
    """
    Takes the current contents of `LEGACY_FACTORY_SEARCH_MODULES`
    and registers all found factories there.
    """
    search_modules = set(LEGACY_FACTORY_SEARCH_MODULES)
    LEGACY_FACTORY_SEARCH_MODULES.clear()

    # Make sure we have objects, not strs.
    # Let this throw ImportError, it's a programming bug
    modules = [module if hasattr(module, '__dict__') else resolve(module)
               for module in search_modules]

    # Sort them as best we can.
    modules.sort(key=_name_key)
    for module in modules:
        register_factories_from_module(module)

def register_factories_from_module(module):
    """
    Given a module object, find all the factories it contains
    and register them in the global site manager.
    """
    gsm = component.getGlobalSiteManager()
    for name, factory in find_factories_in_module(module):
        registered = gsm.queryUtility(_ILegacySearchModuleFactory, name)
        if registered is not None:
            logger.info("Found duplicate registration for legacy search path."
                        "Factory %r will be used for class name %r overriding %r",
                        registered, name, factory)
            continue

        gsm.registerUtility(factory, name=name, provided=_ILegacySearchModuleFactory)

def find_factories_in_module(module,
                             case_sensitive=False):
    """
    Look through the `vars` of *module* to find any eligible factory
    functions.

    An eligible factory is a callable object with a True value for
    the attribute ``__external_can_create__``.

    If *module* is really a module, then only objects that
    are defined in that module will be found. Otherwise (*module* is
    some namespace object) any callable object is acceptable.

    :param bool case_sensitive: If False (the default), then the results will
        have each factory twice, once with its found name, and once
        with its name lower cased.
    :return: An iterable of found (name, factory).
    """
    # It's not totally clear why this is in legacy_factories;
    # it's used from modern stuff like ext:registerAutoPackageIO
    result = []
    mod_name = module.__name__
    # If we're dealing with a namespace object, such as what
    # AutoPackaegIO produces, it may represent types from many modules
    # on purpose. OTOH, if we get here via a string that was supposed
    # to be a module, then we need to respect that and ignore imports.
    # This is complicated by the fact that zope.deprecation puts DeprecationProxy
    # objects into sys.modules, but they appear to handle that correctly
    accept_any_module = not isinstance(module, types.ModuleType)
    for name, value in sorted(vars(module).items()):
        if (callable(value)
                and getattr(value, '__external_can_create__', False)
                and (accept_any_module or getattr(value, '__module__', NotGiven) == mod_name)):
            result.append((name, value))
            if not case_sensitive and name.lower() != name:
                result.append((name.lower(), value))

    return result


 # pylint:disable=wrong-import-position,wrong-import-order
from nti.externalization._compat import import_c_accel
import_c_accel(globals(), 'nti.externalization.internalization._legacy_factories')
