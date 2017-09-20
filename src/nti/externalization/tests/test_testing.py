# -*- coding: utf-8 -*-
"""
Tests for testing.py

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import unittest

from nti.externalization.testing import externalizes

from hamcrest import assert_that
from hamcrest import contains_string
from hamcrest import is_

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

class TestExternalizes(unittest.TestCase):

    def test_mismatch(self):

        with self.assertRaises(AssertionError) as exc:
            assert_that(self, externalizes(is_('foo')))

        e = exc.exception
        assert_that(str(e.args[0]),
                    contains_string("Expected: object that can be externalized to 'foo'"))
        assert_that(str(e.args[0]),
                    contains_string("was replaced by"))

    def test_externalizes_none(self):

        with self.assertRaises(AssertionError) as exc:
            assert_that(None, externalizes(is_('foo')))

        e = exc.exception
        assert_that(str(e.args[0]),
                    contains_string("Expected: object that can be externalized to 'foo'"))
        assert_that(str(e.args[0]),
                    contains_string("externalized to none"))
