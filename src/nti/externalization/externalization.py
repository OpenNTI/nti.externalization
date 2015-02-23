#!/usr/bin/env python
"""
Functions related to actually externalizing objects.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import numbers
import collections
from collections import defaultdict

from ZODB.POSException import POSKeyError

import persistent

import BTrees.OOBTree

from zope import component
from zope import interface
from zope import deprecation
from zope.interface.common import sequence
from zope.dublincore import interfaces as dub_interfaces

from nti.ntiids import ntiids

from .oids import to_external_ntiid_oid

from .interfaces import IExternalObject
from .interfaces import LocatedExternalDict
from .interfaces import StandardExternalFields
from .interfaces import StandardInternalFields
from .interfaces import IExternalObjectDecorator
from .interfaces import ILocatedExternalSequence
from .interfaces import IExternalMappingDecorator
from .interfaces import INonExternalizableReplacer
from .interfaces import INonExternalizableReplacement 

# Local for speed
StandardExternalFields_ID = StandardExternalFields.ID
StandardExternalFields_OID = StandardExternalFields.OID
StandardExternalFields_CLASS = StandardExternalFields.CLASS
StandardExternalFields_NTIID = StandardExternalFields.NTIID
StandardExternalFields_CREATOR = StandardExternalFields.CREATOR
StandardExternalFields_MIMETYPE = StandardExternalFields.MIMETYPE
StandardExternalFields_CONTAINER_ID = StandardExternalFields.CONTAINER_ID
StandardExternalFields_CREATED_TIME = StandardExternalFields.CREATED_TIME
StandardExternalFields_LAST_MODIFIED = StandardExternalFields.LAST_MODIFIED

StandardInternalFields_ID = StandardInternalFields.ID
StandardInternalFields_NTIID = StandardInternalFields.NTIID
StandardInternalFields_CREATOR = StandardInternalFields.CREATOR
StandardInternalFields_CONTAINER_ID = StandardInternalFields.CONTAINER_ID
StandardInternalFields_CREATED_TIME = StandardInternalFields.CREATED_TIME
StandardInternalFields_LAST_MODIFIED = StandardInternalFields.LAST_MODIFIED
StandardInternalFields_LAST_MODIFIEDU = StandardInternalFields.LAST_MODIFIEDU

# It turns out that the name we use for externalization (and really the registry, too)
# we must keep thread-local. We call into objects without any context,
# and they call back into us, and otherwise we would lose
# the name that was established at the top level.
_NotGiven = object()

from .threadlocal import ThreadLocalManager

_manager = ThreadLocalManager(default=lambda: {'name': _NotGiven,
											   'memos': None})

# Things that can be directly externalized
_primitives = six.string_types + (numbers.Number,bool)

def catch_replace_action( obj, exc ):
	"""
	Replaces the external component object `obj` with an object noting a broken object.
	"""
	return { "Class": "BrokenExceptionObject" }

@interface.implementer(INonExternalizableReplacement)
class _NonExternalizableObject(dict): pass

def DefaultNonExternalizableReplacer( obj ):
	logger.debug("Asked to externalize non-externalizable object %s, %s", 
				 type(obj), obj )
	result = _NonExternalizableObject( 	Class='NonExternalizableObject', 
										InternalType=str(type(obj)) )
	return result

class NonExternalizableObjectError(TypeError): pass

def DevmodeNonExternalizableObjectReplacer( obj ):
	"""
	When devmode is active, non-externalizable objects raise an exception.
	"""
	raise NonExternalizableObjectError("Asked to externalize non-externalizable object %s, %s" % (type(obj), obj ) )

@interface.implementer(INonExternalizableReplacer)
def _DevmodeNonExternalizableObjectReplacer( obj ):
	return DevmodeNonExternalizableObjectReplacer

#: The types that we will treat as sequences for externalization purposes. These
#: all map onto lists. (TODO: Should we just try to iter() it, ignoring strings?)
#: In addition, we also support :class:`~zope.interface.common.sequence.IFiniteSequence`
#: by iterating it and mapping onto a list. This allows :class:`~z3c.batching.interfaces.IBatch`
#: to be directly externalized.
SEQUENCE_TYPES = (persistent.list.PersistentList,
				  collections.Set, 
				  list,
				  tuple)

#: The types that we will treat as mappings for externalization purposes. These
#: all map onto a dict.
MAPPING_TYPES  = (persistent.mapping.PersistentMapping,
				  BTrees.OOBTree.OOBTree,
				  collections.Mapping)

from zope.cachedescriptors.property import CachedProperty

class _ExternalizationState(object):

	name = ''
	request = None
	registry = None

	def __init__( self, **kwargs ):

		for k, v in kwargs.iteritems():
			setattr( self, k, v )

	@CachedProperty
	def memo(self):
		# We take a similar approach to pickle.Pickler
		# for memoizing objects we've seen:
		# we map the id of an object to a two tuple: (obj, external-value)
		# the original object is kept in the tuple to keep transient objects alive
		# and thus ensure no overlapping ids
		return {}

def _to_external_object_state(obj, state, top_level=False, decorate=True):
	__traceback_info__ = obj
	
	orig_obj = obj
	orig_obj_id = id(obj)
	if orig_obj_id in state.memo:
		return state.memo[orig_obj_id][1]

	try:
		# TODO: This is needless for the mapping types and sequence types. rework to avoid.
		# Benchmarks show that simply moving it into the last block doesn't actually save much
		# (due to all the type checks in front of it?)

		# This is for legacy code support, to allow existing methods to move to adapters
		# and call us without infinite recursion
		obj_has_usable_external_object = hasattr(obj, 'toExternalObject') and \
										 not getattr( obj, '__ext_ignore_toExternalObject__', False )

		if not obj_has_usable_external_object and not IExternalObject.providedBy( obj ):
			adapter = state.registry.queryAdapter(obj, IExternalObject, default=None, 
												  name=state.name )
			if not adapter and state.name != '':
				# try for the default, but allow passing name of None to disable (?)
				adapter = state.registry.queryAdapter(obj, IExternalObject,
													  default=None, name='' )
			if adapter:
				obj = adapter
				obj_has_usable_external_object = True

		# Note that for speed, before calling 'recall' we are performing the primitive check
		result = obj
		if obj_has_usable_external_object: # either an adapter or the original object
			result = obj.toExternalObject(request=state.request, name=state.name)
		elif hasattr( obj, "toExternalDictionary" ):
			result = obj.toExternalDictionary(request=state.request, name=state.name)
		elif hasattr( obj, "toExternalList" ):
			result = obj.toExternalList()
		elif isinstance(obj, MAPPING_TYPES ):
			result = to_standard_external_dictionary(obj, name=state.name,
													 registry=state.registry, 
													 request=state.request,
													 decorate=decorate )
			if obj.__class__ is dict:
				result.pop( 'Class', None )
			# Note that we recurse on the original items, not the things newly
			# added.
			# NOTE: This means that Links added here will not be externalized. There
			# is an IExternalObjectDecorator that does that
			for key, value in obj.items():
				result[key] = _to_external_object_state( value, state, decorate=decorate) \
							  if not isinstance(value, _primitives) else value
		elif isinstance( obj, SEQUENCE_TYPES ) or \
			 sequence.IFiniteSequence.providedBy( obj ):
			result = [ (_to_external_object_state(x, state, decorate=decorate) \
					    if not isinstance(x, _primitives) else x) for x in obj ]
			result = state.registry.getAdapter(result, ILocatedExternalSequence)
		# PList doesn't support None values, JSON does. The closest
		# coersion I can think of is False.
		elif obj is None:
			if state.coerceNone:
				result = False
		else:
			# Otherwise, we probably won't be able to JSON-ify it.
			# TODO: Should this live here, or at a higher level where the ultimate
			# external target/use-case is known?
			replacer = state.default_non_externalizable_replacer
			result = state.registry.queryAdapter(obj, INonExternalizableReplacer, 
												 default=replacer)(obj)

		if decorate:
			for decorator in state.registry.subscribers((orig_obj,), IExternalObjectDecorator):
				decorator.decorateExternalObject( orig_obj, result )

		# Request specific decorating, if given, is more specific than plain object
		# decorating, so it gets to go last.
		if decorate and state.request is not None and state.request is not _NotGiven:
			for decorator in state.registry.subscribers( (orig_obj, state.request), IExternalObjectDecorator):
				decorator.decorateExternalObject( orig_obj, result )

		state.memo[orig_obj_id] = (orig_obj, result)
		return result
	except state.catch_components as t:
		if top_level:
			raise
		# python rocks. catch_components could be an empty tuple, meaning we catch nothing.
		# or it could be any arbitrary list of exceptions.
		# NOTE: we cannot try to to-string the object, it may try to call back to us
		# NOTE2: In case we encounter a proxy (zope.container.contained.ContainedProxy)
		# the type(o) is not reliable. Only the __class__ is.
		logger.exception("Exception externalizing component object %s/%s", 
						 type(obj), obj.__class__ )
		return state.catch_component_action( obj, t )

def toExternalObject( obj, coerceNone=False, name=_NotGiven, registry=component,
					  catch_components=(), catch_component_action=None,
					  default_non_externalizable_replacer=DefaultNonExternalizableReplacer,
					  request=_NotGiven,
					  decorate=True):
	""" Translates the object into a form suitable for
	external distribution, through some data formatting process. See :const:`SEQUENCE_TYPES`
	and :const:`MAPPING_TYPES` for details on what we can handle by default.

	:param string name: The name of the adapter to :class:IExternalObject to look
		for. Defaults to the empty string (the default adapter). If you provide
		a name, and an adapter is not found, we will still look for the default name
		(unless the name you supply is None).
	:param tuple catch_components: A tuple of exception classes to catch when
		externalizing sub-objects (e.g., items in a list or dictionary). If one of these
		exceptions is caught, then `catch_component_action` will be called to raise or replace
		the value. The default is to catch nothing.
	:param callable catch_component_action: If given with `catch_components`, a function
		of two arguments, the object being externalized and the exception raised. May return
		a different object (already externalized) or re-raise the exception. There is no default,
		but :func:`catch_replace_action` is a good choice.
	:param callable default_non_externalizable_replacer: If we are asked to externalize an object
		and cannot, and there is no :class:`~nti.externalization.interfaces.INonExternalizableReplacer` registered for it,
		then call this object and use the results.
	:param request: If given, the request that the object is being externalized on behalf
		of. If given, then the object decorators will also look for subscribers
		to the object plus the request (like traversal adapters); this is a good way to
		separate out request or user specific code.

	"""

	# Catch the primitives up here, quickly
	if isinstance(obj, _primitives):
		return obj

	v = dict(locals())
	v.pop( 'obj' )
	state = _ExternalizationState( **v )

	if name is _NotGiven:
		name = _manager.get()['name']
	if name is _NotGiven:
		name = ''

	memos = _manager.get()['memos']
	if memos is None:
		memos = defaultdict(dict)

	_manager.push( {'name': name, 'memos': memos} )
	state.name = name
	state.memo = memos[name]

	if request is _NotGiven:
		request = get_current_request()
	state.request = request

	try:
		return _to_external_object_state( obj, state, top_level=True, decorate=decorate)
	finally:
		_manager.pop()

to_external_object = toExternalObject

def stripSyntheticKeysFromExternalDictionary( external ):
	""" Given a mutable dictionary, removes all the external keys
	that might have been added by :func:`to_standard_external_dictionary` and echoed back. """
	for key in _syntheticKeys():
		external.pop( key, None )
	return external

def _syntheticKeys( ):
	return ('OID', 'ID', 'Last Modified', 'Creator', 'ContainerId', 'Class')

def _isMagicKey( key ):
	""" For our mixin objects that have special keys, defines
	those keys that are special and not settable by the user. """
	return key in _syntheticKeys()

isSyntheticKey = _isMagicKey

from calendar import timegm as _calendar_gmtime

def _datetime_to_epoch( dt ):
	return _calendar_gmtime( dt.utctimetuple() ) if dt is not None else None

def _choose_field(result, self, ext_name,
				  converter=lambda x: x,
				  fields=(),
				  sup_iface=None, sup_fields=(), sup_converter=lambda x: x):

	for x in fields:
		try:
			value = getattr(self, x)
		except AttributeError:
			continue
		except POSKeyError:
			logger.exception("Could not get attribute %s for object %s", x, self)
			continue

		if value is not None:
			value = converter(value)
			if value is not None:
				result[ext_name] = value
				return value

	# Nothing. Can we adapt it?
	if sup_iface is not None and sup_fields:
		self = sup_iface(self, None)
		if self is not None:
			return _choose_field(result, self, ext_name,
								 converter=sup_converter, fields=sup_fields)

def to_standard_external_last_modified_time( context, default=None, _write_into=None ):
	"""
	Find and return a number representing the time since the epoch
	in fractional seconds at which the ``context`` was last modified.
	This is the same value that is used by :func:`to_standard_external_dictionary`,
	and takes into account whether something is :class:`nti.dataserver.interfaces.ILastModified`
	or :class:`zope.dublincore.interfaces.IDCTimes`.

	:return: A number if it can be found, or the value of ``default``
	"""
	# The _write_into argument is for the benefit of to_standard_external_dictionary
	holder = _write_into if _write_into is not None else dict()

	_choose_field( holder, context, StandardExternalFields_LAST_MODIFIED,
				   fields=(StandardInternalFields_LAST_MODIFIED, StandardInternalFields_LAST_MODIFIEDU),
				   sup_iface=dub_interfaces.IDCTimes, sup_fields=('modified',), sup_converter=_datetime_to_epoch)
	return holder.get( StandardExternalFields_LAST_MODIFIED, default)

def to_standard_external_created_time( context, default=None, _write_into=None ):
	"""
	Find and return a number representing the time since the epoch
	in fractional seconds at which the ``context`` was created.
	This is the same value that is used by :func:`to_standard_external_dictionary`,
	and takes into account whether something is :class:`nti.dataserver.interfaces.ILastModified`
	or :class:`zope.dublincore.interfaces.IDCTimes`.

	:return: A number if it can be found, or the value of ``default``
	"""
	# The _write_into argument is for the benefit of to_standard_external_dictionary
	holder = _write_into if _write_into is not None else dict()

	_choose_field( holder, context, StandardExternalFields_CREATED_TIME,
				   fields=(StandardInternalFields_CREATED_TIME,),
				   sup_iface=dub_interfaces.IDCTimes, sup_fields=('created',), sup_converter=_datetime_to_epoch)

	return holder.get( StandardExternalFields_CREATED_TIME, default )


def _ext_class_if_needed(self, result):
	if StandardExternalFields_CLASS in result:
		return

	cls = getattr(self, '__external_class_name__', None)
	if cls:
		result[StandardExternalFields_CLASS] = cls
	elif (not self.__class__.__name__.startswith('_')
		  and self.__class__.__module__ not in ( 'nti.externalization',
												 'nti.externalization.datastructures',
												 'nti.externalization.persistence',
												 'nti.externalization.interfaces' )):
		result[StandardExternalFields_CLASS] = self.__class__.__name__

from pyramid.threadlocal import get_current_request # XXX Layer violation

def to_standard_external_dictionary( self, mergeFrom=None, name=_NotGiven,
									 registry=component, decorate=True,
									 request=_NotGiven):
	"""
	Returns a dictionary representing the standard externalization of
	the object. This impl takes care of the standard attributes
	including OID (from :attr:`~persistent.interfaces.IPersistent._p_oid`) and ID (from ``self.id`` if defined)
	and Creator (from ``self.creator``).

	If the object has any
	:class:`~nti.externalization.interfaces.IExternalMappingDecorator`
	subscribers registered for it, they will be called to decorate the
	result of this method before it returns ( *unless* `decorate` is set to
	False; only do this if you know what you are doing! )

	:param dict mergeFrom: For convenience, if ``mergeFrom`` is not None, then those values will
		be added to the dictionary created by this method. The keys and
		values in ``mergeFrom`` should already be external.
	"""
	result = LocatedExternalDict()

	if mergeFrom:
		result.update( mergeFrom )

	if request is _NotGiven:
		request = get_current_request()

	result_id = _choose_field( result, self, StandardExternalFields_ID,
							fields=(StandardInternalFields_ID, StandardExternalFields_ID) )
	# As we transition over to structured IDs that contain OIDs, we'll try to use that
	# for both the ID and OID portions
	if ntiids.is_ntiid_of_type( result_id, ntiids.TYPE_OID ):
		# If we are trying to use OIDs as IDs, it's possible that the
		# ids are in the old, version 1 format, without an intid component. If that's the case,
		# then update them on the fly, but only for notes because odd things happen to other
		# objects (chat rooms?) if we do this to them
		if self.__class__.__name__ == 'Note':
			result_id = result[StandardExternalFields_ID]
			std_oid = to_external_ntiid_oid( self )
			if std_oid and std_oid.startswith( result_id ):
				result[StandardExternalFields_ID] = std_oid
		result[StandardExternalFields_OID] = result[StandardExternalFields_ID]
	else:
		oid = to_external_ntiid_oid( self, default_oid=None ) #toExternalOID( self )
		if oid:
			result[StandardExternalFields_OID] = oid

	_choose_field( result, self, StandardExternalFields_CREATOR,
				   fields=(StandardInternalFields_CREATOR, StandardExternalFields_CREATOR),
				   converter=unicode )

	to_standard_external_last_modified_time( self, _write_into=result )
	to_standard_external_created_time( self, _write_into=result )

	_ext_class_if_needed(self, result)

	_choose_field( result, self, StandardExternalFields_CONTAINER_ID,
				   fields=(StandardInternalFields_CONTAINER_ID,) )
	try:
		_choose_field( result, self, StandardExternalFields_NTIID,
					   fields=(StandardInternalFields_NTIID, StandardExternalFields_NTIID) )
		# During the transition, if there is not an NTIID, but we can find one as the ID or OID,
		# provide that
		if StandardExternalFields_NTIID not in result:
			for field in (StandardExternalFields_ID, StandardExternalFields_OID):
				if ntiids.is_valid_ntiid_string( result.get( field ) ):
					result[StandardExternalFields_NTIID] = result[field]
					break
	except ntiids.InvalidNTIIDError:
		logger.exception( "Failed to get NTIID for object %s", type(self) ) # printing self probably wants to externalize


	if decorate:
		decorate_external_mapping( self, result, registry=registry, request=request )

	return result

def decorate_external_mapping( self, result, registry=component, request=_NotGiven ):
	for decorator in registry.subscribers( (self,), IExternalMappingDecorator ):
		decorator.decorateExternalMapping( self, result )

	if request is _NotGiven:
		request = get_current_request()

	if request is not None:
		for decorator in registry.subscribers( (self, request), IExternalMappingDecorator ):
			decorator.decorateExternalMapping( self, result )

toExternalDictionary = to_standard_external_dictionary
deprecation.deprecated('toExternalDictionary', 'Prefer to_standard_external_dictionary' )

def to_minimal_standard_external_dictionary( self, mergeFrom=None, **kwargs ):
	"Does no decoration. Useful for non-'object' types. `self` should have a `mime_type` field."

	result = LocatedExternalDict()
	if mergeFrom:
		result.update( mergeFrom )
	_ext_class_if_needed(self, result)

	mime_type = getattr( self, 'mime_type', None )
	if mime_type:
		result[StandardExternalFields_MIMETYPE] = mime_type
	return result

# Things that have moved
import zope.deferredimport
zope.deferredimport.initialize()
zope.deferredimport.deprecatedFrom(
	"Import from .persistence",
	"nti.externalization.persistence",
	"NoPickle" )

EXT_FORMAT_JSON = 'json' #: Constant requesting JSON format data
EXT_FORMAT_PLIST = 'plist' #: Constant requesting PList (XML) format data

zope.deferredimport.deprecatedFrom(
	"Import from .representation",
	"nti.externalization.representation",
	"to_external_representation",
	"to_json_representation",
	"to_json_representation_externalized",
	"make_repr",
	"WithRepr")
