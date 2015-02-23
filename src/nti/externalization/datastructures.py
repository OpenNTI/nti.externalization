#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Datastructures to help externalization.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import sys
import numbers

from zope import schema
from zope import interface
from zope.schema.interfaces import SchemaNotProvided

from ZODB.POSException import POSError

from nti.schema.interfaces import find_most_derived_interface

from .interfaces import IInternalObjectIO
from .interfaces import StandardInternalFields
from .interfaces import StandardExternalFields

from .internalization import validate_named_field_value
from .externalization import to_minimal_standard_external_dictionary
from .externalization import to_standard_external_dictionary, toExternalObject

def _syntheticKeys( ):
	return ('OID', 'ID', 'Last Modified', 'Creator', 'ContainerId', 'Class')

def _isMagicKey( key ):
	""" For our mixin objects that have special keys, defines
	those keys that are special and not settable by the user. """
	return key in _syntheticKeys()

isSyntheticKey = _isMagicKey

class ExternalizableDictionaryMixin(object):
	""" Implements a toExternalDictionary method as a base for subclasses. """

	#: If true, then when asked for the standard dictionary, we will instead
	#: produce the *minimal* dictionary. See :func:`~to_minimal_standard_external_dictionary`
	__external_use_minimal_base__ = False

	def __init__(self, *args):
		super(ExternalizableDictionaryMixin,self).__init__(*args)

	def _ext_replacement( self ):
		return self

	def _ext_standard_external_dictionary( self, replacement, mergeFrom=None, **kwargs ):
		if self.__external_use_minimal_base__:
			return to_minimal_standard_external_dictionary( replacement, 
															mergeFrom=mergeFrom,
															**kwargs )
		return to_standard_external_dictionary( replacement, 
												mergeFrom=mergeFrom,
												**kwargs )

	def toExternalDictionary( self, mergeFrom=None, **kwargs ):
		return self._ext_standard_external_dictionary( self._ext_replacement(), 
													   mergeFrom=mergeFrom,
													   **kwargs )

	def stripSyntheticKeysFromExternalDictionary( self, external ):
		""" Given a mutable dictionary, removes all the external keys
		that might have been added by toExternalDictionary and echoed back. """
		for k in _syntheticKeys():
			external.pop( k, None )
		return external

