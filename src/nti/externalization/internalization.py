#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Functions for taking externalized objects and creating application
model objects.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import sys
import inspect
import numbers
import collections

from zope import component
from zope import interface

from zope.dottedname.resolve import resolve

from zope.event import notify as _zope_event_notify

from zope.lifecycleevent import Attributes

from zope.schema.interfaces import IField
from zope.schema.interfaces import WrongType
from zope.schema.interfaces import IFromUnicode
from zope.schema.interfaces import ValidationError
from zope.schema.interfaces import SchemaNotProvided
from zope.schema.interfaces import WrongContainedType

from persistent.interfaces import IPersistent

from .interfaces import IFactory
from .interfaces import IMimeObjectFactory
from .interfaces import IClassObjectFactory
from .interfaces import IInternalObjectUpdater
from .interfaces import StandardExternalFields
from .interfaces import IExternalReferenceResolver
from .interfaces import ObjectModifiedFromExternalEvent
from .interfaces import IExternalizedObjectFactoryFinder

LEGACY_FACTORY_SEARCH_MODULES = set()

StandardExternalFields_CLASS = StandardExternalFields.CLASS
StandardExternalFields_MIMETYPE = StandardExternalFields.MIMETYPE

def register_legacy_search_module( module_name ):
	"""
	The legacy creation search routines will use the modules
	registered by this method.
	"""
	if module_name:
		LEGACY_FACTORY_SEARCH_MODULES.add( module_name )

_EMPTY_DICT = {}
def _find_class_in_dict( className, mod_dict ):
	clazz = mod_dict.get( className )
	if not clazz and className.lower() == className:
		# case-insensitive search of loaded modules if it was lower case.
		for k in mod_dict:
			if k.lower() == className:
				clazz = mod_dict[k]
				break
	return clazz if getattr( clazz, '__external_can_create__', False ) else None

def _search_for_external_factory( typeName, search_set=None ):
	"""
	Deprecated, legacy functionality. Given the name of a type, optionally ending in 's' for
	plural, attempt to locate that type.
	"""
	if not typeName:
		return None

	if search_set is None:
		search_set = LEGACY_FACTORY_SEARCH_MODULES

	className = typeName[0:-1] if typeName.endswith('s') else typeName
	result = None

	for module_name in search_set:
		# Support registering both names and actual module objects
		mod_dict = getattr( module_name, '__dict__', None )
		module = sys.modules.get( module_name ) if mod_dict is None else module_name
		if module is None:
			try:
				module = resolve( module_name )
			except (AttributeError,ImportError):
				# This is a programming error, so that's why we log it
				logger.exception( "Failed to resolve legacy factory search module %s", module_name )

		result = _find_class_in_dict(className, 
									 getattr( module, '__dict__', _EMPTY_DICT ) if mod_dict is None else mod_dict)
		if result:
			break

	return result

@interface.implementer(IFactory)
def default_externalized_object_factory_finder( externalized_object ):
	factory = None
	# We use specialized interfaces instead of plain IFactory to make it clear
	# that these are being created from external data
	try:
		if StandardExternalFields_MIMETYPE in externalized_object:
			factory = component.queryAdapter( externalized_object, IMimeObjectFactory,
											  name=externalized_object[StandardExternalFields_MIMETYPE] )
			if not factory:
				# What about a named utility?
				factory = component.queryUtility( IMimeObjectFactory,
												  name=externalized_object[StandardExternalFields_MIMETYPE] )

			if not factory:
				# Is there a default?
				factory = component.queryAdapter( externalized_object, IMimeObjectFactory )


		if not factory and StandardExternalFields_CLASS in externalized_object:
			class_name = externalized_object[StandardExternalFields_CLASS]
			factory = component.queryAdapter( externalized_object, IClassObjectFactory,
											  name=class_name )
			if not factory:
				factory = find_factory_for_class_name( class_name )
	except (TypeError,KeyError):
		return None

	return factory

default_externalized_object_factory_finder.find_factory = default_externalized_object_factory_finder

@interface.implementer(IExternalizedObjectFactoryFinder)
def default_externalized_object_factory_finder_factory( externalized_object ):
	return default_externalized_object_factory_finder

