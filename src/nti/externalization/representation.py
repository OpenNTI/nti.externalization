#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
External representation support.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import collections

from zope import interface
from zope import component

from .interfaces import EXT_REPR_JSON
from .interfaces import EXT_REPR_YAML
from .interfaces import EXT_REPR_PLIST

from .interfaces import IExternalObjectIO
from .interfaces import IExternalObjectRepresenter

from .externalization import _NotGiven
from .externalization import toExternalObject

###
# Driver functions
###

def to_external_representation( obj, ext_format=EXT_REPR_JSON,
								name=_NotGiven, registry=component ):
	"""
	Transforms (and returns) the `obj` into its external (string) representation.

	:param ext_format: One of :const:`EXT_FORMAT_JSON` or :const:`EXT_FORMAT_PLIST`.
	"""
	# It would seem nice to be able to do this in one step during
	# the externalization process itself, but we would wind up traversing
	# parts of the datastructure more than necessary. Here we traverse
	# the whole thing exactly twice.
	ext = toExternalObject( obj, name=name, registry=registry )

	return registry.getUtility(IExternalObjectRepresenter, name=ext_format).dump(ext)


def to_json_representation( obj ):
	"""
	A convenience function that calls
	:func:`to_external_representation` with :data:`EXT_REPR_JSON`.
	"""
	return to_external_representation( obj, EXT_REPR_JSON )

###
# Plist
###

import plistlib

@interface.implementer(IExternalObjectRepresenter)
@interface.named(EXT_REPR_PLIST)
class PlistRepresenter(object):

	def stripNoneFromExternal(self, obj ):
		""" Given an already externalized object, strips ``None`` values. """
		if isinstance( obj, list ) or isinstance(obj, tuple):
			obj = [self.stripNoneFromExternal(x) for x in obj if x is not None]
		elif isinstance( obj, collections.Mapping ):
			obj = {k: self.stripNoneFromExternal(v)
				   for k,v in obj.iteritems()
				   if v is not None and k is not None}
		return obj


	def dump(self, obj, fp=None ):
		ext = self.stripNoneFromExternal( obj )
		if fp is not None:
			plistlib.writePlist(ext, fp)
		else:
			return plistlib.writePlistToString(ext)


###
# JSON
###

import simplejson

def _second_pass_to_external_object( obj ):
	result = toExternalObject( obj, name='second-pass' )
	if result is obj:
		raise TypeError(repr(obj) + " is not JSON serializable")
	return result

@interface.implementer(IExternalObjectIO)
@interface.named(EXT_REPR_JSON)
class JsonRepresenter(object):

	_DUMP_ARGS = dict(check_circular=False,
					  sort_keys=__debug__, # Makes testing easier
					  default=_second_pass_to_external_object )


	def dump(self, obj, fp=None):
		"""
		Given an object that is known to already be in an externalized form,
		convert it to JSON. This can be about 10% faster then requiring a pass
		across all the sub-objects of the object to check that they are in external
		form, while still handling a few corner cases with a second-pass conversion.
		(These things creep in during the object decorator phase and are usually
		links.)
		"""
		if fp:
			simplejson.dump(obj, fp, **self._DUMP_ARGS)
		else:
			return simplejson.dumps( obj, **self._DUMP_ARGS )

	def load(self, stream):
		# We need all string values to be unicode objects. simplejson (the usual implementation
		# we get from anyjson) is different from the built-in json and returns strings
		# that can be represented as ascii as str objects if the input was a bytestring.
		# The only way to get it to return unicode is if the input is unicode, or
		# to use a hook to do so incrementally. The hook saves allocating the entire request body
		# as a unicode string in memory and is marginally faster in some cases. However,
		# the hooks gets to be complicated if it correctly catches everything (inside arrays,
		# for example; the function below misses them) so decoding to unicode up front
		# is simpler
		#def _read_body_strings_unicode(pairs):
		#	return dict( ( (k, (unicode(v, request.charset) if isinstance(v, str) else v))
		#				   for k, v
		#				   in pairs) )

		if isinstance(stream, bytes):
			stream = stream.decode('utf-8')

		value = simplejson.loads(stream)

		# Depending on whether the simplejson C speedups are active, we can still
		# get back a non-unicode string if the object was a naked string. (If the python
		# version is used, it returns unicode; the C version returns str.)
		if isinstance( value, str ):
			value = unicode(value, 'utf-8') # we know it's simple ascii or it would have produced unicode

		return value

to_json_representation_externalized = JsonRepresenter().dump

###
# YAML
###

import yaml

class _ExtDumper(yaml.SafeDumper): #pylint:disable=R0904
	"""
	We want to represent all of our special object types,
	like LocatedExternalList/Dict and the ContentFragment subtypes,
	as plain yaml data structures.

	Therefore we must register their base types as multi-representers.
	"""

_ExtDumper.add_multi_representer(list, _ExtDumper.represent_list)
_ExtDumper.add_multi_representer(dict, _ExtDumper.represent_dict)
_ExtDumper.add_multi_representer(unicode, _ExtDumper.represent_unicode)

class _UnicodeLoader(yaml.SafeLoader):  #pylint:disable=R0904

	def construct_yaml_str(self, node):
		# yaml defines strings to be unicode, but
		# the default reader encodes anything that can be
		# represented as ASCII back to bytes. We don't
		# want that.
		return self.construct_scalar(node)

_UnicodeLoader.add_constructor('tag:yaml.org,2002:str',
							   _UnicodeLoader.construct_yaml_str)

@interface.implementer(IExternalObjectIO)
@interface.named(EXT_REPR_YAML)
class YamlRepresenter(object):

	def dump(self, obj, fp=None):
		return yaml.dump(obj, stream=fp, Dumper=_ExtDumper)

	def load(self, stream):
		return yaml.load(stream, Loader=_UnicodeLoader)

###
# Misc
###

from ZODB.POSException import ConnectionStateError

def make_repr(default=None):
	if default is None:
		default = lambda self: "%s().__dict__.update( %s )" % (self.__class__.__name__, self.__dict__ )
	def __repr__( self ):
		try:
			return default(self)
		except ConnectionStateError:
			return '%s(Ghost)' % self.__class__.__name__
		except (ValueError,LookupError) as e: # Things like invalid NTIID, missing registrations
			return '%s(%s)' % (self.__class__.__name__, e)
	return __repr__

def WithRepr(default=object()):
	"""
	A class decorator factory to give a __repr__ to
	the object. Useful for persistent objects.

	:keyword default: A callable to be used for the default value.
	"""

	# If we get one argument that is a type, we were
	# called bare (@WithRepr), so decorate the type
	if isinstance(default, type):
		default.__repr__ = make_repr()
		return default

	# If we got None or anything else, we were called as a factory,
	# so return a decorator
	def d(cls):
		cls.__repr__ = make_repr()
		return cls
	return d