@interface.implementer(IInternalObjectIO)
class AbstractDynamicObjectIO(ExternalizableDictionaryMixin):
	"""
	Base class for objects that externalize based on dynamic information.

	Abstractions are in place to allow subclasses to map external and internal names
	independently (this type never uses getattr/setattr/hasattr, except for some
	standard fields).
	"""

	# TODO: there should be some better way to customize this if desired (an explicit list)
	# TODO: Play well with __slots__
	# TODO: This won't evolve well. Need something more sophisticated,
	# probably a meta class.

	# Avoid things super handles
	_excluded_out_ivars_ = {StandardInternalFields.ID, 
							StandardExternalFields.ID, 
							StandardInternalFields.CREATOR,
							StandardExternalFields.CREATOR,
							StandardInternalFields.CONTAINER_ID,
							'lastModified',
							StandardInternalFields.LAST_MODIFIEDU,
							StandardInternalFields.CREATED_TIME,
							'links'}
	_excluded_in_ivars_ = {	StandardInternalFields.ID, 
							StandardExternalFields.ID,
						   	StandardExternalFields.OID,
						   	StandardInternalFields.CREATOR,
						   	StandardExternalFields.CREATOR,
						   	StandardInternalFields.LAST_MODIFIED,
						   	StandardInternalFields.LAST_MODIFIEDU,
						   	# Also the IDCTimes created/modified values
						   	'created', 'modified',
						   	StandardExternalFields.CLASS,
						   	StandardInternalFields.CONTAINER_ID}
	_ext_primitive_out_ivars_ = set()
	_prefer_oid_ = False


	def _ext_all_possible_keys(self):
		raise NotImplementedError() # pragma: no cover

	def _ext_setattr( self, ext_self, k, value ):
		raise NotImplementedError() # pragma: no cover

	def _ext_getattr( self, ext_self, k ):
		"""
		Return the attribute of the `ext_self` object with the external name `k`.
		If the attribute does not exist, should raise (typically :class:`AttributeError`)
		"""
		raise NotImplementedError() # pragma: no cover

	def _ext_keys(self):
		"""
		Return only the names of attributes that should be externalized.
		These values will be used as keys in the external dictionary.

		See :meth:`_ext_all_possible_keys`. This implementation then filters out
		*private* attributes (those beginning with an underscore),
		and those listed in `_excluded_in_ivars_.`
		"""
		#ext_self = self._ext_replacement()
		return 	[k for k in self._ext_all_possible_keys()
				 if (k not in self._excluded_out_ivars_  # specifically excluded
					 and not k.startswith( '_' ))]			# private
					# and not callable(getattr(ext_self,k)))]	# avoid functions

	def _ext_primitive_keys(self):
		"""
		Return a container of string keys whose values are known to be primitive.
		This is an optimization for writing.
		"""
		return self._ext_primitive_out_ivars_

	def toExternalDictionary( self, mergeFrom=None, **kwargs ):
		result = super(AbstractDynamicObjectIO,self).toExternalDictionary( mergeFrom=mergeFrom, **kwargs )
		ext_self = self._ext_replacement()
		primitive_ext_keys = self._ext_primitive_keys()
		for k in self._ext_keys():
			if k in result:
				# Standard key already added
				continue

			attr_val = self._ext_getattr( ext_self, k )
			__traceback_info__ = k, attr_val
			result[k] = toExternalObject( attr_val, **kwargs ) if k not in primitive_ext_keys else attr_val

			if result[k] is not attr_val:
				# We want to be sure things we externalize have the right parent relationship
				# but if we are directly externalizing an existing object (e.g., primitive or something
				# that uses a replacement) we don't want to change the relationship or even set one in the first
				# place---if the object gets pickled later on, that could really screw things up
				# (One symptom is InvalidObjectReference from ZODB across transactions/tests)
				try: #if ILocation.providedBy( result[k] ): (throwing is faster that providedBy)
					result[k].__parent__ = ext_self
				except AttributeError:
					pass

		if StandardExternalFields.ID in result and StandardExternalFields.OID in result \
			   and self._prefer_oid_ and result[StandardExternalFields.ID] != result[StandardExternalFields.OID]:
			result[StandardExternalFields.ID] = result[StandardExternalFields.OID]
		return result

	def toExternalObject( self, mergeFrom=None, **kwargs ):
		return self.toExternalDictionary(mergeFrom, **kwargs)

	def _ext_accept_update_key( self, k, ext_self, ext_keys ):
		"""
		Returns whether or not this key should be accepted for setting
		on the object, or silently ignored.
		:param ext_keys: As an optimization, the value of :meth:`_ext_all_possible_keys`
			is passed. Keys are only accepted if they are in this list.
		"""
		if k in self._excluded_in_ivars_:
			return False

		return k in ext_keys

	def _ext_accept_external_id(self, ext_self, parsed):
		"""
		If the object we're updating does not have an ``id`` set, but there is an
		``ID`` in the external object, should we be able to use it?
		:return: boolean
		"""
		return False # false by default

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		updated = False

		ext_self = self._ext_replacement()
		ext_keys = self._ext_all_possible_keys()
		for k in parsed:
			if not self._ext_accept_update_key( k, ext_self, ext_keys ):
				continue
			__traceback_info__ = k
			self._ext_setattr( ext_self, k, parsed[k] )
			updated = True

		if 	StandardExternalFields.CONTAINER_ID in parsed and \
			getattr( ext_self, StandardInternalFields.CONTAINER_ID, parsed ) is None:
			setattr( ext_self, StandardInternalFields.CONTAINER_ID, 
					parsed[StandardExternalFields.CONTAINER_ID] )
		if 	StandardExternalFields.CREATOR in parsed and \
			getattr( ext_self, StandardExternalFields.CREATOR, parsed ) is None:
			setattr( ext_self, StandardExternalFields.CREATOR, 
					 parsed[StandardExternalFields.CREATOR] )
		if (StandardExternalFields.ID in parsed
			and getattr( ext_self, StandardInternalFields.ID, parsed ) is None
			and self._ext_accept_external_id(ext_self, parsed)):
			setattr( ext_self, StandardInternalFields.ID, parsed[StandardExternalFields.ID] )

		return updated

