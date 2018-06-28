# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
# -*- coding: utf-8 -*-
"""
Functions for taking externalized objects and creating application
model objects.

"""

# There are a *lot* of fixme (XXX and the like) in this file.
# Turn those off in general so we can see through the noise.
# pylint:disable=fixme



from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


# stdlib imports
import collections
import inspect
import numbers
import sys
import types
import warnings

from persistent.interfaces import IPersistent
from six import string_types
from six import text_type
from six import reraise
from six import iteritems
from zope import component
from zope import interface

from zope.dottedname.resolve import resolve
from zope.event import notify as _zope_event_notify
from zope.lifecycleevent import Attributes
from zope.schema.interfaces import IField
from zope.schema.interfaces import IFromUnicode
from zope.schema.interfaces import SchemaNotProvided
from zope.schema.interfaces import ValidationError
from zope.schema.interfaces import WrongContainedType
from zope.schema.interfaces import WrongType

from nti.externalization._compat import identity
from nti.externalization.interfaces import IClassObjectFactory
from nti.externalization.interfaces import IExternalizedObjectFactoryFinder
from nti.externalization.interfaces import IExternalReferenceResolver
from nti.externalization.interfaces import IFactory
from nti.externalization.interfaces import IInternalObjectUpdater
from nti.externalization.interfaces import IMimeObjectFactory
from nti.externalization.interfaces import ObjectModifiedFromExternalEvent # XXX: Move to base_interfaces
from nti.externalization.interfaces import StandardExternalFields

from ._base_interfaces import get_standard_external_fields
from ._base_interfaces import get_standard_internal_fields

StandardExternalFields = get_standard_external_fields()
StandardInternalFields = get_standard_internal_fields()


# pylint: disable=protected-access,ungrouped-imports,too-many-branches
# pylint: disable=redefined-outer-name,inherit-non-class

interface_implementedBy = interface.implementedBy
IPersistent_providedBy = IPersistent.providedBy
component_queryAdapter = component.queryAdapter
component_queryUtility = component.queryUtility

logger = __import__('logging').getLogger(__name__)

_EMPTY_DICT = {}

#: .. deprecated:: 1.0
#: This is legacy functionality, please do not access directly.
#: The public interface is through :func:`register_legacy_search_module`
LEGACY_FACTORY_SEARCH_MODULES = set()

try:
    from zope.testing.cleanup import addCleanUp
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


## Implementation of legacy search modules.

# We go through the global component registry, using a local
# interface. We treat the registry as a cache and we will only
# look at any given module object one time. We can detect duplicates
# in this fashion. (For cython compilation, this lives in interfaces.)
from nti.externalization.interfaces import _ILegacySearchModuleFactory # pylint:disable=wrong-import-position

def __register_legacy_if_not(gsm, name, factory):
    registered = gsm.queryUtility(_ILegacySearchModuleFactory, name)
    if registered is not None:
        logger.info("Found duplicate registration for legacy search path."
                    "Factory %r will be used for class name %r overriding %r",
                    registered, name, factory)
        return

    gsm.registerUtility(factory, name=name, provided=_ILegacySearchModuleFactory)

def _find_factories_in_module(module,
                              case_sensitive=False):
    mod_name = module.__name__
    # If we're dealing with a namespace object, such as what
    # AutoPackaegIO produces, it may represent types from many modules
    # on purpose. OTOH, if we get here via a string that was supposed
    # to be a module, then we need to respect that and ignore imports.
    # This is complicated by the fact that zope.deprecation puts DeprecationProxy
    # objects into sys.modules, but they appear to handle that correctly
    any_module = not isinstance(module, types.ModuleType)
    for name, value in sorted(vars(module).items()):
        if (callable(value)
                and getattr(value, '__external_can_create__', False)
                and (any_module or getattr(value, '__module__', _EMPTY_DICT) == mod_name)):
            yield name, value
            if not case_sensitive and name.lower() != name:
                yield name.lower(), value

