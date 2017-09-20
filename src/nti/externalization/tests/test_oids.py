#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for oids.py.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import unittest

from zope.testing.cleanup import CleanUp

from ..oids import fromExternalOID
from ..oids import toExternalOID

from hamcrest import assert_that
from hamcrest import is_


class TestToExternalOID(CleanUp,
                        unittest.TestCase):

    def test_add_to_connection(self):
        from zope.interface import implementer
        from ZODB.interfaces import IConnection

        @implementer(IConnection)
        class Persistent(object):
            _p_oid = None

            database_name = u'main'
            def add(self, obj):
                obj._p_oid = b'abc'

            def db(self):
                return self


        result = toExternalOID(Persistent(), add_to_connection=True)
        assert_that(result, is_(b'0x616263:6d61696e'))

    def test_add_to_connection_no_connection(self):
        class Persistent(object):
            _p_oid = None

        result = toExternalOID(Persistent(), add_to_connection=True, default='default')
        assert_that(result, is_('default'))

    def test_intid(self):
        from zope.interface import implementer
        from zope.intid.interfaces import IIntIds
        from zope import component

        @implementer(IIntIds)
        class IntIds(object):

            def queryId(self, obj):
                return None

            def register(self, obj):
                return 1

        class Persistent(object):
            _p_oid = b'abc'

        component.provideUtility(IntIds())
        result = toExternalOID(Persistent(), add_to_intids=True)
        assert_that(result, is_(b'0x616263::y'))

class TestFromExternalOID(unittest.TestCase):

    def test_with_intid(self):

        oid, db_name, intid = fromExternalOID(b'0x616263::y')
        assert_that(oid, is_(b'\x00\x00\x00\x00\x00abc'))
        assert_that(db_name, is_(b''))
        assert_that(intid, is_(1))
