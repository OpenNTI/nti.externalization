# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest

from zope.proxy import ProxyBase

from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import is_
from hamcrest import same_instance

from nti.externalization.externalization import to_external_object
from ..externalizer import _obj_has_usable_externalObject


class WithToExternalObject(object):

    def toExternalObject(self, **kwargs):
        return {'a': 42}



class TestFunctions(unittest.TestCase):

    def test_non_proxied(self):
        self.assertTrue(_obj_has_usable_externalObject(WithToExternalObject()))

    def test_has_usable_external_object_proxied(self):

        obj = WithToExternalObject()
        proxied = ProxyBase(obj)

        self.assertTrue(_obj_has_usable_externalObject(proxied))
        self.assertEqual({'a': 42}, to_external_object(proxied))

    def test_proxy_has_usable_external_object_not_allowed(self):

        class Proxy(ProxyBase):

            def toExternalObject(self, **kwargs):
                raise NotImplementedError

        self.assertFalse(_obj_has_usable_externalObject(Proxy(object())))


    def test_calls_conform(self):
        from nti.externalization.interfaces import IInternalObjectExternalizer
        from nti.externalization.interfaces import INonExternalizableReplacementFactory

        class Obj(object):
            def __init__(self):
                self.conforms = []

            def __conform__(self, iface):
                self.conforms.append(iface)

        o = Obj()
        to_external_object(o)

        assert_that(o.conforms, has_length(2))
        assert_that(o.conforms,
                    is_([IInternalObjectExternalizer, INonExternalizableReplacementFactory]))

    def test_uses_directly_provided(self):
        from zope import interface
        from nti.externalization.interfaces import IInternalObjectExternalizer

        class Obj(object):
            pass

        o = Obj()
        interface.directlyProvides(o, IInternalObjectExternalizer)
        o.toExternalObject = lambda *args, **kwargs: ''

        assert_that(IInternalObjectExternalizer(o, None),
                    is_(same_instance(o)))

        x = to_external_object(o)
        assert_that(x, is_(''))


if __name__ == '__main__':
    unittest.main()
