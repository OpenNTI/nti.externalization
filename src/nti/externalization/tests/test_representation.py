# -*- coding: utf-8 -*-
"""
Tests for representation.py

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import re
import unittest

from persistent import Persistent

import fudge

from . import ExternalizationLayerTest
from .. import representation

from hamcrest import assert_that
from hamcrest import contains_string
from hamcrest import is_

logger = __import__('logging').getLogger(__name__)

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
# pylint:disable=attribute-defined-outside-init, useless-object-inheritance

class TestWithRepr(unittest.TestCase):

    def test_default(self):

        @representation.WithRepr
        class Foo(object):
            pass

        r = repr(Foo())
        assert_that(r, contains_string('<nti.externalization.tests.test_representation.Foo'))
        assert_that(r, contains_string('{}>'))

    def test_proxied(self):
        from zope.security.checker import ProxyFactory
        @representation.WithRepr
        class Foo(object):
            pass

        r = repr(ProxyFactory(Foo()))
        assert_that(r, contains_string('<nti.externalization.tests.test_representation.Foo at'))
        assert_that(r, contains_string('{}'))


    def test_with_default_callable(self):
        @representation.WithRepr(lambda s: "<HI>")
        class Foo(object):
            pass

        r = repr(Foo())
        assert_that(r, is_("<HI>"))

    def test_raises_POSError(self):
        def raise_(self):
            from ZODB.POSException import ConnectionStateError
            raise ConnectionStateError()

        @representation.WithRepr(raise_)
        class Foo(object):
            pass

        r = repr(Foo())
        assert_that(r,
                    is_("<nti.externalization.tests.test_representation.Foo(Ghost, "
                        "ConnectionStateError())>"))

    def test_raises_attribute_error(self):
        def raise_(self):
            raise AttributeError()

        @representation.WithRepr(raise_)
        class Foo(object):
            pass

        r = repr(Foo())
        assert_that(r,
                    is_("<nti.externalization.tests.test_representation.Foo("
                        "AttributeError())>"))

    def _normalize_repr(self, r):
        # Pure-python vs C
        r = r.replace('nti.externalization.tests.test_representation.', '')
        # addresses
        r = re.sub(r'0x[0-9a-fA-F]*', '0xdeadbeef', r)
        # Python 3.7 removed the trailing , in exception reprs
        r = r.replace("',)", "')")
        # Python 2 doesn't have a leading b prefix for byte literals
        r = r.replace("oid '", "oid b'")
        return r

    def _normalized_repr(self, o):
        return self._normalize_repr(repr(o))

    def test_persistent_subclass_default(self):
        @representation.WithRepr
        class Foo(Persistent):
            pass

        o = Foo()
        r = self._normalized_repr(o)

        assert_that(r,
                    is_('<Foo object at 0xdeadbeef _p_repr {}>'))

        o._p_oid = b'12345678'
        r = self._normalized_repr(o)
        # Persistent 4.4.3 and above represent the OID using hex; prior
        # to that it was bytes.
        assert_that(r,
                    is_("<Foo object at 0xdeadbeef oid 0xdeadbeef _p_repr {}>"))

        o.a = 1

        r = self._normalized_repr(o)

        assert_that(r,
                    is_("<Foo object at 0xdeadbeef oid 0xdeadbeef _p_repr {'a': 1}>"))

    def test_persistent_subclass_custom(self):
        @representation.WithRepr(lambda s: 'Hi')
        class Foo(Persistent):
            pass

        o = Foo()
        r = self._normalized_repr(o)
        assert_that(r,
                    is_('<Foo object at 0xdeadbeef _p_repr Hi>'))

    def test_persistent_subclass_raise(self):

        def raise_(self):
            raise AttributeError()

        @representation.WithRepr(raise_)
        class Foo(Persistent):
            pass

        o = Foo()
        r = self._normalized_repr(o)

        assert_that(r,
                    is_('<Foo object at 0xdeadbeef _p_repr AttributeError()>'))


class AbstractRepresenterTestMixin(object):
    FORMAT = None

    def _getTargetClass(self):
        raise NotImplementedError

    def _makeOne(self):
        return self._getTargetClass()()

    def _simpleStringRepr(self, s):
        raise NotImplementedError

    def _simpleNumRepr(self, i):
        return str(i)

    def test_dump_fraction(self):
        import fractions
        num = fractions.Fraction('1/3')

        rep = self._makeOne()
        result = rep.dump(num)
        assert_that(result, is_(self._simpleStringRepr('1/3')))

        assert_that(
            representation.to_external_representation({'key': num}, self.FORMAT),
            is_(representation.to_external_representation({'key': '1/3'}, self.FORMAT))
        )

    def test_dump_decimal_integral(self):
        import decimal
        num = decimal.Decimal(1)

        rep = self._makeOne()
        result = rep.dump(num)
        assert_that(result, is_(self._simpleNumRepr(1)))

        assert_that(
            representation.to_external_representation({'key': num}, self.FORMAT),
            is_(representation.to_external_representation({'key': 1}, self.FORMAT))
        )


    def test_dump_decimal_float(self):
        import decimal

        for s in '1.1', '2.561702493119680037517373933E+139':
            num = decimal.Decimal(s)
            rep = self._makeOne()
            result = rep.dump(num)
            assert_that(result.lower(), is_(self._simpleNumRepr(s.lower())))

            # We preserve the full representation of the decimal
            expected = representation.to_external_representation({'key': float(s)}, self.FORMAT)
            expected = expected.replace('2.56170249311968e+139', s.lower())
            assert_that(
                representation.to_external_representation({'key': num}, self.FORMAT).lower(),
                is_(expected)
            )


    def test_dump_decimal_nan(self):
        import decimal
        rep = self._makeOne()

        for f in float('-nan'), float('nan'):
            num = decimal.Decimal.from_float(f)
            result = rep.dump(num)
            __traceback_info__ = result
            result = rep.load(result)
            assert_that(str(f), is_(str(result)))

    def test_dump_decimal_inf(self):
        import decimal
        rep = self._makeOne()

        for f in float('-inf'), float('inf'):
            num = decimal.Decimal(f)
            result = rep.dump(num)
            __traceback_info__ = result
            result = rep.load(result)
            assert_that(result, is_(f))

    def test_unicode(self):
        rep = self._makeOne()

        result = rep.dump(u"Hi")
        assert_that(result, is_(self._simpleStringRepr('Hi')))

        result = rep.load(result)
        assert_that(result, is_(u'Hi'))


class TestYaml(AbstractRepresenterTestMixin,
               ExternalizationLayerTest):

    FORMAT = u'yaml'

    def _getTargetClass(self):
        return representation.YamlRepresenter

    def _simpleStringRepr(self, s):
        return s + '\n...\n'

    def _simpleNumRepr(self, i):
        return str(i) + '\n...\n'


class TestJson(AbstractRepresenterTestMixin,
               ExternalizationLayerTest):

    FORMAT = u'json'

    def _getTargetClass(self):
        return representation.JsonRepresenter

    def _simpleStringRepr(self, s):
        return '"' + s + '"'

    def test_dump_to_stream(self):
        import io

        json = self._makeOne()
        bio = io.BytesIO() if str is bytes else io.StringIO()
        json.dump(u"hi", bio)

        assert_that(bio.getvalue(), is_('"hi"'))

    def test_load_bytes(self):
        json = self._makeOne()
        result = json.load(b'"hi"')
        assert_that(result, is_(u"hi"))

    @fudge.patch('simplejson.loads')
    def test_loads_returns_bytes(self, loads):
        loads.expects_call().returns(b'bytes')

        json = self._makeOne()
        result = json.load(b'hi')
        assert_that(result, is_(u'bytes'))

    def test_to_json_representation(self):
        result = representation.to_json_representation({})
        assert_that(result, is_('{}'))

    def test_second_pass(self):
        from ..interfaces import IExternalObject
        from zope import component

        json = self._makeOne()
        result = json.dump(self)
        assert_that(result, contains_string('NonExternalizableObject'))

        class SecondPass(object):
            def __init__(self, obj):
                self.obj = obj

            def toExternalObject(self, **kw):
                return self.obj

        component.getGlobalSiteManager().registerAdapter(
            SecondPass,
            required=(type(self,),),
            provided=IExternalObject,
            name="second-pass"
        )
        try:
            json = representation.JsonRepresenter()
            with self.assertRaises(TypeError):
                json.dump(self)
        finally:
            component.getGlobalSiteManager().unregisterAdapter(
                SecondPass,
                required=(type(self,),),
                provided=IExternalObject,
                name="second-pass"
            )