@interface.implementer(IInternalObjectIO)
class ExternalizableInstanceDict(AbstractDynamicObjectIO):
	"""
	Externalizes to a dictionary containing the members of __dict__ that do not start with an underscore.

	Meant to be used as a super class; also can be used as an external object superclass.
	"""

	# TODO: there should be some better way to customize this if desired (an explicit list)
	# TODO: Play well with __slots__? ZODB supports slots, but doesn't recommend them
	# TODO: This won't evolve well. Need something more sophisticated,
	# probably a meta class.

	_update_accepts_type_attrs = False

	def _ext_all_possible_keys(self):
		return self._ext_replacement().__dict__.keys()

	def _ext_setattr( self, ext_self, k, value ):
		setattr( ext_self, k, value )

	def _ext_getattr( self, ext_self, k ):
		return getattr( ext_self, k )

	def _ext_accept_update_key( self, k, ext_self, ext_keys ):
		return super(ExternalizableInstanceDict,self)._ext_accept_update_key( k, ext_self, ext_keys ) \
		  or (self._update_accepts_type_attrs and hasattr( ext_self, k ))

	def __repr__( self ):
		try:
			return "<%s.%s %s>" % (self.__class__.__module__, self.__class__.__name__, getattr(self,'creator', '') )
		except POSError, cse:
			return '<%s(Ghost, %s)>' % (self.__class__.__name__, cse)
		except (ValueError,LookupError), e: # Things like invalid NTIID, missing registrations
			return '<%s(%s)>' % (self.__class__.__name__, e)
		except (AttributeError), e: # Another weird database-related issue
			return '<%s(%s)>' % (self.__class__.__name__, e)

_primitives = six.string_types + (numbers.Number,bool)

class _InterfaceCache(object):
	iface = None
	ext_primitive_out_ivars = None
	ext_all_possible_keys = None
	ext_accept_external_id = None

	@classmethod
	def cache_for( cls, externalizer, ext_self ):
		# The Declaration objects maintain a _v_attrs that
		# gets blown away on changes to themselves or their
		# dependents, including adding interfaces dynamically to an instance
		# (In that case, the provided object actually gets reset)
		cache_place = interface.providedBy( ext_self )
		try:
			attrs = cache_place._v_attrs
		except AttributeError:
			attrs = cache_place._v_attrs = {}
		key = type(externalizer)
		if key in attrs:
			cache = attrs[key]
		else:
			cache = cls()
			attrs[key] = cache
		return cache