def find_factory_for_class_name( class_name ):
	factory = component.queryUtility( IClassObjectFactory,
									  name=class_name )
	if not factory:
		factory = _search_for_external_factory( class_name )
	# Did we chop off an extra 's'?
	if not factory and class_name and class_name.endswith( 's' ):
		factory = _search_for_external_factory( class_name + 's' )
	return factory

def find_factory_for( externalized_object, registry=component ):
	"""
	Given a :class:`IExternalizedObject`, locate and return a factory
	to produce a Python object to hold its contents.
	"""
	factory_finder = registry.getAdapter( externalized_object, IExternalizedObjectFactoryFinder )

	return factory_finder.find_factory(externalized_object)

def _resolve_externals(object_io, updating_object, externalObject,
					   registry=component, context=None ):
	# Run the resolution steps on the external object

	for keyPath in getattr( object_io, '__external_oids__', () ):
		# TODO: This version is very simple, generalize it
		if keyPath not in externalObject:
			continue
		externalObjectOid = externalObject.get( keyPath )
		unwrap = False
		if not isinstance( externalObjectOid, collections.MutableSequence ):
			externalObjectOid = [externalObjectOid,]
			unwrap = True

		for i in range(0,len(externalObjectOid)):
			resolver = registry.queryMultiAdapter( (updating_object,externalObjectOid[i]),
												   IExternalReferenceResolver )
			if resolver:
				externalObjectOid[i] = resolver.resolve( externalObjectOid[i] )
		if unwrap and keyPath in externalObject: # Only put it in if it was there to start with
			externalObject[keyPath] = externalObjectOid[0]


	for ext_key, resolver_func in getattr( object_io, '__external_resolvers__', {} ).iteritems():
		if not externalObject.get( ext_key ):
			continue
		# classmethods and static methods are implemented with descriptors,
		# which don't work when accessed through the dictionary in this way,
		# so we special case it so instances don't have to.
		if isinstance( resolver_func, classmethod ) or isinstance( resolver_func, staticmethod ):
			resolver_func = resolver_func.__get__( None, object_io.__class__ )
		elif len( inspect.getargspec( resolver_func )[0] ) == 4: # instance method
			_resolver_func = resolver_func
			resolver_func = lambda x, y, z: _resolver_func( object_io, x, y, z )

		externalObject[ext_key] = resolver_func( context, externalObject, externalObject[ext_key] )

# Things we don't bother trying to internalize
_primitives = six.string_types + (numbers.Number,bool)

def _object_hook( k, v, x ):
	return v

def _recall( k, obj, ext_obj, kwargs ):
	obj = update_from_external_object( obj, ext_obj, **kwargs )
	obj = kwargs['object_hook']( k, obj, ext_obj )
	if IPersistent.providedBy( obj ):
		obj._v_updated_from_external_source = ext_obj
	return obj

