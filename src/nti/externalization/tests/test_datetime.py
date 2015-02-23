#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import raises
from hamcrest import calling
from hamcrest import has_property
from hamcrest import assert_that

import os
import time
from datetime import date
from datetime import timedelta
from zope.interface.common.idatetime import IDate
from zope.interface.common.idatetime import IDateTime

from nti.externalization.datetime import _datetime_to_string
from nti.externalization.datetime import datetime_from_string

from nti.schema.interfaces import InvalidValue

from nti.externalization.tests import externalizes
from nti.externalization.tests import ExternalizationLayerTest

class TestDatetime(ExternalizationLayerTest):

	def test_date_from_string(self):
		assert_that( IDate('1982-01-01'), is_(date))

		assert_that( calling(IDate).with_args('boo'),
					 raises(InvalidValue))

	def test_date_to_string(self):
		the_date = IDate('1982-01-31')
		assert_that( the_date, externalizes( is_( '1982-01-31' )))

	def test_datetime_from_string_returns_naive(self):
		assert_that(IDateTime('1992-01-31T00:00Z'),
					has_property('tzinfo', none()))
		# Round trips
		assert_that(_datetime_to_string(IDateTime('1992-01-31T00:00Z')).toExternalObject(),
					is_('1992-01-31T00:00:00Z'))

	def test_native_timezone_conversion(self):
		# First, test getting it from the environment
		tz = os.environ.get('TZ')
		try:
			# Put us in an environment with no DST
			os.environ['TZ'] = 'CST+06'
			time.tzset()
			assert_that( datetime_from_string('2014-01-20T00:00', assume_local=True),
						 is_( IDateTime('2014-01-20T06:00Z')))

			# Specified sticks, assuming non-local
			assert_that(IDateTime('2014-01-20T06:00'),
						is_( IDateTime('2014-01-20T06:00Z')))

			# Now put us in DST.
			# XXX Not reliable on those days
			os.environ['TZ'] = 'CST+06CDT+05,1,2'
			time.tzset()
			assert_that( datetime_from_string('2014-01-20T00:00', assume_local=True),
						 is_( IDateTime('2014-01-20T06:00Z')))

			# Next, test setting a specific value as a tzname tuple.
			# For this to work we have to be still with the offset in the environment
			assert_that( datetime_from_string('2014-01-20T00:00',
											  assume_local=True,
											  local_tzname=('CST', 'CDT')),
							 is_( IDateTime('2014-01-20T06:00Z')))

		finally:
			if tz:
				os.environ['TZ'] = tz
			else:
				del os.environ['TZ']
			time.tzset()

			# Same result for the canonical name, don't need to be in environment
			assert_that( datetime_from_string('2014-01-20T00:00',
											  assume_local=True,
											  local_tzname='US/Central'),
							 is_( IDateTime('2014-01-20T06:00Z')))
			assert_that( datetime_from_string('2014-01-20T00:00',
											  assume_local=True,
											  local_tzname='US/Eastern'),
							 is_( IDateTime('2014-01-20T05:00Z')))

	def test_timedelta_to_string(self):
		the_delt = timedelta(weeks=16)
		assert_that( the_delt, externalizes( is_( 'P112D' )))
