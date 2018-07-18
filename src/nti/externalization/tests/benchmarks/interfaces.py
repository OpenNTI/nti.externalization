# -*- coding: utf-8 -*-
"""
Interfaces for objects we will benchmark with.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import re

from zope.interface import Interface
from zope.interface import taggedValue

from zope.schema import List
from zope.schema import Object
from zope.schema import URI

from nti.schema.field import Dict
from nti.schema.field import TextLine
from nti.schema.field import ValidTextLine
from nti.schema.field import DecodingValidTextLine

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


class ISimplestPossibleObject(Interface):
    """
    This will be a very simple object, with no
    schema and no fields to set.
    """

class IRootInterface(Interface):
    """
    A root interface.
    """

class IDerivedWithOneTextField(IRootInterface):

    text = TextLine(title=u"Some text", required=True)

    taggedValue('__external_class_name__',
                'DerivedWithOneTextField')


class IHasListOfDerived(IRootInterface):

    the_objects = List(Object(IDerivedWithOneTextField))

    taggedValue('__external_class_name__',
                'HasListOfDerived')

class IFriendlyNamed(Interface):

    alias = TextLine(title=u'Display alias',
                     description=u"Enter preferred display name alias, e.g., johnnyboy."
                     u"Your site may impose limitations on this value.",
                     required=False)

    realname = TextLine(title=u'Full Name aka realname',
                        description=u"Enter full name, e.g. John Smith.",
                        required=False,
                        constraint=checkRealname)

class IAvatarURL(Interface):
    """
    Something that features a display URL.
    """

    avatarURL = URI(title=u"URL of your avatar picture",
                    description=u"If not provided, one will be generated for you.",
                    required=False)


class IBackgroundURL(Interface):

    backgroundURL = URI(title=u"URL of your background picture",
                        description=u"If not provided, one will be generated for you.",
                        required=False)


class IProfileAvatarURL(IAvatarURL, IBackgroundURL):
    pass


class IAddress(IRootInterface):

    full_name = ValidTextLine(title=u"First name", required=True)

    street_address_1 = ValidTextLine(title=u"Street line 1",
                                     max_length=75, required=True)

    street_address_2 = ValidTextLine(title=u"Street line 2",
                                     required=False, max_length=75)

    city = ValidTextLine(title=u"City name", required=True)

    state = ValidTextLine(title=u"State name",
                          required=False, max_length=10)

    postal_code = ValidTextLine(title=u"Postal code",
                                required=False, max_length=30)

    country = ValidTextLine(title=u"Nation name", required=True)
    taggedValue('__external_class_name__',
                'Address')


class IUserContactProfile(Interface):

    addresses = Dict(title=u"A mapping of address objects.",
                     key_type=DecodingValidTextLine(title=u"Adresss key"),
                     value_type=Object(IAddress),
                     min_length=0,
                     required=False)

    phones = Dict(title=u"A mapping of phone numbers objects.",
                  key_type=ValidTextLine(title=u"Phone key"),
                  value_type=ValidTextLine(title=u"A phone"),
                  min_length=0,
                  required=False)

    contact_emails = Dict(title=u"A mapping of contact emails.",
                          key_type=DecodingValidTextLine(title=u"Email key"),
                          value_type=ValidTextLine(title=u'Email',
                                                   constraint=checkEmailAddress),
                          min_length=0,
                          required=False)

class IUserProfile(IProfileAvatarURL,
                   IUserContactProfile,
                   IFriendlyNamed,
                   IRootInterface):
    """A user profile"""
    taggedValue('__external_class_name__',
                'UserProfile')
