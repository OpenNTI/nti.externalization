#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Externalization Interfaces

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope import interface
from zope.component.interfaces import IFactory
from zope.interface.common.mapping import IFullMapping
from zope.interface.common.sequence import ISequence
from zope.interface.interfaces import IObjectEvent
from zope.interface.interfaces import ObjectEvent
from zope.lifecycleevent import IObjectModifiedEvent
from zope.lifecycleevent import ObjectModifiedEvent
from zope.location import ILocation


# pylint:disable=inherit-non-class,no-method-argument,no-self-argument

from ._base_interfaces import LocatedExternalDict
from ._base_interfaces import get_standard_external_fields
from ._base_interfaces import get_standard_internal_fields
from ._base_interfaces import MINIMAL_SYNTHETIC_EXTERNAL_KEYS

StandardExternalFields = get_standard_external_fields()
StandardInternalFields = get_standard_internal_fields()

MINIMAL_SYNTHETIC_EXTERNAL_KEYS = MINIMAL_SYNTHETIC_EXTERNAL_KEYS

class IInternalObjectExternalizer(interface.Interface):
    """
    Implemented by, or adapted from, an object that can
    be externalized.
    """

    __external_can_create__ = interface.Attribute(
        """This must be set to true, generally at the class level, for objects
		that can be created by specifying their Class name.""")

    __external_class_name__ = interface.Attribute(
        """If present, the value is a string that is used for the 'Class' key in the
		external dictionary. If not present, the local name of the object's class is
		used instead.""")

    def toExternalObject(**kwargs):
        """
        Optional, see this :func:`~nti.externalization.externalization.to_external_object`.
        """
IExternalObject = IInternalObjectExternalizer  # b/c aliase


class INonExternalizableReplacement(interface.Interface):
    """
    This interface may be applied to objects that serve as a replacement
    for a non-externalized object.
    """


class INonExternalizableReplacementFactory(interface.Interface):
    """
    An factory object called to make a replacement when
    some object cannot be externalized.
    """

    def __call__(obj): # pylint:disable=signature-differs
        """
        :return: An externalized object to replace the given object. Possibly the
                given object itself if some higher level will handle it.
                The returned object *may* have the ``INonExternalizableReplacement``
                interface.
        """

INonExternalizableReplacer = INonExternalizableReplacementFactory


class IExternalObjectDecorator(interface.Interface):
    """
    Used as a subscription adapter (of the object or the object and
    request) to provide additional information to the externalization
    of an object after it has been externalized by the primary
    implementation of
    :class:`~nti.externalization.interfaces.IInternalObjectExternalizer`.
    Allows for a separation of concerns. These are called in no
    specific order, and so must operate by mutating the external
    object.

    These are called *after* :class:`.IExternalMappingDecorator`.
    """

    def decorateExternalObject(origial, external):
        """
        Decorate the externalized object (which is probably a mapping,
        though this is not guaranteed).

        :param original: The object that is being externalized.
            Passed to facilitate using non-classes as decorators.
        :param external: The externalization of that object, produced
            by an implementation of
            :class:`~nti.externalization.interfaces.IInternalObjectExternalizer`
            or default rules.
        :return: Undefined.
        """


class IExternalMappingDecorator(interface.Interface):
    """
    Used as a subscription adapter (of the object or the object and
    request) to provide additional information to the externalization
    of an object after it has been externalized by the primary
    implementation of
    :class:`~nti.externalization.interfaces.IInternalObjectExternalizer`.
    Allows for a separation of concerns. These are called in no
    specific order, and so must operate by mutating the external
    object.

    These are called *before* :class:`.IExternalObjectDecorator`.
    """

    def decorateExternalMapping(original, external):
        """
        Decorate the externalized object mapping.

        :param original: The object that is being externalized. Passed
            to facilitate using non-classes as decorators.
        :param external: The externalization of that object, an
            :class:`~nti.externalization.interfaces.ILocatedExternalMapping`,
            produced by an implementation of
            :class:`~nti.externalization.interfaces.IInternalObjectExternalizer` or default rules.
        :return: Undefined.
        """


