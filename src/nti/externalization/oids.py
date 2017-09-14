#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Functions for externalizing OIDs.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import binascii
import collections

from zope import component

from zope.intid.interfaces import IIntIds

from ZODB.interfaces import IConnection

from nti.externalization._compat import bytes_
from nti.externalization._compat import native_

from nti.externalization.integer_strings import to_external_string
from nti.externalization.integer_strings import from_external_string

from nti.externalization.proxy import removeAllProxies


def toExternalOID(self, default=None, add_to_connection=False,
                  add_to_intids=False, use_cache=True):
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

    if use_cache:
        try:
            # See comments in to_external_ntiid_oid
            return getattr(self, '_v_to_external_oid')
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
                jar.add(self)
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
    oid = b'0x' + binascii.hexlify(oid)
    try:
        jar = jar or self._p_jar
    except AttributeError:
        pass

    if jar:
        db_name = jar.db().database_name
        oid = oid + b':' + binascii.hexlify(bytes_(db_name))
    intutility = component.queryUtility(IIntIds)
    if intutility is not None:
        intid = intutility.queryId(self)
        if intid is None and add_to_intids:
            intid = intutility.register(self)
        if intid is not None:
            if not jar:
                oid = oid + b':'  # Ensure intid is always the third part
            oid = oid + b':' + bytes_(to_external_string(intid))

    try:
        setattr(self, str('_v_to_external_oid'), oid)
    except (AttributeError, TypeError):
        pass
    return oid
to_external_oid = toExternalOID

ParsedOID = collections.namedtuple('ParsedOID', ['oid', 'db_name', 'intid'])


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
    if      isinstance(ext_oid, bytes) and len(ext_oid) == 8 and \
        not ext_oid.startswith(b'0x') and ext_oid.count(b':') != 2:
        # The last conditions might be overkill, but toExternalOID is actually
        # returning bytes, and it could conceivably be exactly 8 chars long;
        # however, a raw oid could also start with the two chars 0x and contain two colons
        # so the format is a bit ambiguous...
        return ParsedOID(ext_oid, '', None)

    ext_oid = bytes_(ext_oid) if not isinstance(ext_oid, bytes) else ext_oid
    parts = ext_oid.split(b':') if b':' in ext_oid else (ext_oid,)
    oid_string = parts[0]
    name_s = parts[1] if len(parts) > 1 else b""
    intid_s = native_(parts[2]) if len(parts) > 2 else None

    # Translate the external format if needed
    if oid_string.startswith(b'0x'):
        oid_string = binascii.unhexlify(oid_string[2:])
        name_s = binascii.unhexlify(name_s)
    # Recall that oids are padded to 8 with \x00
    oid_string = oid_string.rjust(8, b'\x00')
    __traceback_info__ = ext_oid, oid_string, name_s, intid_s
    if intid_s is not None:
        intid = from_external_string(intid_s)
    else:
        intid = None

    return ParsedOID(oid_string, name_s, intid)
from_external_oid = fromExternalOID


# Things that have moved
import zope.deferredimport
zope.deferredimport.initialize()
zope.deferredimport.deprecatedFrom(
    "Import from nti.ntiids.oids",
    "nti.ntiids.oids",
    "MASKED_EXTERNAL_CREATOR",
    "DEFAULT_EXTERNAL_CREATOR",
    "to_external_ntiid_oid")
