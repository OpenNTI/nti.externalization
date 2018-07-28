#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
from contextlib import contextmanager
from datetime import date
from datetime import timedelta
import os
import time
import unittest

from zope.interface.common.idatetime import IDate
from zope.interface.common.idatetime import IDateTime

from zope.configuration import xmlconfig
from zope.testing import cleanup

import nti.externalization
from nti.externalization.datetime import datetime_to_string
from nti.externalization.datetime import datetime_from_string
from nti.externalization.tests import ExternalizationLayerTest
from nti.externalization.tests import externalizes
from nti.schema.interfaces import InvalidValue

from hamcrest import assert_that
from hamcrest import calling
from hamcrest import has_property
from hamcrest import is_
from hamcrest import none
from hamcrest import raises

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

@contextmanager
def environ_tz():
    tz = os.environ.get('TZ')
    try:
        yield
    finally:
        if tz: # pragma: no cover
            os.environ['TZ'] = tz
        else: # pragma: no cover
            del os.environ['TZ']
        time.tzset()

class TestDatetime(ExternalizationLayerTest):

    def test_date_from_string(self):
        assert_that(IDate('1982-01-01'), is_(date))

        assert_that(calling(IDate).with_args('boo'),
                    raises(InvalidValue))

    def test_date_to_string(self):
        the_date = IDate('1982-01-31')
        assert_that(the_date, externalizes(is_('1982-01-31')))

    def test_datetime_from_string_returns_naive(self):
        assert_that(IDateTime('1992-01-31T00:00Z'),
                    has_property('tzinfo', none()))
        # Round trips
        assert_that(datetime_to_string(IDateTime('1992-01-31T00:00Z')).toExternalObject(),
                    is_('1992-01-31T00:00:00Z'))

    def test_native_timezone_conversion(self):
        # First, test getting it from the environment
        with environ_tz():
            # Put us in an environment with no DST
            os.environ['TZ'] = 'CST+06'
            time.tzset()
            assert_that(datetime_from_string('2014-01-20T00:00', assume_local=True),
                        is_(IDateTime('2014-01-20T06:00Z')))

            # Specified sticks, assuming non-local
            assert_that(IDateTime('2014-01-20T06:00'),
                        is_(IDateTime('2014-01-20T06:00Z')))

            # Now put us in DST.
            # XXX Not reliable on those days
            os.environ['TZ'] = 'CST+06CDT+05,1,2'
            time.tzset()
            assert_that(datetime_from_string('2014-01-20T00:00', assume_local=True),
                        is_(IDateTime('2014-01-20T06:00Z')))

            # Next, test setting a specific value as a tzname tuple.
            # For this to work we have to be still with the offset in the
            # environment
            assert_that(datetime_from_string('2014-01-20T00:00',
                                             assume_local=True,
                                             local_tzname=('CST', 'CDT')),
                        is_(IDateTime('2014-01-20T06:00Z')))

            # Now with an invalid local_tzname
            assert_that(datetime_from_string('2014-01-20T00:00',
                                             assume_local=True,
                                             local_tzname=('dne')),
                        is_(IDateTime('2014-01-20T06:00Z')))

        # Same result for the canonical name, don't need to be in
        # environment
        assert_that(datetime_from_string('2014-01-20T00:00',
                                         assume_local=True,
                                         local_tzname='US/Central'),
                    is_(IDateTime('2014-01-20T06:00Z')))
        assert_that(datetime_from_string('2014-01-20T00:00',
                                         assume_local=True,
                                         local_tzname='US/Eastern'),
                    is_(IDateTime('2014-01-20T05:00Z')))

    def test_timedelta_to_string(self):
        the_delt = timedelta(weeks=16)
        assert_that(the_delt, externalizes(is_('P112D')))

    def test_datetime_from_timestamp(self):
        from datetime import datetime
        assert_that(IDateTime(123456), is_(datetime.utcfromtimestamp(123456)))

class TestTzinfo(unittest.TestCase):

    def test_invalid_local_name_in_dst_uses_system_settings(self):
        import pytz
        from nti.externalization.datetime import _local_tzinfo
        with environ_tz():
            os.environ['TZ'] = 'CST+06CDT+05,0,365'
            time.tzset()
            zone = _local_tzinfo('dne')
            assert_that(zone, is_(pytz.timezone('Etc/GMT+5')))


def doctest_setUp(_):
    xmlconfig.file('configure.zcml', nti.externalization)

def doctest_tearDown(_):
    cleanup.cleanUp()

def test_suite():
    import doctest
    from unittest import defaultTestLoader
    suite = defaultTestLoader.loadTestsFromName(__name__)

    return unittest.TestSuite([
        suite,
        doctest.DocTestSuite(
            'nti.externalization.datetime',
            setUp=doctest_setUp,
            tearDown=doctest_tearDown,
        ),
    ])
