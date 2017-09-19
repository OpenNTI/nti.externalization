#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from six import with_metaclass

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import same_instance

from nti.externalization.singleton import SingletonDecorator

from nti.externalization.tests import ExternalizationLayerTest


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