@interface.implementer(IInternalObjectIO)
class InterfaceObjectIO(AbstractDynamicObjectIO):
	"""
	Externalizes to a dictionary based on getting the attributes of an
	object defined by an interface. If any attribute has a true value
	for the tagged value ``_ext_excluded_out``, it will not be considered
	for reading or writing.

	Meant to be used as an adapter, so accepts the object to
	externalize in the constructor, as well as the interface to use to
	guide the process. The object is externalized using the
	most-derived version of the interface given to the constructor
	that it implements.

	If the interface (or an ancestor) has a tagged value
	``__external_class_name__``, it can either be the value to use for
	the ``Class`` key, or a callable
	``__external_class_name__(interface, object ) -> name.``

	(TODO: In the future extend this to multiple, non-overlapping interfaces, and better
	interface detection (see :class:`ModuleScopedInterfaceObjectIO` for a limited version of this.)
	"""

	_ext_iface_upper_bound = None
	validate_after_update = True

	def __init__( self, ext_self, iface_upper_bound=None, validate_after_update=True ):
		"""
		:param iface_upper_bound: The upper bound on the schema to use
			to externalize `ext_self`; we will use the most derived sub-interface
			of this interface that the object implements. Subclasses can either override this
			constructor to pass this parameter (while taking one argument themselves,
			to be usable as an adapter), or they can define the class
			attribute ``_ext_iface_upper_bound``
		:param bool validate_after_update: If ``True`` (the default) then the entire
			schema will be validated after an object has been updated with :meth:`update_from_external_object`,
			not just the keys that were assigned.
		"""
		super(InterfaceObjectIO, self).__init__(  )
		self._ext_self = ext_self
		# Cache all of this data that we use. It's required often and, if not quite a bottleneck,
		# does show up in the profiling data
		cache = _InterfaceCache.cache_for( self, ext_self )
		if not cache.iface:
			cache.iface = self._ext_find_schema( ext_self, iface_upper_bound or self._ext_iface_upper_bound )
		self._iface = cache.iface

		if not cache.ext_primitive_out_ivars:
			cache.ext_primitive_out_ivars = self._ext_primitive_out_ivars_.union( self._ext_find_primitive_keys() )
		self._ext_primitive_out_ivars_ = cache.ext_primitive_out_ivars

		if not validate_after_update:
			self.validate_after_update = validate_after_update

	@property
	def schema(self):
		""" The schema we will use to guide the process """
		return self._iface

	def _ext_find_schema( self, ext_self, iface_upper_bound ):
		return find_most_derived_interface( ext_self, iface_upper_bound, possibilities=self._ext_schemas_to_consider( ext_self ) )

	def _ext_find_primitive_keys(self):
		result = set()
		for n in self._ext_all_possible_keys():
			field = self._iface[n]
			field_type = getattr( field, '_type', None )
			if field_type:
				if isinstance( field_type, tuple ):
					if all( (issubclass( x, _primitives ) for x in field_type ) ):
						result.add( n )
				elif issubclass( field_type, _primitives ):
					result.add( n )

		return result

	def _ext_schemas_to_consider( self, ext_self ):
		return interface.providedBy( ext_self )

	def _ext_replacement( self ):
		return self._ext_self

	def _ext_all_possible_keys(self):
		cache = _InterfaceCache.cache_for( self, self._ext_self )
		if cache.ext_all_possible_keys is None:
			cache.ext_all_possible_keys = [n for n in self._iface.names(all=True)
										   if not interface.interfaces.IMethod.providedBy(self._iface[n])
										   and not self._iface[n].queryTaggedValue('_ext_excluded_out', False)]
		return cache.ext_all_possible_keys

	def _ext_getattr( self, ext_self, k ):
		# TODO: Should this be directed through IField.get?
		return getattr( ext_self, k )

	def _ext_setattr( self, ext_self, k, value ):
		validate_named_field_value( ext_self, self._iface, k, value )()

	def _ext_accept_external_id(self, ext_self, parsed):
		"""
		If the interface we're working from has a tagged value
		of `__external_accept_id__` on the `id` field, then
		this will return that value; otherwise, returns false.
		"""
		cache = _InterfaceCache.cache_for(self, ext_self)
		if cache.ext_accept_external_id is None:
			try:
				cache.ext_accept_external_id = cache.iface['id'].getTaggedValue('__external_accept_id__')
			except KeyError:
				cache.ext_accept_external_id = False
		return cache.ext_accept_external_id

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		result = super(InterfaceObjectIO,self).updateFromExternalObject( parsed, *args, **kwargs )
		# If we make it this far, then validate the object.
		# TODO: Should probably just make sure that there are no /new/ validation errors added
		# Best we can do right now is skip this step if asked
		if self.validate_after_update:
			self._validate_after_update(self._iface, self._ext_self)
		return result

	def _validate_after_update( self, iface, ext_self ):
		errors = schema.getValidationErrors( iface, ext_self )
		if errors:
			__traceback_info__ = errors
			try:
				raise errors[0][1]
			except SchemaNotProvided as e:
				exc_info = sys.exc_info()
				if not e.args: # zope.schema doesn't fill in the details, which sucks
					e.args = (errors[0][0],)
				raise exc_info[0], exc_info[1], exc_info[2]

	def toExternalObject( self, mergeFrom=None, **kwargs ):
		ext_class_name = None
		for iface in self._iface.__iro__:
			ext_class_name = iface.queryTaggedValue( '__external_class_name__' )
			if callable(ext_class_name):
				# Even though the tagged value may have come from a superclass,
				# give the actual class (interface) we're using
				ext_class_name = ext_class_name( self._iface, self._ext_replacement() )
			if ext_class_name:
				break

		if ext_class_name:
			mergeFrom = mergeFrom or {}
			mergeFrom[StandardExternalFields.CLASS] = ext_class_name

		result = super(InterfaceObjectIO,self).toExternalObject( mergeFrom=mergeFrom, **kwargs )
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

	def _ext_find_schema( self, ext_self, iface_upper_bound ):
		# If the upper bound is given, then let the super class handle it all.
		# Presumably the user has given the correct branch to search.

		if iface_upper_bound is not None:
			return super(ModuleScopedInterfaceObjectIO,self)._ext_find_schema( ext_self, iface_upper_bound )

		most_derived = super(ModuleScopedInterfaceObjectIO,self)._ext_find_schema( ext_self, interface.Interface )
		# In theory, this is now the most derived interface.
		# If we have a graph that is not a tree, though, it may not be.
		# In that case, we are not suitable for use with this object
		for iface in self._ext_schemas_to_consider( ext_self ):
			if not most_derived.isOrExtends( iface ):
				raise TypeError( "Most derived interface %s does not extend %s; non-tree interface structure. "
								 "Searching module %s and considered %s on object %s of class %s and type %s"
								 % ( most_derived, iface, self._ext_search_module,
									 list(self._ext_schemas_to_consider( ext_self ) ), 
									 ext_self, ext_self.__class__, type(ext_self) ) )

		return most_derived

	def _ext_schemas_to_consider( self, ext_self ):
		return (x for x in interface.providedBy( ext_self )
				if x.__module__ == self._ext_search_module.__name__
				and not x.queryTaggedValue('_ext_is_marker_interface'))

# Things that have moved
import zope.deferredimport
zope.deferredimport.initialize()
zope.deferredimport.deprecatedFrom(
	"Moved to nti.externalization.interfaces",
	"nti.externalization.interfaces",
	"IExternalObject",
	"LocatedExternalDict",
	"LocatedExternalList",
	"ILocatedExternalMapping",
	"ILocatedExternalSequence")
