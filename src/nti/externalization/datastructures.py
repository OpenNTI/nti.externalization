# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
# -*- coding: utf-8 -*
"""
Datastructures to help externalization.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# There are a *lot* of fixme (XXX and the like) in this file.
# Turn those off in general so we can see through the noise.
# pylint:disable=fixme
# pylint:disable=keyword-arg-before-vararg

# stdlib imports
import numbers


import six
from six import iteritems
from zope import interface
from zope import schema
from zope.schema.interfaces import SchemaNotProvided
from zope.schema.interfaces import IDict
from zope.schema.interfaces import IObject

from nti.schema.interfaces import find_most_derived_interface

from .interfaces import IInternalObjectIO
from .interfaces import IInternalObjectIOFinder
from .interfaces import IAnonymousObjectFactory
from .interfaces import StandardInternalFields

# Things imported from cython with matching cimport
from .externalization.dictionary import to_minimal_standard_external_dictionary
from .externalization.dictionary import internal_to_standard_external_dictionary
# Must rename this so it doesn't conflict with method defs;
# that breaks cython
from .externalization.externalizer import to_external_object as _toExternalObject

from .internalization import validate_named_field_value
from .internalization.factories import find_factory_for
from .representation import make_repr
from .factory import AnonymousObjectFactory

from ._base_interfaces import get_standard_external_fields
from ._base_interfaces import get_standard_internal_fields
from ._base_interfaces import NotGiven

from ._interface_cache import cache_for

StandardExternalFields = get_standard_external_fields()
StandardInternalFields = get_standard_internal_fields()
IDict_providedBy = IDict.providedBy
IObject_providedBy = IObject.providedBy

__all__ = [
    'ExternalizableDictionaryMixin',
    'AbstractDynamicObjectIO',
    'ExternalizableInstanceDict',
    'InterfaceObjectIO',
    'ModuleScopedInterfaceObjectIO',
]

class ExternalizableDictionaryMixin(object):
    """
    Implements a toExternalDictionary method as a base for subclasses.
    """

    #: If true, then when asked for the standard dictionary, we will instead
    #: produce the *minimal* dictionary. See :func:`~to_minimal_standard_external_dictionary`
    __external_use_minimal_base__ = False

    def _ext_replacement(self):
        """
        Return the object that we are externalizing.

        This class returns ``self``, but subclasses will typically override this.
        """
        return self

    def _ext_standard_external_dictionary(self, replacement, mergeFrom=None, **kwargs):
        if self.__external_use_minimal_base__:
            return to_minimal_standard_external_dictionary(replacement,
                                                           mergeFrom=mergeFrom)

        return internal_to_standard_external_dictionary(
            replacement,
            mergeFrom=mergeFrom,
            decorate=kwargs.get('decorate', True),
            request=kwargs.get('request', NotGiven),
            decorate_callback=kwargs.get('decorate_callback', NotGiven))

    def toExternalDictionary(self, mergeFrom=None, *unused_args, **kwargs):
        """
        Produce the standard external dictionary for this object.

        Uses `_ext_replacement`.
        """
        return self._ext_standard_external_dictionary(self._ext_replacement(),
                                                      mergeFrom=mergeFrom,
                                                      **kwargs)


class AbstractDynamicObjectIO(ExternalizableDictionaryMixin):
    """
    Base class for objects that externalize based on dynamic information.

    Abstractions are in place to allow subclasses to map external and internal names
    independently (this type never uses getattr/setattr/hasattr, except for some
    standard fields).

    See `InterfaceObjectIO` for a complete implementation.
    """

    # TODO: there should be some better way to customize this if desired (an explicit list)
    # TODO: Play well with __slots__
    # TODO: This won't evolve well. Need something more sophisticated,
    # probably a meta class.

    # Avoid things super handles
    # These all *should* be frozenset() and immutable
    _excluded_out_ivars_ = frozenset({
        StandardInternalFields.ID,
        StandardExternalFields.ID,
        StandardInternalFields.CREATOR,
        StandardExternalFields.CREATOR,
        StandardInternalFields.CONTAINER_ID,
        'lastModified',
        StandardInternalFields.LAST_MODIFIEDU,
        StandardInternalFields.CREATED_TIME,
        'links'
    })
    _excluded_in_ivars_ = frozenset({
        StandardInternalFields.ID,
        StandardExternalFields.ID,
        StandardExternalFields.OID,
        StandardInternalFields.CREATOR,
        StandardExternalFields.CREATOR,
        StandardInternalFields.LAST_MODIFIED,
        StandardInternalFields.LAST_MODIFIEDU,
        # Also the IDCTimes created/modified values
        'created', 'modified',
        StandardExternalFields.CLASS,
        StandardInternalFields.CONTAINER_ID
    })
    _ext_primitive_out_ivars_ = frozenset()
    _prefer_oid_ = False

    def find_factory_for_named_value(self, key, value, registry):
        """
        Uses `.find_factory_for` to locate a factory.

        This does not take into account the current object (context)
        or the *key*. It only handles finding factories based on the
        class or MIME type found within *value*.
        """
        return find_factory_for(value, registry)

    def _ext_replacement(self):
        # Redeclare this here for cython
        return self

    def _ext_all_possible_keys(self):
        """
        This method must return a frozenset of native strings.
        """
        raise NotImplementedError()

    def _ext_setattr(self, ext_self, k, value):
        raise NotImplementedError()

    def _ext_getattr(self, ext_self, k, default=NotGiven):
        """
        _ext_getattr(object, name[, default]) -> value

        Return the attribute of the *ext_self* object with the internal name *name*.
        If the attribute does not exist, should raise (typically :exc:`AttributeError`),
        unless *default* is given, in which case it returns that.

        .. versionchanged:: 1.0a4
            Add the *default* argument.
        """
        raise NotImplementedError()

    def _ext_replacement_getattr(self, name, default=NotGiven):
        """
        Like `_ext_getattr`, but automatically fills in `_ext_replacement`
        for the *ext_self* argument.

        .. versionadded:: 1.0a4
        """
        return self._ext_getattr(self._ext_replacement(), name, default)

    def _ext_keys(self):
        """
        Return only the names of attributes that should be externalized.
        These values will be used as keys in the external dictionary.

        See :meth:`_ext_all_possible_keys`. This implementation then filters out
        *private* attributes (those beginning with an underscore),
        and those listed in ``_excluded_in_ivars_``.

        This method must return a set of native strings.
        """
        # Sadly, we cannot yet enforce what type _excluded_out_ivars_ is.
        # Mostly it is a set or frozen set (depending on how it was
        # combined with the declaration in this class) but some overrides
        # in the wild have it as a tuple. We need a metaclass to fix that.
        excluded = self._excluded_out_ivars_
        return [k for k in self._ext_all_possible_keys()
                if (k not in excluded  # specifically excluded
                    and not k.startswith('_'))]  # private
        # and not callable(getattr(ext_self,k)))]    # avoid functions

    def _ext_primitive_keys(self):
        """
        Return a container of string keys whose values are known to be primitive.
        This is an optimization for writing.

        This method must return a frozenset.
        """
        return self._ext_primitive_out_ivars_

    def toExternalDictionary(self, mergeFrom=None, *unused_args, **kwargs):
        result = super(AbstractDynamicObjectIO, self).toExternalDictionary(mergeFrom=mergeFrom,
                                                                           **kwargs)
        ext_self = self._ext_replacement()
        primitive_ext_keys = self._ext_primitive_keys()
        for k in self._ext_keys():
            if k in result:
                # Standard key already added
                continue

            ext_val = attr_val = self._ext_getattr(ext_self, k)
            __traceback_info__ = k, attr_val
            if k not in primitive_ext_keys:
                ext_val = _toExternalObject(attr_val, **kwargs)

            result[k] = ext_val

            if ext_val is not attr_val:
                # We want to be sure things we externalize have the
                # right parent relationship but if we are directly
                # externalizing an existing object (e.g., primitive or
                # something that uses a replacement) we don't want to
                # change the relationship or even set one in the first
                # place---if the object gets pickled later on, that
                # could really screw things up (One symptom is
                # InvalidObjectReference from ZODB across
                # transactions/tests) if ILocation.providedBy(
                # result[k] ): (throwing is faster than providedBy)
                try:
                    ext_val.__parent__ = ext_self
                except AttributeError:
                    # toExternalObject is schizophrenic about when it converts
                    # return values to LocatedExternalDict/List. Sometimes it
                    # does, sometimes it does not.
                    pass

        if (StandardExternalFields.ID in result
                and StandardExternalFields.OID in result
                and self._prefer_oid_
                and result[StandardExternalFields.ID] != result[StandardExternalFields.OID]):
            result[StandardExternalFields.ID] = result[StandardExternalFields.OID]
        return result

    def toExternalObject(self, mergeFrom=None, *args, **kwargs):
        return self.toExternalDictionary(mergeFrom, *args, **kwargs)

    def _ext_accept_update_key(self, k, ext_self, ext_keys):
        """
        Returns whether or not this key should be accepted for setting
        on the object, or silently ignored.

        :param ext_keys: As an optimization, the value of :meth:`_ext_all_possible_keys`
            is passed. Keys are only accepted if they are in this list.
        """
        __traceback_info__ = k, ext_self, ext_keys

        return k not in self._excluded_in_ivars_ and k in ext_keys

    def _ext_accept_external_id(self, ext_self, parsed):
        """
        If the object we're updating does not have an ``id`` set, but there is an
        ``ID`` in the external object, should we be able to use it?

        :return: boolean
        """
        __traceback_info__ = ext_self, parsed
        return False  # false by default

    def updateFromExternalObject(self, parsed, *unused_args, **unused_kwargs):
        return self._updateFromExternalObject(parsed)

    def _updateFromExternalObject(self, parsed):
        updated = False

        ext_self = self._ext_replacement()
        ext_keys = self._ext_all_possible_keys()
        for k, v in iteritems(parsed):
            if not self._ext_accept_update_key(k, ext_self, ext_keys):
                continue
            __traceback_info__ = (k, v)
            self._ext_setattr(ext_self, k, v)
            updated = True

        # TODO: Should these go through _ext_setattr?
        if (StandardExternalFields.CONTAINER_ID in parsed
                and getattr(ext_self, StandardInternalFields.CONTAINER_ID, parsed) is None):
            setattr(ext_self,
                    StandardInternalFields.CONTAINER_ID,
                    parsed[StandardExternalFields.CONTAINER_ID])
        if (StandardExternalFields.CREATOR in parsed
                and getattr(ext_self, StandardInternalFields.CREATOR, parsed) is None):
            setattr(ext_self,
                    StandardInternalFields.CREATOR,
                    parsed[StandardExternalFields.CREATOR])
        if (StandardExternalFields.ID in parsed
                and getattr(ext_self, StandardInternalFields.ID, parsed) is None
                and self._ext_accept_external_id(ext_self, parsed)):
            setattr(ext_self,
                    StandardInternalFields.ID,
                    parsed[StandardExternalFields.ID])

        return updated

interface.classImplements(AbstractDynamicObjectIO, IInternalObjectIOFinder)


class _ExternalizableInstanceDict(AbstractDynamicObjectIO):

    # TODO: there should be some better way to customize this if desired (an explicit list)
    # TODO: Play well with __slots__? ZODB supports slots, but doesn't recommend them
    # TODO: This won't evolve well. Need something more sophisticated,
    # probably a meta class.
    _update_accepts_type_attrs = False

    def __init__(self, context):
        self.context = context
        for name in (
                '_update_accepts_type_attrs',
                '__external_use_minimal_base__',
                '_excluded_in_ivars_',
                '_excluded_out_ivars_',
                '_ext_primitive_out_ivars_',
                '_prefer_oid_'
        ):
            try:
                v = getattr(context, name)
            except AttributeError:
                continue
            else:
                setattr(self, name, v)

    def _ext_replacement(self):
        return self.context

    def _ext_all_possible_keys(self):
        return frozenset(self._ext_replacement().__dict__.keys())

    def _ext_getattr(self, ext_self, k, default=NotGiven):
        if default is NotGiven:
            return getattr(ext_self, k)
        return getattr(ext_self, k, default)

    def _ext_setattr(self, ext_self, k, value):
        setattr(ext_self, k, value)

    def _ext_accept_update_key(self, k, ext_self, ext_keys):
        return (
            super(_ExternalizableInstanceDict, self)._ext_accept_update_key(k, ext_self, ext_keys)
            or (self._update_accepts_type_attrs and hasattr(ext_self, k))
        )


class ExternalizableInstanceDict(object):
    """
    Externalizes to a dictionary containing the members of
    ``__dict__`` that do not start with an underscore.

    Meant to be used as a super class; also can be used as an external
    object superclass.

    Consider carefully before using this class. Generally, an interface
    and `InterfaceObjectIO` are better.

    .. versionchanged:: 1.0a5
       No longer extends `AbstractDynamicObjectIO`, just delegates to it.
       Most of the `_ext_`` prefixed methods can no longer be overridden.
    """
    # This class is sometimes subclassed while also subclassing persistent.Persistent,
    # which doesn't work if it's an extension class with an incompatible layout,
    # as AbstractDynamicObjectIO is, so we can't subclass that. It's rarely used,
    # so performance doesn't matter as much.

    # pylint:disable=protected-access
    _update_accepts_type_attrs = _ExternalizableInstanceDict._update_accepts_type_attrs
    __external_use_minimal_base__ = _ExternalizableInstanceDict.__external_use_minimal_base__
    _excluded_out_ivars_ = AbstractDynamicObjectIO._excluded_out_ivars_
    _excluded_in_ivars_ = AbstractDynamicObjectIO._excluded_in_ivars_
    _ext_primitive_out_ivars_ = AbstractDynamicObjectIO._ext_primitive_out_ivars_
    _prefer_oid_ = AbstractDynamicObjectIO._prefer_oid_

    def _ext_replacement(self):
        "See `ExternalizableDictionaryMixin._ext_replacement`."
        return self

    def __make_io(self):
        return _ExternalizableInstanceDict(self._ext_replacement())

    def __getattr__(self, name):
        # here if we didn't have the attribute. Does our IO?
        return getattr(self.__make_io(), name)

    def updateFromExternalObject(self, parsed, *unused_args, **unused_kwargs):
        "See `~.IInternalObjectIO.updateFromExternalObject`"
        self.__make_io().updateFromExternalObject(parsed)

    def toExternalObject(self, mergeFrom=None, *args, **kwargs):
        "See `~.IInternalObjectIO.toExternalObject`. Calls `toExternalDictionary`."
        return self.toExternalDictionary(mergeFrom, *args, **kwargs)

    def toExternalDictionary(self, mergeFrom=None, *unused_args, **kwargs):
        "See `ExternalizableDictionaryMixin.toExternalDictionary`"
        return self.__make_io().toExternalDictionary(mergeFrom)

    __repr__ = make_repr()


interface.classImplements(ExternalizableInstanceDict, IInternalObjectIO)

_primitives = six.string_types + (numbers.Number, bool)

_anonymous_dict_factory = AnonymousObjectFactory(lambda x: x)
_anonymous_dict_factory.__external_factory_wants_arg__ = True

class InterfaceObjectIO(AbstractDynamicObjectIO):
    """
    Externalizes the *context* to a dictionary based on getting the
    attributes of an object defined by an interface. If any attribute
    has a true value for the tagged value ``_ext_excluded_out``, it
    will not be considered for reading or writing.

    This is an implementation of
    `~nti.externalization.interfaces.IInternalObjectIOFinder`, meaning
    it can both internalize (update existing objects) and externalize
    (producing dictionaries), and that it gets to choose the factories
    used for sub-objects when internalizing.

    This class is meant to be used as an adapter, so it accepts the
    object to externalize in the constructor, as well as the interface
    to use to guide the process. The object is externalized using the
    most-derived version of the interface given to the constructor
    that it implements.

    If the interface (or an ancestor) has a tagged value
    ``__external_class_name__``, it can either be the value to use for
    the ``Class`` key, or a callable
    ``__external_class_name__(interface, object ) -> name.``

    (TODO: In the future extend this to multiple, non-overlapping
    interfaces, and better interface detection (see
    :class:`ModuleScopedInterfaceObjectIO` for a limited version of
    this.)

    This class overrides `_ext_replacement` to return the *context*.
    """

    _ext_iface_upper_bound = None

    def __init__(self, context, iface_upper_bound=None, validate_after_update=True):
        """
        :param iface_upper_bound: The upper bound on the schema to use
            to externalize `ext_self`; we will use the most derived sub-interface
            of this interface that the object implements. Subclasses can either override this
            constructor to pass this parameter (while taking one argument themselves,
            to be usable as an adapter), or they can define the class
            attribute ``_ext_iface_upper_bound``
        :param bool validate_after_update: If ``True`` (the default) then the entire
            schema will be validated after an object has been updated with
            :meth:`update_from_external_object`, not just the keys that were assigned.
        """
        AbstractDynamicObjectIO.__init__(self)
        self._ext_self = context
        # Cache all of this data that we use. It's required often and, if not quite a bottleneck,
        # does show up in the profiling data
        cache = cache_for(self, context)
        if cache.iface is None:
            cache.iface = self._ext_find_schema(
                context,
                iface_upper_bound if iface_upper_bound is not None else self._ext_iface_upper_bound
            )
        self._iface = cache.iface

        if not cache.ext_primitive_out_ivars:
            keys = self._ext_find_primitive_keys()
            cache.ext_primitive_out_ivars = self._ext_primitive_out_ivars_ | keys
        self._ext_primitive_out_ivars_ = cache.ext_primitive_out_ivars

        self.validate_after_update = validate_after_update

    def __repr__(self):
        return '<%s.%s for %r at 0x%x>' % (
            type(self).__module__, type(self).__name__,
            self.schema,
            id(self)
        )

    @property
    def schema(self):
        """
        The schema we will use to guide the process
        """
        return self._iface

    def _ext_find_schema(self, ext_self, iface_upper_bound):
        return find_most_derived_interface(ext_self,
                                           iface_upper_bound,
                                           possibilities=self._ext_schemas_to_consider(ext_self))

    def _ext_find_primitive_keys(self):
        result = set()
        for n in self._ext_all_possible_keys():
            field = self._iface[n]
            field_type = getattr(field, '_type', None)
            if field_type is not None:
                if isinstance(field_type, tuple):
                    if all([issubclass(x, _primitives) for x in field_type]):
                        result.add(n)
                elif issubclass(field_type, _primitives):
                    result.add(n)

        return frozenset(result)

    def _ext_schemas_to_consider(self, ext_self):
        return interface.providedBy(ext_self)

    def _ext_replacement(self):
        return self._ext_self

    def _ext_all_possible_keys(self):
        cache = cache_for(self, self._ext_self)
        if cache.ext_all_possible_keys is None:
            iface = self._iface
            is_method = interface.interfaces.IMethod.providedBy
            cache.ext_all_possible_keys = frozenset([
                n for n in iface.names(all=True)
                if (not is_method(iface[n])
                    and not iface[n].queryTaggedValue('_ext_excluded_out', False))
            ])
        return cache.ext_all_possible_keys

    def _ext_getattr(self, ext_self, k, default=NotGiven):
        # TODO: Should this be directed through IField.get?
        if default is NotGiven:
            return getattr(ext_self, k)
        return getattr(ext_self, k, default)

    def _ext_setattr(self, ext_self, k, value):
        validate_named_field_value(ext_self, self._iface, k, value)()

    def _ext_accept_external_id(self, ext_self, parsed):
        """
        If the interface we're working from has a tagged value
        of ``__external_accept_id__`` on the ``id`` field, then
        this will return that value; otherwise, returns false.
        """
        __traceback_info__ = ext_self, parsed,
        cache = cache_for(self, ext_self)
        if cache.ext_accept_external_id is None:
            try:
                field = cache.iface['id']
                cache.ext_accept_external_id = field.getTaggedValue('__external_accept_id__')
            except KeyError:
                cache.ext_accept_external_id = False
        return cache.ext_accept_external_id

    def find_factory_for_named_value(self, key, value, registry):
        """
        If `AbstractDynamicObjectIO.find_factory_for_named_value`
        cannot find a factory based on examining *value*, then we use
        the context objects's schema to find a factory.

        If the schema contains an attribute named *key*, it will be
        queried for the tagged value ``__external_factory__``. If
        present, this tagged value should be the name of a factory
        object implementing `.IAnonymousObjectFactory` registered in
        *registry* (typically registered in the global site).

        The ZCML directive `.IAnonymousObjectFactoryDirective` sets up both the
        registration and the tagged value.

        This is useful for internalizing data from external sources
        that does not provide a class or MIME field within the data.

        The most obvious limitation of this is that if the *value* is part
        of a sequence, it must be a homogeneous sequence. The factory is
        called with no arguments, so the only way to deal with heterogeneous
        sequences is to subclass this object and override this method to
        examine the value itself.

        A second limitation is that the external data key must match
        the internal schema field name. Again, the only way to
        remove this limitation is to subclass this object.

        If no registered factory is found, and the schema field is
        a `zope.schema.Dict` with a value type of `zope.schema.Object`,
        then we return a factory which will update the object in place.

        .. versionchanged:: 1.0a6
           Only return an anonymous factory for ``IDict`` fields when
           it wants objects for the value.

        """
        factory = AbstractDynamicObjectIO.find_factory_for_named_value(self, key, value, registry)
        if factory is None:
            # Is there a factory on the field?
            try:
                field = self._iface[key]
                # See zcml.py:anonymousObjectFactoryDirective.
                # This *should* be a string giving the dottedname of a factory utility.
                # For test purposes we also allow it to be an actual object.

                # TODO: If this becomes a bottleneck, the ZCML could
                # have an argument global=False to allow setting the type
                # directly instead of a string; the user would have to
                # *know* that no sites would ever need a different value.
            except KeyError:
                pass
            else:
                factory = field.queryTaggedValue('__external_factory__')
                # When it is a string, we require the factory to exist.
                # Anything else is a programming error.
                if isinstance(factory, str):
                    factory = registry.getUtility(IAnonymousObjectFactory, factory)

                if (
                        factory is None
                        and IDict_providedBy(field)
                        and isinstance(value, dict)
                        and IObject_providedBy(field.value_type)
                ):
                    # If is no factory found, check to see if the
                    # schema field is a Dict with a complex value type, and if
                    # so, automatically update it in place. The alternative
                    # requires the user to use a ZCML directive for each such
                    # dict field.
                    factory = _anonymous_dict_factory
        return factory

    def updateFromExternalObject(self, parsed, *unused_args, **unused_kwargs):
        result = AbstractDynamicObjectIO._updateFromExternalObject(self, parsed)
        # If we make it this far, then validate the object.

        # TODO: Should probably just make sure that there are no /new/
        # validation errors added Best we can do right now is skip
        # this step if asked

        # TODO: Swizzle this method at runtime to be in this object's
        # dict, so we can elide the check.
        if self.validate_after_update:
            self._validate_after_update(self._iface, self._ext_self)
        return result

    def _validate_after_update(self, iface, ext_self):
        errors = schema.getValidationErrors(iface, ext_self)
        if errors:
            __traceback_info__ = errors
            try:
                raise errors[0][1]
            except SchemaNotProvided as e: # pragma: no cover
                # XXX: We shouldn't be able to get here;
                # ext_setattr should be doing this
                # This can probably be removed
                if not e.args:  # zope.schema doesn't fill in the details, which sucks
                    e.args = (errors[0][0],)
                raise

    def toExternalObject(self, mergeFrom=None, **kwargs):
        ext_class_name = None
        for iface in self._iface.__iro__:
            ext_class_name = iface.queryTaggedValue('__external_class_name__')
            if callable(ext_class_name):
                # Even though the tagged value may have come from a superclass,
                # give the actual class (interface) we're using
                ext_class_name = ext_class_name(self._iface,
                                                self._ext_replacement())
            if ext_class_name:
                break

        if ext_class_name:
            mergeFrom = mergeFrom if mergeFrom is not None else {}
            mergeFrom[StandardExternalFields.CLASS] = ext_class_name

        result = super(InterfaceObjectIO, self).toExternalObject(mergeFrom=mergeFrom, **kwargs)
        return result


class ModuleScopedInterfaceObjectIO(InterfaceObjectIO):
    """
    Only considers the interfaces provided within a given module
    (usually declared as a class attribute) when searching for the
    schema to use to externalize an object; the most derived version
    of interfaces within that module will be used. Subclasses must
    declare the class attribute ``_ext_search_module`` to be a module
    (something with the ``__name__``) attribute to locate interfaces
    in.

    Suitable for use when all the externalizable fields of interest
    are declared by an interface within a module, and an object does
    not implement two unrelated interfaces from the same module.

    .. note:: If the object does implement unrelated interfaces, but
            one (set) of them is a marker interface (featuring no schema
            fields or attributes), then it can be tagged with
            ``_ext_is_marker_interface`` and it will be excluded when
            determining the most derived interfaces. This can correct some
            cases that would otherwise raise a TypeError.
    """

    _ext_search_module = None

    def _ext_find_schema(self, ext_self, iface_upper_bound):
        # If the upper bound is given, then let the super class handle it all.
        # Presumably the user has given the correct branch to search.

        if iface_upper_bound is not None:
            return super(ModuleScopedInterfaceObjectIO, self)._ext_find_schema(
                ext_self, iface_upper_bound)

        most_derived = super(ModuleScopedInterfaceObjectIO, self)._ext_find_schema(
            ext_self, interface.Interface)

        # In theory, this is now the most derived interface.
        # If we have a graph that is not a tree, though, it may not be.
        # In that case, we are not suitable for use with this object
        for iface in self._ext_schemas_to_consider(ext_self):
            if iface is most_derived:
                # Support interfaces that have their __module__ changed
                # dynamically (e.g., test_benchmarks)
                continue
            if not most_derived.isOrExtends(iface):
                raise TypeError(
                    "Most derived interface %s does not extend %s; non-tree interface structure. "
                    "Searching module %s and considered %s on object %s of class %s and type %s"
                    % (most_derived, iface, self._ext_search_module,
                       list(self._ext_schemas_to_consider(ext_self)),
                       ext_self, ext_self.__class__,
                       type(ext_self)))

        return most_derived

    def _ext_schemas_to_consider(self, ext_self):
        search_module_name = self._ext_search_module.__name__
        return [x for x in interface.providedBy(ext_self)
                if x.__module__ == search_module_name
                and not x.queryTaggedValue('_ext_is_marker_interface')]

# pylint:disable=wrong-import-position,wrong-import-order
from nti.externalization._compat import import_c_accel
import_c_accel(globals(), 'nti.externalization._datastructures')
