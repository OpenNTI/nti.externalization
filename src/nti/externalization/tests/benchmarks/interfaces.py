# -*- coding: utf-8 -*-
"""
Interfaces for objects we will benchmark with.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope.interface import Interface
from zope.interface import taggedValue

from nti.schema.field import TextLine

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