def update_from_external_object( containedObject, externalObject,
								 registry=component, context=None,
								 require_updater=False,
								 notify=True, object_hook=_object_hook ):
	"""
	Central method for updating objects from external values.

	:param containedObject: The object to update.
	:param externalObject: The object (typically a mapping or sequence) to update
		the object from. Usually this is obtained by parsing an external
		format like JSON.
	:param context: An object passed to the update methods.
	:param require_updater: If True (not the default) an exception will be raised
		if no implementation of :class:`~nti.externalization.interfaces.IInternalObjectUpdater` can be found
		for the `containedObject.`
	:param bool notify: If ``True`` (the default), then if the updater for the `containedObject` either has no preference
		(returns None) or indicates that the object has changed,
		then an :class:`~nti.externalization.interfaces.IObjectModifiedFromExternalEvent` will be fired. This may
		be a recursive process so a top-level call to this object may spawn
		multiple events. The events that are fired will have a ``descriptions`` list containing
		one or more :class:`~zope.lifecycleevent.interfaces.IAttributes` each with
		``attributes`` for each attribute we modify (assuming that the keys in the ``externalObject``
		map one-to-one to an attribute; if this is the case and we can also find an interface
		declaring the attribute, then the ``IAttributes`` will have the right value for ``interface``
		as well).
	:param callable object_hook: If given, called with the results of every nested object
		as it has been updated. The return value will be used instead of the nested object.
		Signature ``f(k,v,x)`` where ``k`` is either the key name, or None in the case of a sequence,
		``v`` is the newly-updated value, and ``x`` is the external object used to update ``v``.

	:return: `containedObject` after updates from `externalObject`
	"""

	kwargs = dict(registry=registry, 
				  context=context, 
				  require_updater=require_updater, 
				  notify=notify, 
				  object_hook=object_hook)

	# Parse any contained objects
	# TODO: We're (deliberately?) not actually updating any contained
	# objects, we're replacing them. Is that right? We could check OIDs...
	# If we decide that's right, then the internals could be simplified by
	# splitting the two parts
	# TODO: Schema validation
	# TODO: Should the current user impact on this process?

	# Sequences do not represent python types, they represent collections of
	# python types
	if isinstance( externalObject, collections.MutableSequence ):
		tmp = []
		for i in externalObject:
			factory = find_factory_for( i, registry=registry )
			tmp.append( _recall( None, factory(), i, kwargs ) if factory else i )
		return tmp

	assert isinstance( externalObject, collections.MutableMapping )
	# We have to save the list of keys, it's common that they get popped during the update
	# process, and then we have no descriptions to send
	external_keys = list()
	for k, v in externalObject.iteritems():
		external_keys.append( k )
		if isinstance( v, _primitives ):
			continue

		if isinstance( v, collections.MutableSequence ):
			# Update the sequence in-place
			__traceback_info__ = k, v
			v = _recall( k, (), v, kwargs )
			externalObject[k] = v
		else:
			factory = find_factory_for( v, registry=registry )
			externalObject[k] = _recall( k, factory(), v, kwargs ) if factory else v

	updater = None
	if 	hasattr( containedObject, 'updateFromExternalObject' ) and \
		not getattr( containedObject, '__ext_ignore_updateFromExternalObject__', False ):
		# legacy support. The __ext_ignore_updateFromExternalObject__ allows a transitition to an adapter
		# without changing existing callers and without triggering infinite recursion
		updater = containedObject
	else:
		if require_updater:
			get = registry.getAdapter
		else:
			get = registry.queryAdapter

		updater = get( containedObject, IInternalObjectUpdater )

	if updater is not None:
		# Let the updater resolve externals too
		_resolve_externals( updater, containedObject, externalObject, 
							registry=registry, context=context )

		updated = None
		# The signature may vary.
		argspec = inspect.getargspec( updater.updateFromExternalObject )
		if 'context' in argspec.args or (argspec.keywords and 'dataserver' not in argspec.args):
			updated = updater.updateFromExternalObject( externalObject, context=context )
		elif argspec.keywords or 'dataserver' in argspec.args:
			updated = updater.updateFromExternalObject( externalObject, dataserver=context )
		else:
			updated = updater.updateFromExternalObject( externalObject )

		# Broadcast a modified event if the object seems to have changed.
		if notify and (updated is None or updated):
			# TODO: We need to try to find the actual interfaces and fields to allow correct
			# decisions to be made at higher levels.
			# zope.formlib.form.applyData does this because it has a specific, configured mapping. We
			# just do the best we can by looking at what's implemented. The most specific
			# interface wins
			descriptions = collections.defaultdict(list) # map from interface class to list of keys
			provides = interface.providedBy( containedObject )
			for k in external_keys:
				iface_providing_attr = None
				iface_attr = provides.get( k )
				if iface_attr:
					iface_providing_attr = iface_attr.interface
				descriptions[iface_providing_attr].append( k )
			attributes = [Attributes(iface, *keys) for iface, keys in descriptions.items()]
			event = ObjectModifiedFromExternalEvent( containedObject, *attributes )
			event.external_value = externalObject
			# Let the updater have its shot at modifying the event, too, adding
			# interfaces or attributes. (Note: this was added to be able to provide
			# sharedWith information on the event, since that makes for a better stream.
			# If that use case expands, revisit this interface
			try:
				meth = updater._ext_adjust_modified_event
			except AttributeError:
				pass
			else:
				event = meth( event )
			_zope_event_notify( event )

	return containedObject

