#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Functions to represent potentially large integers as the shortest
possible human-readable and writable strings. The motivation is to be
able to take int ids as produced by an :class:`zc.intid.IIntId`
utility and produce something that can be written down and typed in by
a human. To this end, the strings produced have to be:

* One-to-one and onto the integer domain;
* As short as possible;
* While not being easily confused;
* Or accidentaly permuted

To meet those goals, we define an alphabet consisting of the ASCII
digits and upper and lowercase letters, leaving out troublesome pairs
(zero and upper and lower oh and upper queue, one and upper and lower
ell) (actually, those troublesome pairs will all map to the same
character).

We also put a version marker at the end of the string so we can evolve
this algorithm gracefully but still honor codes in the wild.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import string

# In the first version of the protocol, the version marker, which would
# come at the end, is always omitted. Subsequent versions will append
# a value that cannot be produced from the _VOCABULARY
_VERSION = b'$'

# First, our vocabulary.
# Remove the letter values o and O, Q (confused with O if you're sloppy), l and L, 
# and i and I, leaving the digits 1 and 0
_REMOVED = b'oOQlLiI'
_REPLACE = b'0001111'
_VOCABULARY = b''.join( reversed(sorted(list(set(string.ascii_letters + string.digits) - set( _REMOVED ))) ))

# We translate the letters we removed
_TRANSTABLE = string.maketrans( _REMOVED, _REPLACE )

# Leaving us a base vocabulary to map integers into
_BASE = len(_VOCABULARY)

_ZERO_MARKER = b'@' # Zero is special

def from_external_string(key):
	"""
	Turn the base [BASE] number [key] into an integer

	:raises ValueError: If the key is invalid or contains illegal characters.
	:raises UnicodeDecodeError: If the key is a Unicode object, and contains
		non-ASCII characters (which wouldn't be valid anyway)
	"""

	if not key:
		raise ValueError("Improper key" )

	if isinstance( key, unicode ):
		# Unicode keys cause problems: The _TRANSTABLE is coerced
		# to Unicode, which fails because it contains non-ASCII values.
		# So instead, we encode the unicode string to ascii, which, if it is a
		# valid key, will work
		key = key.encode( 'ascii' )


	key = key[:-1] if key[-1] == _VERSION else key # strip the version if needed
	key = string.translate( key, _TRANSTABLE ) # translate bad chars

	if key == _ZERO_MARKER:
		return 0

	int_sum = 0
	for idx, char in enumerate(reversed(key)):
		int_sum += _VOCABULARY.index(char) * pow(_BASE, idx)
	return int_sum

def to_external_string(integer):
	"""
	Turn an integer [integer] into a base [BASE] number
	in (byte) string representation.
	"""

	# we won't step into the while if integer is 0
	# so we just solve for that case here
	if integer == 0:
		return _ZERO_MARKER

	result = b''
	# Simple string concat benchmarks the fastest for this size data,
	# among a list and an array.array( 'c' )
	while integer > 0:
		integer, remainder = divmod( integer, _BASE )
		result = _VOCABULARY[remainder] + result
	return result
