# -*- coding: utf-8 -*-
"""
Interfaces for objects we will benchmark with.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import re

from zope.interface import Interface


from nti.schema.interfaces import InvalidValue

# pylint:disable=inherit-non-class

class EmailAddressInvalid(InvalidValue):
    """
    Invalid email address.
    """

    i18n_message = u"The email address you have entered is not valid."

    def __init__(self, address):
        super(EmailAddressInvalid, self).__init__(address, value=address)


class RealnameInvalid(InvalidValue):
    """
    Invalid realname.
    """

    field = 'realname'
    i18n_message = u"The first or last name you have entered is not valid."

    def __init__(self, name):
        super(RealnameInvalid, self).__init__(name, value=name)


rfc822_specials = '()<>@,;:\\"[]'


def isValidMailAddress(addr):
    """Returns True if the email address is valid and False if not."""
    # Taken from z3c.schema.email
    # pylint:disable=too-many-return-statements
    # pylint:disable=too-many-branches
    # First we validate the name portion (name@domain)
    c = 0
    while c < len(addr):
        if addr[c] == '@':
            break
        # Make sure there are only ASCII characters
        if ord(addr[c]) <= 32 or ord(addr[c]) >= 127:
            return False
        # A RFC-822 address cannot contain certain ASCII characters
        if addr[c] in rfc822_specials:
            return False
        c = c + 1

    # check whether we have any input and that the name did not end with a dot
    if not c or addr[c - 1] == '.':
        return False

    # check also starting and ending dots in (name@domain)
    if addr.startswith('.') or addr.endswith('.'):
        return False

    # Next we validate the domain portion (name@domain)
    domain = c = c + 1
    # Ensure that the domain is not empty (name@)
    if domain >= len(addr):
        return False
    count = 0
    while c < len(addr):
        # Make sure that domain does not end with a dot or has two dots in a row
        if addr[c] == '.':
            if c == domain or addr[c - 1] == '.':
                return False
            count = count + 1
        # Make sure there are only ASCII characters
        if ord(addr[c]) <= 32 or ord(addr[c]) >= 127:
            return False
        # A RFC-822 address cannot contain certain ASCII characters
        if addr[c] in rfc822_specials:
            return False
        c = c + 1
    return count >= 1


#: A sequence of only non-alphanumeric characters
#: or a sequence of only digits and spaces, the underscore, and non-alphanumeric characters
#: (which is basically \W with digits and _ added back
_INVALID_REALNAME_RE = re.compile(r'^\W+$|^[\d\s\W_]+$', re.UNICODE)


def checkRealname(value):
    """
    Ensure that the realname doesn't consist of just digits/spaces
    or just alphanumeric characters
    """
    if value:
        if _INVALID_REALNAME_RE.match(value):
            raise RealnameInvalid(value)
        # Component parts? TODO: What about 'Jon Smith 3' as 'Jon Smith III'?
        # for x in value.split():
    return True

def _checkEmailAddress(address):
    """
    Check email address.

    This should catch most invalid but no valid addresses.
    """
    if not isValidMailAddress(address):
        raise EmailAddressInvalid(address)
    domain = address.rsplit('.', 1)[-1]
    if domain.lower() not in ('com', 'org', 'net', 'edu'):
        raise EmailAddressInvalid(address)
    return True


def _isValidEmail(email):
    """
    checks for valid email
    """
    _checkEmailAddress(email)
    return True


def checkEmailAddress(value):
    if value and _isValidEmail(value):
        return True
    raise EmailAddressInvalid(value)


class IRootInterface(Interface):
    """
    A root interface.
    """
