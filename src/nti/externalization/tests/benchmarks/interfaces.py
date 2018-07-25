# -*- coding: utf-8 -*-
"""
Interfaces for objects we will benchmark with.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope.interface import Interface
from zope.interface import taggedValue

from zope.schema import List
from zope.schema import Object

from nti.schema.field import TextLine

from nti.externalization.tests.benchmarks.bootstrapinterfaces import IRootInterface
from nti.externalization.tests.benchmarks.profileinterfaces import IFriendlyNamed
from nti.externalization.tests.benchmarks.profileinterfaces import IAvatarURL
from nti.externalization.tests.benchmarks.profileinterfaces import IBackgroundURL
from nti.externalization.tests.benchmarks.profileinterfaces import IProfileAvatarURL
from nti.externalization.tests.benchmarks.profileinterfaces import IAddress
from nti.externalization.tests.benchmarks.profileinterfaces import IUserContactProfile
from nti.externalization.tests.benchmarks.profileinterfaces import IUserProfile

__all__ = [
    'IRootInterface',
    'ISimplestPossibleObject',
    'IDerivedWithOneTextField',
    'IHasListOfDerived',
    'IFriendlyNamed',
    'IAvatarURL',
    'IBackgroundURL',
    'IProfileAvatarURL',
    'IAddress',
    'IUserContactProfile',
    'IUserProfile',
]

# pylint:disable=inherit-non-class
class ISimplestPossibleObject(Interface):
    """
    This will be a very simple object, with no
    schema and no fields to set.
    """

class IDerivedWithOneTextField(IRootInterface):

    text = TextLine(title=u"Some text", required=True)

    taggedValue('__external_class_name__',
                'DerivedWithOneTextField')


class IHasListOfDerived(IRootInterface):

    the_objects = List(Object(IDerivedWithOneTextField))

    taggedValue('__external_class_name__',
                'HasListOfDerived')

for _ in __all__:
    # For documentation purposes, we have profileinterfaces separate.
    # But only one interfaces module is recognized by ext:registerAutoPackageIO
    globals()[_].__module__ = IHasListOfDerived.__module__