def _register_factories_from_module(module):
    gsm = component.getGlobalSiteManager()

    for name, value in _find_factories_in_module(module):
        __register_legacy_if_not(gsm, name, value)

def _register_factories_from_search_set():
    search_modules = set(LEGACY_FACTORY_SEARCH_MODULES)
    LEGACY_FACTORY_SEARCH_MODULES.clear()

    # Make sure we have objects, not strs.
    modules = []
    for module in search_modules:
        if not hasattr(module, '__dict__'):
            # Let this throw ImportError, it's a programming bug
            name = module
            module = resolve(name)
        modules.append(module)

    # Sort them as best we can.
    modules.sort(key=lambda s: getattr(s, '__name__', ''))
    for module in modules:
        _register_factories_from_module(module)


_ext_factory_warnings = set()

def _search_for_external_factory(typeName):
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
        _register_factories_from_search_set()


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
        logger.debug("Deprecated: Using legacy class finder for %r", typeName)
        if len(_ext_factory_warnings) > 1024:
            _ext_factory_warnings.clear() # pragma: no cover

    return factory

def _find_factory_for_mime_or_class(externalized_object):
    # We use specialized interfaces instead of plain IFactory to make it clear
    # that these are being created from external data

    try:
        mime_type = externalized_object[StandardExternalFields.MIMETYPE]
    except TypeError:
        # Not subscriptable. We won't be able to work for
        # this object
        return None
    except KeyError:
        # sad trombone. Not present.
        pass
    else:
        if mime_type:
            factory = component_queryAdapter(externalized_object,
                                             IMimeObjectFactory,
                                             mime_type)
            if factory is not None:
                return factory

            # What about a named utility?
            factory = component_queryUtility(IMimeObjectFactory,
                                             mime_type)

            if factory is not None:
                return factory

            # Is there a default?
            factory = component_queryAdapter(externalized_object,
                                             IMimeObjectFactory)

            if factory is not None:
                return factory

    # Fallback to class
    try:
        class_name = externalized_object[StandardExternalFields.CLASS]
    except KeyError:
        # very sad trombone
        return None

    if class_name:
        factory = component_queryAdapter(externalized_object,
                                         IClassObjectFactory,
                                         class_name)
        if factory is not None:
            return factory

        return find_factory_for_class_name(class_name)


class _DefaultExternalizedObjectFactoryFinder(object):
    # This is an IFactory, declared below.
    # (Cython cdef classes cannot have decorators)
    __slots__ = ()

    def find_factory(self, externalized_object):
        return _find_factory_for_mime_or_class(externalized_object)

    # We are callable for BWC and because that's what an IFactory is
    def __call__(self, externalized_object):
        return _find_factory_for_mime_or_class(externalized_object)

interface.classImplements(_DefaultExternalizedObjectFactoryFinder,
                          IFactory)

default_externalized_object_factory_finder = _DefaultExternalizedObjectFactoryFinder()


@interface.implementer(IExternalizedObjectFactoryFinder)
def default_externalized_object_factory_finder_factory(unused_externalized_object):
    return default_externalized_object_factory_finder


def find_factory_for_class_name(class_name):
    factory = component_queryUtility(IClassObjectFactory, class_name)
    if factory is None:
        factory = _search_for_external_factory(class_name)
    # Did we chop off an extra 's'?
    if factory is None and class_name and class_name.endswith('s'):
        factory = _search_for_external_factory(class_name + 's')
    return factory


def find_factory_for(externalized_object, registry=component):
    """
    Given a :class:`IExternalizedObject`, locate and return a factory
    to produce a Python object to hold its contents.
    """
    factory_finder = registry.queryAdapter(
        externalized_object,
        IExternalizedObjectFactoryFinder)
    if factory_finder is not None:
        return factory_finder.find_factory(externalized_object)


    return _find_factory_for_mime_or_class(externalized_object)


