#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import raises
from hamcrest import calling
from hamcrest import assert_that

from zope.interface.common.idatetime import IDate

from nti.schema.interfaces import InvalidValue

from nti.externalization.tests import ExternalizationLayerTest

class TestDate(ExternalizationLayerTest):

	def test_exception(self):
		assert_that( calling(IDate).with_args('xx'), raises(InvalidValue) )
