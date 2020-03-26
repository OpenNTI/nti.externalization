# -*- coding: utf-8 -*-
"""
Support for externalizing arbitrary numbers.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import fractions
import decimal

from zope import interface
from zope import component
from zope.interface.common.numbers import INumber
from zope.interface.common.numbers import IRational

from nti.externalization.interfaces import IInternalObjectExternalizer


@interface.implementer(IInternalObjectExternalizer)
@component.adapter(INumber)
class second_chance_number_externalizer(object):
    def __init__(self, context):
        self.context = context

    def toExternalObject(self, **unused_kwargs):
        return str(self.context)

# Depending on the order of imports, these may or may not have
# been declared already.
if not IRational.providedBy(fractions.Fraction('1/3')): # pragma: no cover
    interface.classImplements(fractions.Fraction, IRational)

if not INumber.providedBy(decimal.Decimal('1')): # pragma: no cover
    # NOT an IReal; see notes in stdlib numbers.py for why.
    interface.classImplements(decimal.Decimal, INumber)

assert IRational.providedBy(fractions.Fraction('1/3'))
assert INumber.providedBy(decimal.Decimal('1'))