def _resolve_externals(object_io, updating_object, externalObject,
                       registry=component, context=None):
    # Run the resolution steps on the external object
    # TODO: Document this.

    for keyPath in getattr(object_io, '__external_oids__', ()):
        # TODO: This version is very simple, generalize it
        # TODO: This check seems weird. Why do we do it this way
        # instead of getting the object and seeing if it's false?
        if keyPath not in externalObject:
            continue
        externalObjectOid = externalObject[keyPath]
        unwrap = False
        if not isinstance(externalObjectOid, collections.MutableSequence):
            externalObjectOid = [externalObjectOid, ]
            unwrap = True

        for i in range(0, len(externalObjectOid)): # pylint:disable=consider-using-enumerate
            resolver = registry.queryMultiAdapter((updating_object, externalObjectOid[i]),
                                                  IExternalReferenceResolver)
            if resolver:
                externalObjectOid[i] = resolver.resolve(externalObjectOid[i])
        if unwrap and keyPath in externalObject:  # Only put it in if it was there to start with
            externalObject[keyPath] = externalObjectOid[0]

    for ext_key, resolver_func in getattr(object_io, '__external_resolvers__', {}).items():
        extValue = externalObject.get(ext_key)
        if not extValue:
            continue
        # classmethods and static methods are implemented with descriptors,
        # which don't work when accessed through the dictionary in this way,
        # so we special case it so instances don't have to.
        if isinstance(resolver_func, (classmethod, staticmethod)):
            resolver_func = resolver_func.__get__(None, object_io.__class__)

        try:
            extValue = resolver_func(context, externalObject, extValue)
        except TypeError:
            # instance function?
            # Note that the try/catch is still faster than
            # what we were doing to detect instance functions, which was to use
            # len(inspect.getargspec(func)[0]) == 4 by about 4,000X !
            extValue = resolver_func(object_io, context, externalObject, extValue)

        externalObject[ext_key] = extValue



# Things we don't bother trying to internalize
_primitives = string_types + (numbers.Number, bool)

class _RecallArgs(object):
    __slots__ = (
        'registry',
        'context',
        'require_updater',
        'notify',
        'pre_hook',
    )

    def __init__(self, registry,
                 context,
                 require_updater,
                 notify,
                 pre_hook):
        self.registry = registry
        self.context = context
        self.require_updater = require_updater
        self.notify = notify
        self.pre_hook = pre_hook


def _recall(k, obj, ext_obj, kwargs):
    # We must manually pass all the args to get the optimized
    # cython call
    obj = update_from_external_object(obj, ext_obj,
                                      registry=kwargs.registry,
                                      context=kwargs.context,
                                      require_updater=kwargs.require_updater,
                                      notify=kwargs.notify,
                                      pre_hook=kwargs.pre_hook)
    if IPersistent_providedBy(obj): # pragma: no cover
        obj._v_updated_from_external_source = ext_obj
    return obj


def _notifyModified(containedObject, externalObject, updater=None, external_keys=None,
                    eventFactory=ObjectModifiedFromExternalEvent, kwargs=None):
    # try to provide external keys
    if kwargs is None:
        kwargs = {}
    if external_keys is None or not external_keys:
        external_keys = [k for k in externalObject.keys()]

    # TODO: We need to try to find the actual interfaces and fields to allow correct
    # decisions to be made at higher levels.
    # zope.formlib.form.applyData does this because it has a specific, configured mapping. We
    # just do the best we can by looking at what's implemented. The most specific
    # interface wins
    # map from interface class to list of keys
    descriptions = {}
    provides = interface.providedBy(containedObject)
    get_iface = provides.get
    for k in external_keys:
        iface_providing_attr = None
        iface_attr = get_iface(k)
        if iface_attr is not None:
            iface_providing_attr = iface_attr.interface

        descriptions.setdefault(iface_providing_attr, []).append(k)
    attributes = [Attributes(iface, *sorted(keys))
                  for iface, keys in descriptions.items()]
    event = eventFactory(containedObject, *attributes, **kwargs)
    event.external_value = externalObject
    # Let the updater have its shot at modifying the event, too, adding
    # interfaces or attributes. (Note: this was added to be able to provide
    # sharedWith information on the event, since that makes for a better stream.
    # If that use case expands, revisit this interface.
    # XXX: Document and test this.
    try:
        meth = updater._ext_adjust_modified_event
    except AttributeError:
        pass
    else:
        event = meth(event) # pragma: no cover
    _zope_event_notify(event)
    return event

