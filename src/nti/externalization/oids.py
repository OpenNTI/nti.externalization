#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Functions for externalizing OIDs.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import collections
from six import string_types

from zope import component
from zope.security.management import system_user

from zc import intid as zc_intid

from ZODB.interfaces import IConnection

from nti.common.proxy import removeAllProxies

from nti.ntiids import ntiids

from . import integer_strings

def toExternalOID(self, default=None, add_to_connection=False, add_to_intids=False):
	"""
	For a persistent object, returns its persistent OID in a pasreable
	external format (see :func:`fromExternalOID`). If the object has not been saved, and
	`add_to_connection` is `False` (the default) returns the `default`.

	:param add_to_connection: If the object is persistent but not yet added to a
		connection, setting this to true will attempt to add it to the nearest connection
		in its containment tree, thus letting it have an OID.
	:param add_to_intids: If we can obtain an OID for this object, but it does
		not have an intid, and an intid utility is available, then if this is
		``True`` (not the default) we will register it with the utility.

	:return: A :class:`bytes` string.
	"""

	try:
		return self.toExternalOID() or default
	except AttributeError:
		pass

	try:
		# See comments in to_external_ntiid_oid
		return getattr( self, '_v_to_external_oid' )
	except AttributeError:
		pass

	# because if it was proxied, we should still read the right thing above;
	# this saves time
	self = removeAllProxies(self)
	try:
		oid = self._p_oid
	except AttributeError:
		return default

	jar = None
	if not oid:
		if add_to_connection:
			try:
				jar = IConnection(self)
				jar.add( self )
				oid = self._p_oid
			except Exception:
				return default
		else:
			return default

	# The object ID is defined to be 8 charecters long. It gets
	# padded with null chars to get to that length; we strip
	# those out. Finally, it probably has chars that
	# aren't legal in UTF or ASCII, so we go to hex and prepend
	# a flag, '0x'
	# TODO: Why are we keeping this as a bytes string, not unicode?
	oid = oid.lstrip(b'\x00')
	oid = b'0x' + oid.encode('hex')
	try:
		jar = jar or self._p_jar
	except AttributeError:
		pass

	if jar:
		db_name = jar.db().database_name
		oid = oid + b':' + db_name.encode( 'hex' )

	intutility = component.queryUtility( zc_intid.IIntIds )
	if intutility is not None:
		intid = intutility.queryId( self )
		if intid is None and add_to_intids:
			intid = intutility.register( self )
		if intid is not None:
			if not jar:
				oid = oid + b':' # Ensure intid is always the third part
			oid = oid + b':' + integer_strings.to_external_string( intid )

	try:
		setattr( self, str('_v_to_external_oid'), oid )
	except (AttributeError,TypeError):
		pass

	return oid

to_external_oid = toExternalOID

ParsedOID = collections.namedtuple('ParsedOID', ['oid', 'db_name', 'intid'] )

def fromExternalOID(ext_oid):
	"""
	Given a string, as produced by :func:`toExternalOID`, parses it into its
	component parts.


	:param string ext_oid: As produced by :func:`toExternalOID`.

	:return: A three-tuple: ``(oid, dbname, intid)`` (:class:`ParsedOID`). Only the
		OID is guaranteed to be present; the other fields may be empty (``db_name``)
		or `None` (``intid``).

	"""
	# But, for legacy reasons, we accept directly the bytes given
	# in _p_oid, so we have to be careful with our literals here
	# to avoid Unicode[en|de]codeError
	__traceback_info__ = ext_oid
	# Sometimes raw _p_oid values do contain a b':', so simply splitting
	# on that is not reliable, so try to detect raw _p_oid directly
	if 	isinstance(ext_oid, bytes) and len(ext_oid) == 8 and \
		not ext_oid.startswith(b'0x') and ext_oid.count(b':') != 2:
		# The last conditions might be overkill, but toExternalOID is actually
		# returning bytes, and it could conceivably be exactly 8 chars long;
		# however, a raw oid could also start with the two chars 0x and contain two colons
		# so the format is a bit ambiguous...
		return ParsedOID( ext_oid, '', None )

	parts = ext_oid.split( b':' ) if b':' in ext_oid else (ext_oid,)
	oid_string = parts[0]
	name_s = parts[1] if len(parts) > 1 else b""
	intid_s = str(parts[2]) if len(parts) > 2 else None

	# Translate the external format if needed
	if oid_string.startswith( b'0x' ):
		oid_string = oid_string[2:].decode( 'hex' )
		name_s = name_s.decode( 'hex' )
	# Recall that oids are padded to 8 with \x00
	oid_string = oid_string.rjust( 8, b'\x00' )
	__traceback_info__ = ext_oid, oid_string, name_s, intid_s
	if intid_s is not None:
		intid = integer_strings.from_external_string( intid_s )
	else:
		intid = None

	return ParsedOID( oid_string, name_s, intid )

from_external_oid = fromExternalOID

MASKED_EXTERNAL_CREATOR = 'unknown'
DEFAULT_EXTERNAL_CREATOR = system_user.id

def to_external_ntiid_oid(contained, default_oid=None,
						  add_to_connection=False,
						  add_to_intids=False,
						  mask_creator=False):
	"""
	:return: An NTIID string utilizing the object's creator and persistent
		id.
	:param str default_oid: The default value for the externalization of the OID.
		If this is ``None`` (the default), and no external OID can be found
		(using :func:`toExternalOID`), then this function will return None.
	:param add_to_connection: If the object is persistent but not yet added to a
		connection, setting this to true will attempt to add it to the nearest
		connection in its containment tree, thus letting it have an OID.
	:keyword bool mask_creator: If true (not the default), then the actual
		creator of the object will not be present in the NTIID string.
	"""

	__traceback_info__ = type(contained)

	if callable( getattr( contained, 'to_external_ntiid_oid', None ) ):
		return contained.to_external_ntiid_oid()

	# We really want the external OID, but for those weird time we may not be saved we'll
	# allow the ID of the object, unless we are explicitly overridden
	contained = removeAllProxies( contained )

	# By definition, these are persistent.Persistent objects, so a _v_ attribute
	# is going to be volatile and thread-local (or nearly). If the object cache
	# is in use, the worst that can happen is that the third part of the OID
	# is/not around for longer/less long than otherwise. (Which could potentially differ
	# from one worker to the next).
	# On large renderings, benchmarks show this can be worth ~10%
	cache_key = str('_v_to_external_ntiid_oid_%s' % mask_creator)
	ext_oid = getattr( contained, cache_key, None)
	if ext_oid:
		return ext_oid

	oid = toExternalOID( contained,
						 default=default_oid,
						 add_to_connection=add_to_connection,
						 add_to_intids=add_to_intids)
	if not oid:
		return None

	if mask_creator:
		creator = MASKED_EXTERNAL_CREATOR
	else:
		creator = getattr( contained, 'creator', DEFAULT_EXTERNAL_CREATOR )

	ext_oid = ntiids.make_ntiid(provider=(creator
										   if isinstance(creator, string_types)
										   else getattr(creator, 'username', DEFAULT_EXTERNAL_CREATOR)),
								specific=oid,
								nttype=ntiids.TYPE_OID)
	try:
		setattr(contained, cache_key, ext_oid)
	except (AttributeError,TypeError): # TypeError is a BrokenModified
		pass
	return ext_oid
