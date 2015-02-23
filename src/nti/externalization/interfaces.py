#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Externalization Interfaces

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope.interface.common.sequence import ISequence
from zope.interface.common.mapping import IFullMapping

from zope.component.interfaces import IFactory

from zope.location import ILocation

class StandardExternalFields(object):
	"""
	Namespace object defining constants whose values are the
	keys used in external mappings.
	"""
	OID   = 'OID'
	ID    = 'ID'
	NTIID = 'NTIID'
	LAST_MODIFIED = 'Last Modified'
	CREATED_TIME = 'CreatedTime'
	CREATOR = 'Creator'
	CONTAINER_ID = 'ContainerId'
	CLASS = 'Class'
	MIMETYPE = 'MimeType'
	LINKS = 'Links'
	HREF = 'href'
	ITEMS = 'Items'

StandardExternalFields.ALL = (lambda : [ v for k,v in StandardExternalFields.__dict__.iteritems() 
										if not k.startswith( '_' ) ])()

class StandardInternalFields(object):
	"""
	Namespace object defining constants whose values are the
	property/attribute names looked for on internal objects.
	"""

	ID = 'id'
	NTIID = 'ntiid'

	CREATOR = 'creator'
	LAST_MODIFIED = 'lastModified'
	LAST_MODIFIEDU = 'LastModified'
	CREATED_TIME = 'createdTime'
	CONTAINER_ID = 'containerId'

class IInternalObjectExternalizer(interface.Interface):
	"""
	Implemented by, or adapted from, an object that can
	be externalized.
	"""

	__external_can_create__ = interface.Attribute(
		""" This must be set to true, generally at the class level, for objects
		that can be created by specifying their Class name. """)

	__external_class_name__ = interface.Attribute(
		""" If present, the value is a string that is used for the 'Class' key in the
		external dictionary. If not present, the local name of the object's class is
		used instead. """)

	def toExternalObject(**kwargs):
		""" Optional, see this :func:`~nti.externalization.externalization.to_external_object`."""

	# def updateFromExternalObject( parsed, *args, **kwargs ):
	# 	""" Optional, updates this object using the parsed input
	# 	from the external object form. If the object does not implement
	# 	this method, then if it implements clear() and update() those will be
	# 	used. The arguments are optional context arguments possibly passed. One
	# 	common key is dataserver pointing to a Dataserver."""

IExternalObject = IInternalObjectExternalizer # b/c aliase

class INonExternalizableReplacer(interface.Interface):
	"""
	An adapter object called to make a replacement when
	some object cannot be externalized.
	"""

	def __call__(obj):
		"""
		:return: An externalized object to replace the given object. Possibly the
			given object itself if some higher level will handle it.
		"""

class INonExternalizableReplacement(interface.Interface):
	"""
	This interface may be applied to objects that serve as a replacement
	for a non-externalized object.
	"""

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

	def decorateExternalObject( origial, external ):
		"""
		Decorate the externalized object (which is probably a mapping,
		though this is not guaranteed).

		:param original: The object that is being externalized.
			Passed to facilitate using non-classes as decorators.
		:param external: The externalization of that object, produced
			by an implementation of :class:`~nti.externalization.interfaces.IInternalObjectExternalizer` or
			default rules.
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

	def decorateExternalMapping( original, external ):
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

class ILocatedExternalMapping(IExternalizedObject,ILocation,IFullMapping):
	"""
	The externalization of an object as a dictionary, maintaining its location
	information.
	"""

class ILocatedExternalSequence(IExternalizedObject,ILocation,ISequence):
	"""
	The externalization of an object as a sequence, maintaining its location
	information.
	"""

@interface.implementer( ILocatedExternalMapping )
class LocatedExternalDict(dict):
	"""
	A dictionary that implements :class:`~nti.externalization.interfaces.ILocatedExternalMapping`. Returned
	by :func:`~nti.externalization.externalization.to_standard_external_dictionary`.

	This class is not :class:`.IContentTypeAware`, and it indicates so explicitly by declaring a
	`mime_type` value of None.
	"""

	__name__ = ''
	__parent__ = None
	__acl__ = ()
	mimeType = None

@interface.implementer( ILocatedExternalSequence )
class LocatedExternalList(list):
	"""
	A list that implements :class:`~nti.externalization.interfaces.ILocatedExternalSequence`. Returned
	by :func:`~nti.externalization.externalization.to_external_object`.

	This class is not :class:`.IContentTypeAware`, and it indicates so explicitly by declaring a
	`mimeType` value of None.
	"""

	__name__ = ''
	__parent__ = None
	__acl__ = ()
	mimeType = None

###
# Representations as strings
###

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
EXT_REPR_JSON = 'json'
#: Constant requesting PList (XML) format data
EXT_REPR_PLIST = 'plist'
#: Constant requesting YAML format data
EXT_REPR_YAML = 'yaml'

### Creating and updating new and existing objects given external forms

class IMimeObjectFactory(IFactory):
	"""
	A factory named for the external mime-type of objects it works with.
	"""

class IClassObjectFactory(IFactory):
	"""
	A factory named for the external class name of objects it works with.
	"""

class IExternalizedObjectFactoryFinder(interface.Interface):
	"""
	An adapter from an externalized object to something that can find
	factories.
	"""

	def find_factory( externalized_object ):
		"""
		Given an externalized object, return a :class:`zope.component.interfaces.IFactory` to create the proper
		internal types.

		:return: An :class:`zope.component.interfaces.IFactory`, or :const:`None`.
		"""

class IExternalReferenceResolver(interface.Interface):
	"""
	Used as a multi-adapter from an *internal* object and an external reference
	to something that can resolve the reference.
	"""

	def resolve( reference ):
		"""
		Resolve the external reference and return it.
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
		""" For objects who need to perform arbitrary resolution from external
		forms to internal forms, this attribute is a map from key path to
		a function of three arguments, the dataserver, the parsed object, and the value to resolve.
		It should return the new value. Note that the function here is at most
		a class or static method, not an instance method. """)

	def updateFromExternalObject( externalObject, *args, **kwargs ):
		"""
		Update the object this is adapting from the external object.
		Two alternate signatures are supported, one with ``dataserver`` instead of
		context, and one with no keyword args.

		:return: If not ``None``, a value that can be interpreted as a boolean,
			indicating whether or not the internal object actually
			underwent updates. If ``None``, no meaning is assigned (to allow older
			code that doesn't return at all.)
		"""

class IInternalObjectIO(IInternalObjectExternalizer,IInternalObjectUpdater):
	"""
	A single object responsible for both reading and writing internal objects
	in external forms.
	"""

from zope.lifecycleevent import ObjectModifiedEvent
from zope.lifecycleevent import IObjectModifiedEvent

class IObjectModifiedFromExternalEvent(IObjectModifiedEvent):
	"""
	An object has been updated from an external value.
	"""

	external_value = interface.Attribute("The external value")

@interface.implementer( IObjectModifiedFromExternalEvent )
class ObjectModifiedFromExternalEvent(ObjectModifiedEvent):
	external_value = None
