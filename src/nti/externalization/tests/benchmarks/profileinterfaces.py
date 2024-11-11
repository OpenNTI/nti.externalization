# -*- coding: utf-8 -*-
"""
A rich user profile.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope.interface import Interface
from zope.interface import taggedValue

from zope.schema import Object
from zope.schema import URI

from nti.schema.field import Dict
from nti.schema.field import TextLine
from nti.schema.field import ValidTextLine
from nti.schema.field import DecodingValidTextLine

from nti.externalization.tests.benchmarks.bootstrapinterfaces import IRootInterface
from nti.externalization.tests.benchmarks.bootstrapinterfaces import checkEmailAddress
from nti.externalization.tests.benchmarks.bootstrapinterfaces import checkRealname

# pylint:disable=inherit-non-class
class IFriendlyNamed(Interface):

    alias = TextLine(title='Display alias',
                     description="Enter preferred display name alias, e.g., johnnyboy."
                     "Your site may impose limitations on this value.",
                     required=False)

    realname = TextLine(title='Full Name aka realname',
                        description="Enter full name, e.g. John Smith.",
                        required=False,
                        constraint=checkRealname)

class IAvatarURL(Interface):
    """
    Something that features a display URL.
    """

    avatarURL = URI(title="URL of your avatar picture",
                    description="If not provided, one will be generated for you.",
                    required=False)


class IBackgroundURL(Interface):

    backgroundURL = URI(title="URL of your background picture",
                        description="If not provided, one will be generated for you.",
                        required=False)


class IProfileAvatarURL(IAvatarURL, IBackgroundURL):
    pass


class IAddress(IRootInterface):

    full_name = ValidTextLine(title="First name", required=True)

    street_address_1 = ValidTextLine(title="Street line 1",
                                     max_length=75, required=True)

    street_address_2 = ValidTextLine(title="Street line 2",
                                     required=False, max_length=75)

    city = ValidTextLine(title="City name", required=True)

    state = ValidTextLine(title="State name",
                          required=False, max_length=10)

    postal_code = ValidTextLine(title="Postal code",
                                required=False, max_length=30)

    country = ValidTextLine(title="Nation name", required=True)
    taggedValue('__external_class_name__',
                'Address')


class IUserContactProfile(Interface):

    addresses = Dict(title="A mapping of address objects.",
                     key_type=DecodingValidTextLine(title="Adresss key"),
                     value_type=Object(IAddress),
                     min_length=0,
                     required=False)

    phones = Dict(title="A mapping of phone numbers objects.",
                  key_type=ValidTextLine(title="Phone key"),
                  value_type=ValidTextLine(title="A phone"),
                  min_length=0,
                  required=False)

    contact_emails = Dict(title="A mapping of contact emails.",
                          key_type=DecodingValidTextLine(title="Email key"),
                          value_type=ValidTextLine(title='Email',
                                                   constraint=checkEmailAddress),
                          min_length=0,
                          required=False)

class IUserProfile(IProfileAvatarURL, # pylint:disable=too-many-ancestors
                   IUserContactProfile,
                   IFriendlyNamed,
                   IRootInterface):
    """A user profile"""
    taggedValue('__external_class_name__',
                'UserProfile')
