#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from nti.externalization.singleton import SingletonDecorator
from nti.externalization.singleton import Singleton
from nti.externalization.tests import ExternalizationLayerTest

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import is_not

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904


class TestSingleton(ExternalizationLayerTest):

    def test_singleton_decorator(self):

        # Torturous way of getting a metaclass in a Py2/Py3 compatible
        # way.
        X = SingletonDecorator('X', (object,), {})

        # No context
        assert_that(X(), is_(X()))

        # context ignored
        assert_that(X('context'), is_(X('other_context')))

        # two contexts for the common multi-adapter case
        assert_that(X('context', 'request'),
                    is_(X('other_context', 'other_request')))

        # no instance variables
        x = X()
        with self.assertRaises(AttributeError):
            x.b = 1

        with self.assertRaises(AttributeError):
            getattr(x, '__dict__')

    def test_singleton_when_ancestor_is_singleton(self):
        X = SingletonDecorator('X', (object,), {})
        Y = SingletonDecorator('Y', (X,), {})

        class Z(Y): # pylint:disable=no-init
            pass

        assert_that(X(), is_(X()))
        assert_that(Y(), is_(Y()))
        assert_that(Z(), is_(Z()))
        assert_that(X(), is_not(Z()))
        assert_that(Y(), is_not(Z()))

    def test_custom_eq_hash_ne_ignored(self):

        class X(Singleton):

            def __eq__(self, other): # pragma: no cover
                raise Exception

            __ne__ = __eq__

            def __hash__(self): # pragma: no cover
                raise Exception



        assert_that(X(), is_(X()))
        assert_that(hash(X()), is_(hash(X())))
        assert_that(X(), is_not(self))
