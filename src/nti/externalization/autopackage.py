#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# If we extend ExtensionClass.Base, __class_init__ is called automatically
# for each subclass. But we also start participating in acquisition, which
# is probably not what we want
# import ExtensionClass

from zope import interface

from zope.dottedname import resolve as dottedname

from zope.mimetype.interfaces import IContentTypeAware

from ZODB.loglevels import TRACE

from .datastructures import ModuleScopedInterfaceObjectIO
from .internalization import register_legacy_search_module

class AutoPackageSearchingScopedInterfaceObjectIO(ModuleScopedInterfaceObjectIO):
	"""
	A special, magic, type of interface-driven input and output, one designed
	for the common use case of a package that provides the common pattern:

	* interfaces.py
	* externalization.py (where a subclass of this object lives)
	* configure.zcml (where the subclass is registered as an adapter for each object;
	* you may also then provide mime-factories as well)
	* other modules, where types are defined for the external interfaces.

	Once you derive from this class and implement the abstract methods, you
	need to call :meth:`__class_init__` (exactly once) on your subclass.
	"""

	@classmethod
	def _ap_compute_external_class_name_from_interface_and_instance( cls, iface, impl ):
		"""
		Assigned as the tagged value __external_class_name__ to each
		interface. This will be called on an instance implementing iface.
		"""
		# Use the __class__, not type(), to work with proxies
		return cls._ap_compute_external_class_name_from_concrete_class( impl.__class__ )

	@classmethod
	def _ap_compute_external_class_name_from_concrete_class( cls, a_type ):
		return getattr( a_type, '__external_class_name__', a_type.__name__ )

	@classmethod
	def _ap_compute_external_mimetype( cls, package_name, a_type, ext_class_name ):
		# 'nti.assessment', FooBar, 'FooBar' => vnd.nextthought.assessment.foobar
		# Recall that mimetypes should be byte strings
		local = package_name.rsplit( '.', 1 )[-1]
		return bytes(b'application/vnd.nextthought.' + local + b'.' + ext_class_name.lower())

	@classmethod
	def _ap_enumerate_externalizable_root_interfaces( cls, interfaces ): # TODO: We can probably do something with this
		raise NotImplementedError()

	@classmethod
	def _ap_enumerate_module_names( cls ):
		raise NotImplementedError()

	@classmethod
	def _ap_find_factories( cls, package_name ):
		class _ClassNameRegistry(object):
			pass
		for mod_name in cls._ap_enumerate_module_names():
			mod = dottedname.resolve( package_name + '.' + mod_name )
			for _, v in mod.__dict__.items():
				# ignore imports and non-concrete classes
				# NOTE: using issubclass to properly support metaclasses
				if getattr( v, '__module__', None) != mod.__name__ or not issubclass( type(v), type ):
					continue
				# implementation_name = k
				implementation_class = v
				# Does this implement something that should be externalizable?
				if any( (iface.queryTaggedValue( '__external_class_name__') for iface in interface.implementedBy(implementation_class)) ):
					ext_class_name = cls._ap_compute_external_class_name_from_concrete_class( implementation_class )

					setattr( _ClassNameRegistry, ext_class_name, implementation_class )

					if not implementation_class.__dict__.get( 'mimeType', None ):
						# NOT hasattr. We don't use hasattr because inheritance would
						# throw us off. It could be something we added, and iteration order
						# is not defined (if we got the subclass first we're good, we fail if we
						# got superclass first).
						# Also, not a simple 'in' check. We want to allow for setting mimeType = None
						# in the dict for static analysis purposes

						# legacy check
						if 'mime_type' in implementation_class.__dict__:
							setattr( implementation_class, 'mimeType', implementation_class.__dict__['mime_type'] )
						else:
							setattr( implementation_class,
									 'mimeType',
									 cls._ap_compute_external_mimetype( package_name, implementation_class, ext_class_name ) )
							setattr( implementation_class, 'mime_type', implementation_class.mimeType )

						if not IContentTypeAware.implementedBy( implementation_class ): # well it does now
							interface.classImplements( implementation_class, IContentTypeAware )

					# Opt in for creating, unless explicitly disallowed
					if not hasattr( implementation_class, '__external_can_create__' ):
						setattr( implementation_class, '__external_can_create__', True )
						# Let them have containers
						if not hasattr( implementation_class, 'containerId' ):
							setattr( implementation_class, 'containerId', None )
		return _ClassNameRegistry

	@classmethod
	def _ap_find_package_name( cls ):
		ext_module_name = cls.__module__
		package_name = ext_module_name.rsplit( '.', 1 )[0]
		return package_name

	@classmethod
	def _ap_find_package_interface_module(cls):
		# First, get the correct working module
		package_name = cls._ap_find_package_name()

		# Now the interfaces
		package_ifaces = dottedname.resolve( package_name + '.interfaces' )
		return package_ifaces

	@classmethod
	def __class_init__( cls ): # ExtensionClass.Base class initializer
		# Do nothing when this class itself is initted
		if cls.__name__ == 'AutoPackageSearchingScopedInterfaceObjectIO' and cls.__module__ == __name__:
			return

		# First, get the correct working module
		package_name = cls._ap_find_package_name()

		# Now the interfaces
		package_ifaces = cls._ap_find_package_interface_module()
		cls._ext_search_module = package_ifaces
		logger.log( TRACE, "Autopackage tagging interfaces in %s", package_ifaces )
		# Now tag them
		for iface in cls._ap_enumerate_externalizable_root_interfaces( package_ifaces ):
			iface.setTaggedValue( '__external_class_name__', cls._ap_compute_external_class_name_from_interface_and_instance )

		# Now find the factories
		factories = cls._ap_find_factories( package_name )
		register_legacy_search_module( factories )
