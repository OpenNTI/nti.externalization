# -*- coding: utf-8 -*-
"""
Tests for dublincore.py

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import unittest

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import same_instance

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904


# Test when configured via subscription adapters

class AbstractDCDecoratorTest(object):

    def _getTargetClass(self):
        raise NotImplementedError()

    def _makeOne(self):
        return self._getTargetClass()()

    def test_singleton(self):
        x = self._makeOne()
        y = self._makeOne()

        assert_that(x, is_(same_instance(y)))

class TestDCextendedExternalMappingDecorator(AbstractDCDecoratorTest,
                                             unittest.TestCase):

    def _getTargetClass(self):
        from nti.externalization.dublincore import DCExtendedExternalMappingDecorator
        return DCExtendedExternalMappingDecorator


class TestDCDescriptiveProprtiesExternalMappingDecorator(AbstractDCDecoratorTest,
                                                         unittest.TestCase):

    def _getTargetClass(self):
        from nti.externalization.dublincore import DCDescriptivePropertiesExternalMappingDecorator
        return DCDescriptivePropertiesExternalMappingDecorator
