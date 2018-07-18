#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import sys
import unittest

from nti.externalization.integer_strings import from_external_string
from nti.externalization.integer_strings import to_external_string

from hamcrest import assert_that
from hamcrest import calling
from hamcrest import is_
from hamcrest import raises

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904


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
        for i in range(sys.maxsize - 2000, sys.maxsize):
            _t(i)

    def test_decode_unicode(self):
        assert_that(from_external_string(u'abcde'),
                    is_(204869188))

    def test_bad_value(self):
        assert_that(calling(from_external_string).with_args(''),
                    raises(ValueError, "Improper key"))

def test_suite():
    import doctest
    from unittest import defaultTestLoader
    suite = defaultTestLoader.loadTestsFromName(__name__)

    return unittest.TestSuite([
        suite,
        doctest.DocTestSuite('nti.externalization.integer_strings'),
    ])
