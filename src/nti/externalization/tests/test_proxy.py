#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import unittest

from Acquisition import Implicit
from ExtensionClass import Base
from zope.container.contained import ContainedProxy
from zope.proxy import ProxyBase

from nti.externalization.proxy import removeAllProxies
from nti.testing.matchers import aq_inContextOf

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import same_instance

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904


class EC(Base):
    x = None

    @classmethod
    def wrapping(cls, implicit):
        ec = cls()
        ec.x = implicit
        return ec.x

class IM(Implicit):
    pass

def aq_proxied(im):
    ec = EC()
    ec.x = im
    assert_that(ec.x, is_(aq_inContextOf(ec)))
    return ec.x

class TestProxy(unittest.TestCase):

    def test_removeAllProxies_simple(self):

        obj = IM()

        # One layer of wrapping of each
        for wrap in ProxyBase, ContainedProxy, aq_proxied:
            wrapped = wrap(obj)
            assert_that(removeAllProxies(wrapped), is_(same_instance(obj)))


    def test_removeAllProxies_doubled(self):
        # double wrapping in weird combos
        obj = IM()
        for wrap in ProxyBase, ContainedProxy, aq_proxied:
            wrapped = wrap(obj)
            for wrap2 in ContainedProxy, ProxyBase:
                __traceback_info__ = wrap, wrap2
                wrapped = wrap2(wrapped)
                assert_that(removeAllProxies(wrapped), is_(same_instance(obj)))

    def test_removeAllProxies_multiple_wraps(self):
        from itertools import permutations
        wrappers = [ProxyBase, ContainedProxy, EC.wrapping]
        obj = IM()
        wrapped = obj
        for permutation in permutations(wrappers):
            for wrapper in permutation:
                wrapped = wrapper(wrapped)

        assert_that(removeAllProxies(wrapped), is_(same_instance(obj)))

def test_suite():
    import doctest
    from unittest import defaultTestLoader
    suite = defaultTestLoader.loadTestsFromName(__name__)

    return unittest.TestSuite([
        suite,
        doctest.DocTestSuite('nti.externalization.proxy'),
    ])