def validate_field_value( self, field_name, field, value ):
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
	field = field.bind( self )
	try:
		if isinstance(value, unicode) and IFromUnicode.providedBy( field ):
			value = field.fromUnicode( value ) # implies validation
		else:
			field.validate( value )
	except SchemaNotProvided as e:
		# The object doesn't implement the required interface.
		# Can we adapt the provided object to the desired interface?
		# First, capture the details so we can reraise if needed
		exc_info = sys.exc_info()
		if not e.args: # zope.schema doesn't fill in the details, which sucks
			e.args = (field_name,field.schema)

		try:
			value = field.schema( value )
			field.validate( value )
		except (LookupError,TypeError, ValidationError):
			# Nope. TypeError means we couldn't adapt, and a
			# validation error means we could adapt, but it still wasn't
			# right. Raise the original SchemaValidationError.
			raise exc_info[0], exc_info[1], exc_info[2]
	except WrongType as e:
		# Like SchemaNotProvided, but for a primitive type,
		# most commonly a date
		# Can we adapt?
		if len(e.args) != 3:
			raise
		exc_info = sys.exc_info()
		exp_type = e.args[1]
		# If the type unambiguously implements an interface (one interface)
		# that's our target. IDate does this
		if len( list(interface.implementedBy( exp_type )) ) != 1:
			raise
		schema = list(interface.implementedBy(exp_type))[0]
		try:
			value = component.getAdapter( value, schema )
		except (LookupError,TypeError):
			# No registered adapter, darn
			raise exc_info[0], exc_info[1], exc_info[2]
		except ValidationError as e:
			# Found an adapter, but it does its own validation,
			# and that validation failed (eg, IDate below)
			# This is still a more useful error than WrongType,
			# so go with it after ensuring it has a field
			e.field = field
			raise

		# Lets try again with the adapted value
		return validate_field_value( self, field_name, field, value )

	except WrongContainedType as e:
		# We failed to set a sequence. This would be of simple (non externalized)
		# types.
		# Try to adapt each value to what the sequence wants, just as above,
		# if the error is one that may be solved via simple adaptation
		# TODO: This is also thrown from IObject fields when validating the fields of the object
		exc_info = sys.exc_info()
		if not e.args or not all( (isinstance(x, SchemaNotProvided) for x in e.args[0] ) ):
			raise

		# IObject provides `schema`, which is an interface, so we can adapt
		# using it. Some other things do not, for example nti.schema.field.Variant
		# They might provide a `fromObject` function to do the conversion
		# The field may be able to handle the whole thing by itself or we may need
		# to do the individual objects

		converter = lambda x: x
		loop = True
		if hasattr( field, 'fromObject' ):
			converter = field.fromObject
			loop = False
		elif hasattr( field.value_type, 'fromObject' ):
			converter = field.value_type.fromObject
		elif hasattr( field.value_type, 'schema' ):
			converter = field.value_type.schema
		try:
			value = [converter( v ) for v in value] if loop else converter(value)
		except TypeError:
			# TypeError means we couldn't adapt, in which case we want
			# to raise the original error. If we could adapt,
			# but the converter does its own validation (e.g., fromObject)
			# then we want to let that validation error rise
			raise exc_info[0], exc_info[1], exc_info[2]

		# Now try to set the converted value
		try:
			field.validate( value )
		except ValidationError:
			# Nope. TypeError means we couldn't adapt, and a
			# validation error means we could adapt, but it still wasn't
			# right. Raise the original SchemaValidationError.
			raise exc_info[0], exc_info[1], exc_info[2]

	if (field.readonly
		and field.get(self) is None
		and field.queryTaggedValue('_ext_allow_initial_set')):
		if value is not None:
			# First time through we get to set it, but we must bypass
			# the field
			def _do_set():
				setattr(self, str(field_name), value)
		else:
			def _do_set():
				# no-op
				return
	else:
		def _do_set():
			return field.set(self, value)

	return _do_set

def validate_named_field_value( self, iface, field_name, value ):
	"""
	Given a :class:`zope.interface.Interface` and the name of one of its attributes,
	validate that the given ``value`` is appropriate to set. See :func:`validate_field_value`
	for details.

	:param string field_name: The name of a field contained in `iface`. May name
		a regular :class:`zope.interface.Attribute`, or a :class:`zope.schema.interfaces.IField`;
		if the latter, extra validation will be possible.

	:return: A callable of no arguments to call to actually set the value.
	"""
	field = iface[field_name]
	if IField.providedBy( field ):
		return validate_field_value( self, field_name, field, value )
	return lambda: setattr( self, field_name, value )
