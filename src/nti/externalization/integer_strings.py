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

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

__all__ = [
    'to_external_string',
    'from_external_string',
]

# stdlib imports
import string

try:
    maketrans = str.maketrans
except AttributeError: # Python 2
    from string import maketrans

translate = str.translate

# In the first version of the protocol, the version marker, which would
# come at the end, is always omitted. Subsequent versions will append
# a value that cannot be produced from the _VOCABULARY
_VERSION = '$'

# First, our vocabulary.
# Remove the letter values o and O, Q (confused with O if you're sloppy), l and L,
# and i and I, leaving the digits 1 and 0
_REMOVED = 'oOQlLiI'
_REPLACE = '0001111'
_VOCABULARY = ''.join(
    reversed(sorted(list(set(string.ascii_letters + string.digits) - set(_REMOVED))))
)

# We translate the letters we removed
_TRANSTABLE = maketrans(_REMOVED, _REPLACE)

# Leaving us a base vocabulary to map integers into
_BASE = len(_VOCABULARY)

_ZERO_MARKER = '@'  # Zero is special


def from_external_string(key):
    """
    Turn the string in *key* into an integer.

    >>> from_external_string('xkr')
    6773

    :param str key: A native string, as produced by `to_external_string`.
       (On Python 2, unicode *keys* are also valid.)

    :raises ValueError: If the key is invalid or contains illegal characters.
    :raises UnicodeDecodeError: If the key is a Unicode object, and contains
        non-ASCII characters (which wouldn't be valid anyway)
    """

    if not key:
        raise ValueError("Improper key")

    if not isinstance(key, str):
        # Unicode keys cause problems on Python 2: The _TRANSTABLE is coerced
        # to Unicode, which fails because it contains non-ASCII values.
        # So instead, we encode the unicode string to ascii, which, if it is a
        # valid key, will work
        key = key.decode('ascii') if isinstance(key, bytes) else key.encode('ascii')

    # strip the version if needed
    key = key[:-1] if key[-1] == _VERSION else key
    key = translate(key, _TRANSTABLE)  # translate bad chars

    if key == _ZERO_MARKER:
        return 0

    int_sum = 0
    for idx, char in enumerate(reversed(key)):
        int_sum += _VOCABULARY.index(char) * pow(_BASE, idx)
    return int_sum


def to_external_string(integer):
    """
    Turn an integer into a native string representation.

    >>> to_external_string(123)
    'xk'
    >>> to_external_string(123456789)
    'kVxr5'

    """

    # we won't step into the while if integer is 0
    # so we just solve for that case here
    if integer == 0:
        return _ZERO_MARKER

    result = ''
    # Simple string concat benchmarks the fastest for this size data,
    # among a list and an array.array( 'c' )
    while integer > 0:
        integer, remainder = divmod(integer, _BASE)
        result = _VOCABULARY[remainder] + result
    return result
