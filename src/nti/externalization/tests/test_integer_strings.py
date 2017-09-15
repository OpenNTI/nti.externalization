#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

import sys
import unittest

from nti.externalization.integer_strings import to_external_string
from nti.externalization.integer_strings import from_external_string

try:
    maxint = sys.maxint
except AttributeError:
    maxint = sys.maxsize


class TestIntStrings(unittest.TestCase):

    def test_round_trip(self):

        def _t(i):
            ext = to_external_string(i)
            __traceback_info__ = i, ext
            parsed = from_external_string(ext)
            assert_that(parsed, is_(i))

        # Small values
        for i in range(0, 100):
            _t(i)

        # Medium values
        for i in range(2000, 5000):
            _t(i)

        # Big values
        for i in range(maxint - 2000, maxint):
            _t(i)

    def test_decode_unicode(self):
        assert_that(from_external_string(u'abcde'), 
					is_(204869188))