class IExternalizedObject(interface.Interface):
    """
    An object that has already been externalized and needs no further
    transformation.
    """


class ILocatedExternalMapping(IExternalizedObject, ILocation, IFullMapping):
    """
    The externalization of an object as a dictionary, maintaining its location
    information.
    """


class ILocatedExternalSequence(IExternalizedObject, ILocation, ISequence):
    """
    The externalization of an object as a sequence, maintaining its location
    information.
    """


interface.classImplements(LocatedExternalDict, ILocatedExternalMapping)


@interface.implementer(ILocatedExternalSequence)
class LocatedExternalList(list):
    """
    A list that implements
    :class:`~nti.externalization.interfaces.ILocatedExternalSequence`.
    Returned by
    :func:`~nti.externalization.externalization.to_external_object`.

    This class is not :class:`.IContentTypeAware`, and it indicates so explicitly by declaring a
    `mimeType` value of None.
    """

    __name__ = u''
    __parent__ = None
    __acl__ = ()
    mimeType = None

# Representations as strings


class IExternalObjectRepresenter(interface.Interface):
    """
    Something that can represent an external object as a sequence of bytes.

    These will be registered as named utilities and may each have slightly
    different representation characteristics.
    """

    def dump(obj, fp=None):
        """
        Write the given object. If `fp` is None, then the string
        representation will be returned, otherwise, fp specifies a writeable
        object to which the representation will be written.
        """


class IExternalRepresentationReader(interface.Interface):
    """
    Something that can read an external string, as produced by
    :class:`.IExternalObjectRepresenter` and return an equivalent
    external value.`
    """

    def load(stream):
        """
        Load from the stream an external value. String values should be
        read as unicode.

        All objects must support the stream being a sequence of bytes,
        some may support an open file object.
        """


class IExternalObjectIO(IExternalObjectRepresenter,
                        IExternalRepresentationReader):
    """
    Something that can read and write external values.
    """


#: Constant requesting JSON format data
EXT_REPR_JSON = u'json'

#: Constant requesting YAML format data
EXT_REPR_YAML = u'yaml'


# Creating and updating new and existing objects given external forms


class IMimeObjectFactory(IFactory):
    """
    A factory named for the external mime-type of objects it works with.
    """


class IClassObjectFactory(IFactory):
    """
    A factory named for the external class name of objects it works with.
    """


class IAnonymousObjectFactory(IFactory):
    """
    A factory for external data that doesn't identify its object type.

    This data is not produced by this library but comes from external
    sources.

    When these are registered as factories (utilities) care must be
    taken to avoid name clashes (since there are no "natural" unique
    names).

    See the ZCML directive
    :class:`~nti.externalization.zcml.IAnonymousObjectFactoryDirective`
    for a simple way to do this.

    .. versionadded:: 1.0a3
    """


class IExternalizedObjectFactoryFinder(interface.Interface):
    """
    An adapter from an externalized object to something that can find
    factories.
    """

    def find_factory(externalized_object):
        """
        Given an externalized object, return a
        :class:`zope.component.interfaces.IFactory` to create the
        proper internal types.

        :return: An :class:`zope.component.interfaces.IFactory`, or :const:`None`.
        """


class IExternalReferenceResolver(interface.Interface):
    """
    Used as a multi-adapter from an *internal* object and an external reference
    to something that can resolve the reference.
    """

    def resolve(reference):
        """
        Resolve the external reference and return it.
        """

