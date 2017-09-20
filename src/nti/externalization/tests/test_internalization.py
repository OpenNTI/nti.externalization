#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope.interface.common.idatetime import IDate

from nti.externalization.tests import ExternalizationLayerTest
from nti.schema.interfaces import InvalidValue

from hamcrest import assert_that
from hamcrest import calling
from hamcrest import raises

__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904





class TestDate(ExternalizationLayerTest):

	def test_exception(self):
		assert_that(calling(IDate).with_args('xx'), raises(InvalidValue))
