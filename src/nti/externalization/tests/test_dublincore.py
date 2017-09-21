# -*- coding: utf-8 -*-
"""
Tests for dublincore.py

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import unittest

from . import ExternalizationLayerTest

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import same_instance

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
# pylint: disable=attribute-defined-outside-init

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

    def test_decorated(self):
        class Original(object):
            creators = None

        external = {}
        original = Original()
        self._makeOne().decorateExternalMapping(original, external)

        assert_that(external,
                    is_({'DCCreator': None}))

        # If we add one, running again will not overwrite it,
        # but it will set the new field
        original.creators = ['abc']
        self._makeOne().decorateExternalMapping(original, external)

        assert_that(external,
                    is_({'DCCreator': None,
                         'Creator': 'abc'}))


class TestDCDescriptiveProprtiesExternalMappingDecorator(AbstractDCDecoratorTest,
                                                         unittest.TestCase):

    def _getTargetClass(self):
        from nti.externalization.dublincore import DCDescriptivePropertiesExternalMappingDecorator
        return DCDescriptivePropertiesExternalMappingDecorator

    def test_decorated(self):

        class Original(object):
            pass

        external = {}
        original = Original()
        self._makeOne().decorateExternalMapping(original, external)

        assert_that(external,
                    is_({'DCTitle': None,
                         'DCDescription': None}))

        # If we add one, running again will not overwrite it,
        original.title = 'Title'
        original.description = 'description'
        self._makeOne().decorateExternalMapping(original, external)

        assert_that(external,
                    is_({'DCTitle': None,
                         'DCDescription': None}))

        external = {}
        self._makeOne().decorateExternalMapping(original, external)

        assert_that(external,
                    is_({'DCTitle': original.title,
                         'DCDescription': original.description}))

class TestConfigured(ExternalizationLayerTest):

    def test_decorate(self):
        from zope.dublincore.interfaces import IDCDescriptiveProperties
        from zope.dublincore.interfaces import IDCExtended
        from zope import interface

        from nti.externalization.externalization import decorate_external_mapping

        @interface.implementer(IDCExtended, IDCDescriptiveProperties)
        class O(object):
            creators = ('abc',)
            title = 'title'
            description = 'description'

        result = decorate_external_mapping(O(), {})

        assert_that(result,
                    is_({'DCTitle': O.title,
                         'DCDescription': O.description,
                         'DCCreator': O.creators,
                         'Creator': O.creators[0]}))