class INamedExternalizedObjectFactoryFinder(interface.Interface):
    """
    An object that can find factories for particular named
    external objects.

    This is registered as an adapter for particular internal
    objects, so that internal object, and any schema it implements,
    can be used to choose the factory for nested objects being
    updated into it.
    """

    def find_factory_for_named_value(name, value, registry):
        """
        Find a factory for the external object *value* when it
        is the value with the name *name*.

        This function has three key pieces of information to work with.

        First, it is an adapter from an internal object, so it knows
        the ultimate destination object (the context) where the results of the
        factory will be set.

        Second, it knows the incoming name of the external value.

        Third, it knows the actual incoming external value.

        For example, if the external data looked like ``{'key': 'value'}``
        a call to ``update_from_external_object(internal_object, data)``
        would conceptually result in a call that looked like this::

            adapter = INamedExternalizedObjectFactoryFinder(internal_object)
            factory = adapter.find_factory_for_named_value('key', 'value')

        When the value for the external data is a mutable sequence,
        this function will be called once for each item in the sequence.
        So external data of ``{'key': [1, 2, 3]}`` would result in calls
        ``('key', 1)``, ``('key', 2)`` and ``('key', 3)``.

        This function can return actual factories that produce fresh
        objects, or it can return the current object assigned to the ultimate
        attribute in the context to update that exact object in place.
        This can be beneficial for persistent objects.
        """

class IInternalObjectUpdater(interface.Interface):
    """
    An adapter that can be used to update an internal object from
    its externalized representation.
    """

    __external_oids__ = interface.Attribute(
        """For objects whose external form includes object references (OIDs),
		this attribute is a list of key paths that should be resolved. The
		values for the key paths may be singleton items or mutable sequences.
		Resolution may involve placing a None value for a key.""")

    __external_resolvers__ = interface.Attribute(
        """For objects who need to perform arbitrary resolution from external
		forms to internal forms, this attribute is a map from key path to
		a function of three arguments, the dataserver, the parsed object, and the value to resolve.
		It should return the new value. Note that the function here is at most
		a class or static method, not an instance method.""")

    def updateFromExternalObject(externalObject, context, **kwargs):
        """
        Update the object this is adapting from the external object.

        Alternately, the signature can be ``updateFromExternalObject(externalObject)``
        or simply ``updateFromExternalObject(externalObject, **kwargs)``. In this
        last case, ``context`` will be passed as a value in ``**kwargs``.


        :return: If not ``None``, a value that can be interpreted as a boolean,
                indicating whether or not the internal object actually
                underwent updates. If ``None``, the caller should assume that the object
                was updated (to allow older
                code that doesn't return at all.)
        """


class IInternalObjectIO(IInternalObjectExternalizer, IInternalObjectUpdater):
    """
    A single object responsible for both reading and writing internal objects
    in external forms. This is convenient for keeping code organized.
    """

class IInternalObjectIOFinder(INamedExternalizedObjectFactoryFinder,
                              IInternalObjectIO):
    """
    Like `IInternalObjectIO`, but this object also gets the chance to find factories
    for objects.

    The class `~.InterfaceObjectIO` implements this interface.
    """

class IObjectWillUpdateFromExternalEvent(IObjectEvent):
    """
    An object will be updated from an external value.
    """
    external_value = interface.Attribute("The external value")


@interface.implementer(IObjectWillUpdateFromExternalEvent)
class ObjectWillUpdateFromExternalEvent(ObjectEvent):
    external_value = None


class IObjectModifiedFromExternalEvent(IObjectModifiedEvent):
    """
    An object has been updated from an external value.
    """
    kwargs = interface.Attribute("The key word arguments")
    external_value = interface.Attribute("The external value")


@interface.implementer(IObjectModifiedFromExternalEvent)
class ObjectModifiedFromExternalEvent(ObjectModifiedEvent):

    kwargs = None
    external_value = None

    def __init__(self, obj, *descriptions, **kwargs):
        super(ObjectModifiedFromExternalEvent, self).__init__(obj, *descriptions)
        self.kwargs = kwargs


class IIterable(interface.Interface):
    """
    Base interface for iterable types.
    """

    def __iter__():
        """Return an iterator object.
        """


class IList(IIterable):
    """
    Marker interface for lists
    """
interface.classImplements(list, IList)


class _ILegacySearchModuleFactory(interface.Interface):

    def __call__(*args, **kwargs): # pylint:disable=no-method-argument,arguments-differ
        """
        Create and return the object.
        """
