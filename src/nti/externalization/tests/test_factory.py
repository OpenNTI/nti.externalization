# -*- coding: utf-8 -*-
"""
Tests for factory.py

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import doctest
import unittest

from nti.testing import base
from nti.testing import matchers

from hamcrest import assert_that
from hamcrest import has_entry
from hamcrest import has_key
from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_property
from nti.testing.matchers import validly_provides

logger = __import__('logging').getLogger(__name__)

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

class TestObjectFactory(unittest.TestCase):

    def _getInterface(self):
        from zope.component.interfaces import IFactory
        return IFactory

    def _getTargetClass(self):
        from nti.externalization.factory import ObjectFactory
        return ObjectFactory

    def _makeOne(self, *args, **kwargs):
        return self._getTargetClass()(*args, **kwargs)

    def test_implements_interface(self):

        class Callable(object):
            pass

        factory = self._makeOne(Callable)

        assert_that(factory(), is_(Callable))
        assert_that(factory.title, is_(''))
        assert_that(factory.description, is_(''))

        assert_that(factory, validly_provides(self._getInterface()))

    def test_equality(self):

        class Callable1(object):
            pass

        factory1 = self._makeOne(Callable1)
        factory1_a = self._makeOne(Callable1)

        assert_that(factory1, is_(factory1_a))

        class Callable2(object):
            pass

        factory2 = self._makeOne(Callable2)
        assert_that(factory1, is_not(factory2))
        assert_that(factory2, is_not(factory1))

    def test_subclass(self):
        class Callable(object):
            pass

        class Factory(self._getTargetClass()):
            default_factory = Callable
            default_title = "title"
            default_description = "description"

        factory = Factory()

        assert_that(factory, has_property('_callable', Callable))
        assert_that(factory, has_property('title', Factory.default_title))
        assert_that(factory, has_property('description', Factory.default_description))

        factory = Factory(object, 'foo', 'baz')
        assert_that(factory, has_property('_callable', object))
        assert_that(factory, has_property('title', 'foo'))
        assert_that(factory, has_property('description', 'baz'))

    def test_create_non_callable(self):
        with self.assertRaises(ValueError):
            self._makeOne()


class TestMimeObjectFactory(TestObjectFactory):

    def _getInterface(self):
        from nti.externalization.interfaces import IMimeObjectFactory
        return IMimeObjectFactory

    def _getTargetClass(self):
        from nti.externalization.factory import MimeObjectFactory
        return MimeObjectFactory

class TestClassObjectFactory(TestObjectFactory):

    def _getInterface(self):
        from nti.externalization.interfaces import IClassObjectFactory
        return IClassObjectFactory

    def _getTargetClass(self):
        from nti.externalization.factory import ClassObjectFactory
        return ClassObjectFactory

def test_suite():
    return unittest.TestSuite((
        unittest.defaultTestLoader.loadTestsFromName(__name__),
        doctest.DocTestSuite("nti.externalization.factory"),
    ))
