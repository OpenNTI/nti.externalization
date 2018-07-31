# -*- coding: utf-8 -*-
"""
Tests for interfaces.py

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest

from hamcrest import assert_that
from hamcrest import has_property

from nti.externalization.interfaces import LocatedExternalDict

class TestLocatedExternalDict(unittest.TestCase):

    def _makeOne(self, *args, **kwargs):
        return LocatedExternalDict(*args, **kwargs)

    def test_construct_from_keywords(self):
        led = self._makeOne(a=1, b=2)
        self.assertEqual(led, {'a': 1, 'b': 2})

    def test_construct_from_dict(self):
        led = self._makeOne({'a': 1, 'b': 2})
        self.assertEqual(led, {'a': 1, 'b': 2})

    def test_arbitrary_attributes(self):
        led = self._makeOne()
        led.lastModified = 42
        assert_that(led, has_property('lastModified', 42))
