# -*- coding: utf-8 -*-
"""
Implementations of interfaces.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope import interface

from zope.schema.fieldproperty import createFieldProperties

from nti.externalization.datastructures import ExternalizableInstanceDict
from nti.externalization.representation import WithRepr

from nti.schema.fieldproperty import createDirectFieldProperties
from nti.schema.schema import SchemaConfigured
from nti.schema.eqhash import EqHash

from . import interfaces


@interface.implementer(interfaces.ISimplestPossibleObject)
class SimplestPossibleObject(ExternalizableInstanceDict):
    __external_can_create__ = True
    mimeType = 'application/vnd.nextthought.benchmarks.simplestpossibleobject'


@interface.implementer(interfaces.IDerivedWithOneTextField)
class DerivedWithOneTextField(object):
    createDirectFieldProperties(interfaces.IDerivedWithOneTextField)

    def __init__(self, text=u''):
        self.text = text

@interface.implementer(interfaces.IHasListOfDerived)
class HasListOfDerived(object):
    createDirectFieldProperties(interfaces.IHasListOfDerived)


@interface.implementer(interfaces.IAddress)
@EqHash('full_name', 'street_address_1', 'postal_code')
@WithRepr
class Address(SchemaConfigured):
    createDirectFieldProperties(interfaces.IAddress)

@interface.implementer(interfaces.IUserProfile)
@EqHash('addresses', 'alias', 'phones', 'realname')
@WithRepr
class UserProfile(SchemaConfigured):
    createFieldProperties(interfaces.IUserProfile)
