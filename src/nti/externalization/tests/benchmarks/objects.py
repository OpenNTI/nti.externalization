# -*- coding: utf-8 -*-
"""
Implementations of interfaces.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope import interface

from nti.externalization.datastructures import ExternalizableInstanceDict
from nti.schema.fieldproperty import createDirectFieldProperties

from . import interfaces


@interface.implementer(interfaces.ISimplestPossibleObject)
class SimplestPossibleObject(ExternalizableInstanceDict):
    __external_can_create__ = True
    mimeType = 'application/vnd.nextthought.benchmarks.simplestpossibleobject'


@interface.implementer(interfaces.IDerivedWithOneTextField)
class DerivedWithOneTextField(object):
    createDirectFieldProperties(interfaces.IDerivedWithOneTextField)