def notifyModified(containedObject, externalObject, updater=None, external_keys=(),
                   eventFactory=ObjectModifiedFromExternalEvent, **kwargs):
    return _notifyModified(containedObject, externalObject, updater, external_keys,
                           eventFactory, kwargs)

notify_modified = notifyModified


def update_from_external_object(containedObject, externalObject,
                                registry=component, context=None,
                                require_updater=False,
                                notify=True,
                                pre_hook=None):
    """
    Central method for updating objects from external values.

    :param containedObject: The object to update.
    :param externalObject: The object (typically a mapping or sequence) to update
        the object from. Usually this is obtained by parsing an external
        format like JSON.
    :param context: An object passed to the update methods.
    :param require_updater: If True (not the default) an exception
        will be raised if no implementation of
        :class:`~nti.externalization.interfaces.IInternalObjectUpdater`
        can be found for the `containedObject.`
    :keyword bool notify: If ``True`` (the default), then if the updater
        for the `containedObject` either has no preference (returns
        None) or indicates that the object has changed, then an
        :class:`~nti.externalization.interfaces.IObjectModifiedFromExternalEvent`
        will be fired. This may be a recursive process so a top-level
        call to this object may spawn multiple events. The events that
        are fired will have a ``descriptions`` list containing one or
        more :class:`~zope.lifecycleevent.interfaces.IAttributes` each
        with ``attributes`` for each attribute we modify (assuming
        that the keys in the ``externalObject`` map one-to-one to an
        attribute; if this is the case and we can also find an
        interface declaring the attribute, then the ``IAttributes``
        will have the right value for ``interface`` as well).
    :keyword callable pre_hook: If given, called with the before
        update_from_external_object is called for every nested object.
        Signature ``f(k,x)`` where ``k`` is either the key name, or
        None in the case of a sequence and ``x`` is the external
        object. Deprecated.
    :return: `containedObject` after updates from `externalObject`

    .. versionchanged:: 1.0.0a2
       Remove the ``object_hook`` parameter.
    """

    if pre_hook is not None:
        for i in range(3):
            warnings.warn('pre_hook is deprecated', FutureWarning, stacklevel=i)

    kwargs = _RecallArgs(
        registry,
        context,
        require_updater,
        notify,
        pre_hook
    )


    # Parse any contained objects
    # TODO: We're (deliberately?) not actually updating any contained
    # objects, we're replacing them. Is that right? We could check OIDs...
    # If we decide that's right, then the internals could be simplified by
    # splitting the two parts
    # TODO: Schema validation
    # TODO: Should the current user impact on this process?

    # Sequences do not represent python types, they represent collections of
    # python types
    if isinstance(externalObject, collections.MutableSequence):
        tmp = []
        for value in externalObject:
            if pre_hook is not None:
                pre_hook(None, value)
            factory = find_factory_for(value, registry=registry)
            tmp.append(_recall(None, factory(), value, kwargs) if factory is not None else value)
        # XXX: TODO: Should we be assigning this to the slice of externalObject?
        # in-place?
        return tmp

    assert isinstance(externalObject, collections.MutableMapping)

    # We have to save the list of keys, it's common that they get popped during the update
    # process, and then we have no descriptions to send
    external_keys = list()
    for k, v in iteritems(externalObject):
        external_keys.append(k)
        if isinstance(v, _primitives):
            continue

        if pre_hook is not None:
            pre_hook(k, v)

        if isinstance(v, collections.MutableSequence):
            # Update the sequence in-place
            # XXX: This is not actually updating it.
            # We need to slice externalObject[k[:]]
            __traceback_info__ = k, v
            v = _recall(k, (), v, kwargs)
            externalObject[k] = v
        else:
            factory = find_factory_for(v, registry=registry)
            if factory is not None:
                externalObject[k] = _recall(k, factory(), v, kwargs)

    updater = None
    if hasattr(containedObject, 'updateFromExternalObject') \
        and not getattr(containedObject, '__ext_ignore_updateFromExternalObject__', False):
        # legacy support. The __ext_ignore_updateFromExternalObject__
        # allows a transition to an adapter without changing
        # existing callers and without triggering infinite recursion
        updater = containedObject
    else:
        if require_updater:
            get = registry.getAdapter
        else:
            get = registry.queryAdapter

        updater = get(containedObject, IInternalObjectUpdater)

    if updater is not None:
        # Let the updater resolve externals too
        _resolve_externals(updater, containedObject, externalObject,
                           registry=registry, context=context)

        updated = None
        # The signature may vary.
        # XXX: This is slow and cumbersome and needs to go.
        # See https://github.com/NextThought/nti.externalization/issues/30
        try:
            argspec = inspect.getargspec(updater.updateFromExternalObject)
        except TypeError: # pragma: no cover (This is hard to catch in pure-python coverage mode)
            # Cython functions and other extension types are "not a Python function"
            # and don't work with this. We assume they use the standard form accepting
            # 'context' as kwarg
            updated = updater.updateFromExternalObject(externalObject, context=context)
        else:
            if 'context' in argspec.args or (argspec.keywords and 'dataserver' not in argspec.args):
                updated = updater.updateFromExternalObject(externalObject,
                                                           context=context)
            elif argspec.keywords or 'dataserver' in argspec.args:
                updated = updater.updateFromExternalObject(externalObject,
                                                           dataserver=context)
            else:
                updated = updater.updateFromExternalObject(externalObject)

        # Broadcast a modified event if the object seems to have changed.
        if notify and (updated is None or updated):
            _notifyModified(containedObject, externalObject,
                            updater, external_keys)

    return containedObject

