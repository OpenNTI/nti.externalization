#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


from nti.externalization.singleton import SingletonDecorator
from nti.externalization.tests import ExternalizationLayerTest

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import is_not
from hamcrest import same_instance

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904


class TestSingleton(ExternalizationLayerTest):

    def test_singleton_decorator(self):

        # Torturous way of getting a metaclass in a Py2/Py3 compatible
        # way.
        X = SingletonDecorator('X', (object,), {})

        # No context
        assert_that(X(), is_(same_instance(X())))

        # context ignored
        assert_that(X('context'), is_(same_instance(X('other_context'))))

        # two contexts for the common multi-adapter case
        assert_that(X('context', 'request'),
                    is_(same_instance(X('other_context', 'other_request'))))

        x = X()
        with self.assertRaises(AttributeError):
            x.b = 1

        with self.assertRaises(AttributeError):
            getattr(x, '__dict__')

    def test_singleton_when_ancestor_is_singleton(self):
        X = SingletonDecorator('X', (object,), {})
        Y = SingletonDecorator('Y', (X,), {})
        class Z(Y):
            pass

        assert_that(X(), is_(same_instance(X())))
        assert_that(Y(), is_(same_instance(Y())))
        assert_that(Z(), is_(same_instance(Z())))
        assert_that(X(), is_not(same_instance(Z())))
        assert_that(Y(), is_not(same_instance(Z())))


def test_suite():
    import unittest
    import doctest
    suite = unittest.defaultTestLoader.loadTestsFromName(__name__)

    return unittest.TestSuite([
        suite,
        doctest.DocTestSuite(
            'nti.externalization.singleton',
        ),
    ])