def _noop():
    pass


class _FirstSet(object):

    __slots__ = (
        'ext_self',
        'field_name',
        'value',
    )

    def __init__(self, ext_self, field_name, value):
        self.ext_self = ext_self
        self.field_name = field_name
        self.value = value

    def __call__(self):
        setattr(self.ext_self, self.field_name, self.value)

class _FieldSet(object):

    __slots__ = (
        'ext_self',
        'field',
        'value'
    )

    def __init__(self, ext_self, field, value):
        self.ext_self = ext_self
        self.field = field
        self.value = value

    def __call__(self):
        self.field.set(self.ext_self, self.value)


def validate_field_value(self, field_name, field, value):
    """
    Given a :class:`zope.schema.interfaces.IField` object from a schema
    implemented by `self`, validates that the proposed value can be
    set. If the value needs to be adapted to the schema type for validation to work,
    this method will attempt that.

    :param string field_name: The name of the field we are setting. This
            implementation currently only uses this for informative purposes.
    :param field: The schema field to use to validate (and set) the value.
    :type field: :class:`zope.schema.interfaces.IField`

    :raises zope.interface.Invalid: If the field cannot be validated,
            along with a good reason (typically better than simply provided by the field itself)
    :return: A callable of no arguments to call to actually set the value (necessary
            in case the value had to be adapted).
    """
    __traceback_info__ = field_name, value
    field = field.bind(self)
    try:
        if isinstance(value, text_type) and IFromUnicode.providedBy(field):
            value = field.fromUnicode(value)  # implies validation
        else:
            field.validate(value)
    except SchemaNotProvided as e:
        # The object doesn't implement the required interface.
        # Can we adapt the provided object to the desired interface?
        # First, capture the details so we can reraise if needed
        exc_info = sys.exc_info()
        if not e.args:  # zope.schema doesn't fill in the details, which sucks
            e.args = (field_name, field.schema)

        try:
            value = field.schema(value)
            field.validate(value)
        except (LookupError, TypeError, ValidationError, AttributeError):
            # Nope. TypeError (or AttrError - Variant) means we couldn't adapt,
            # and a validation error means we could adapt, but it still wasn't
            # right. Raise the original SchemaValidationError.
            reraise(*exc_info)
        finally:
            del exc_info
    except WrongType as e:
        # Like SchemaNotProvided, but for a primitive type,
        # most commonly a date
        # Can we adapt?
        if len(e.args) != 3: # pragma: no cover
            raise
        exc_info = sys.exc_info()
        exp_type = e.args[1]
        # If the type unambiguously implements an interface (one interface)
        # that's our target. IDate does this
        if len(list(interface_implementedBy(exp_type))) != 1:
            try:
                raise # pylint:disable=misplaced-bare-raise
            finally:
                del exc_info
        schema = list(interface_implementedBy(exp_type))[0]
        try:
            value = schema(value)
        except (LookupError, TypeError):
            # No registered adapter, darn
            raise reraise(*exc_info)
        except ValidationError as e:
            # Found an adapter, but it does its own validation,
            # and that validation failed (eg, IDate below)
            # This is still a more useful error than WrongType,
            # so go with it after ensuring it has a field
            e.field = field
            raise
        finally:
            del exc_info

        # Lets try again with the adapted value
        return validate_field_value(self, field_name, field, value)

    except WrongContainedType as e:
        # We failed to set a sequence. This would be of simple (non externalized)
        # types.
        # Try to adapt each value to what the sequence wants, just as above,
        # if the error is one that may be solved via simple adaptation
        # TODO: This is also thrown from IObject fields when validating the
        # fields of the object
        if not e.args or not all([isinstance(x, SchemaNotProvided) for x in e.args[0]]):
            raise # pragma: no cover
        exc_info = sys.exc_info()
        # IObject provides `schema`, which is an interface, so we can adapt
        # using it. Some other things do not, for example nti.schema.field.Variant
        # They might provide a `fromObject` function to do the conversion
        # The field may be able to handle the whole thing by itself or we may need
        # to do the individual objects

        converter = identity
        loop = True
        if hasattr(field, 'fromObject'):
            converter = field.fromObject
            loop = False
        elif hasattr(field.value_type, 'fromObject'):
            converter = field.value_type.fromObject
        elif hasattr(field.value_type, 'schema'):
            converter = field.value_type.schema
        try:
            value = [converter(v) for v in value] if loop else converter(value)
        except TypeError:
            # TypeError means we couldn't adapt, in which case we want
            # to raise the original error. If we could adapt,
            # but the converter does its own validation (e.g., fromObject)
            # then we want to let that validation error rise
            try:
                raise reraise(*exc_info)
            finally:
                del exc_info


        # Now try to set the converted value
        try:
            field.validate(value)
        except ValidationError:
            # Nope. TypeError means we couldn't adapt, and a
            # validation error means we could adapt, but it still wasn't
            # right. Raise the original SchemaValidationError.
            raise reraise(*exc_info)
        finally:
            del exc_info
    if (field.readonly
            and field.query(self) is None
            and field.queryTaggedValue('_ext_allow_initial_set')):
        if value is not None:
            # First time through we get to set it, but we must bypass
            # the field
            _do_set = _FirstSet(self, str(field_name), value)
        else:
            _do_set = _noop
    else:
        _do_set = _FieldSet(self, field, value)

    return _do_set





def validate_named_field_value(self, iface, field_name, value):
    """
    Given a :class:`zope.interface.Interface` and the name of one of its attributes,
    validate that the given ``value`` is appropriate to set. See :func:`validate_field_value`
    for details.

    :param string field_name: The name of a field contained in
        `iface`. May name a regular :class:`zope.interface.Attribute`,
        or a :class:`zope.schema.interfaces.IField`; if the latter,
        extra validation will be possible.

    :return: A callable of no arguments to call to actually set the value.
    """
    field = iface[field_name]
    if IField.providedBy(field):
        return validate_field_value(self, field_name, field, value)

    return _FirstSet(self, field_name, value)


from nti.externalization._compat import import_c_accel # pylint:disable=wrong-import-position,wrong-import-order
import_c_accel(globals(), 'nti.externalization._internalization')
