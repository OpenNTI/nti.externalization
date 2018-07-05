#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import unittest

import persistent
from persistent import Persistent
from persistent.wref import WeakRef as PWeakRef

from nti.externalization.persistence import PersistentExternalizableList
from nti.externalization.persistence import PersistentExternalizableDictionary
from nti.externalization.persistence import PersistentExternalizableWeakList
from nti.externalization.persistence import getPersistentState
from nti.externalization.persistence import setPersistentStateChanged
from nti.externalization.tests import ExternalizationLayerTest

from hamcrest import assert_that
from hamcrest import calling
from hamcrest import is_
from hamcrest import is_not
from hamcrest import raises

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904


class TestPersistentExternalizableList(ExternalizationLayerTest):

    def test_externalize(self):
        obj = PersistentExternalizableList([1, 2, None, 3])

        assert_that(obj.toExternalList(), is_([1, 2, 3]))
        assert_that(obj.toExternalList(), is_(list))

    def test_values(self):
        obj = PersistentExternalizableList([1, 2, None, 3])

        assert_that(obj.values(), is_(obj))
        assert_that(list(iter(obj.values())), is_([1, 2, None, 3]))


class TestPersistentExternalizableWeakList(ExternalizationLayerTest):

    def test_mutate(self):

        obj = PersistentExternalizableWeakList()

        # Cannot set non-persistent objects
        assert_that(calling(obj.append).with_args(object()),
                    raises(AttributeError))

        pers = Persistent()
        obj.append(pers)
        assert_that(obj[0], is_(pers))

        pers2 = Persistent()
        obj[0] = pers2
        assert_that(obj[0], is_(pers2))
        assert_that(obj.count(pers2), is_(1))
        assert_that(obj.count(pers), is_(0))

        # iteration
        for x in obj:
            assert_that(x, is_(pers2))
        assert_that(obj.index(pers2), is_(0))

        assert_that(obj.pop(), is_(pers2))
        assert_that(calling(obj.pop), raises(IndexError))

        assert_that(obj, is_(obj))

        obj.append(pers2)
        # mul
        assert_that(obj * 2,
                    is_(PersistentExternalizableWeakList([pers2, pers2])))

        # imul
        obj *= 2
        assert_that(obj, is_(PersistentExternalizableWeakList([pers2, pers2])))

        obj.pop()
        # insert
        obj.insert(1, pers2)
        assert_that(obj, is_(PersistentExternalizableWeakList([pers2, pers2])))

        assert_that(obj, is_([pers2, pers2]))
        assert_that(obj, is_not([pers2, pers]))
        assert_that(obj, is_not(pers))
        obj.remove(pers2)
        obj.remove(pers2)
        assert_that(obj, is_([]))

class TestPersistentExternalizableDict(unittest.TestCase):

    def test_to_external_dict(self):
        class Obj(object):
            def toExternalObject(self, **kw):
                return "hi"
        d = PersistentExternalizableDictionary(key=Obj())
        assert_that(d.toExternalDictionary(), is_({'key': 'hi'}))

        # Now minimal
        d.__external_use_minimal_base__ = True
        assert_that(d.toExternalDictionary(), is_({'key': 'hi'}))

class TestGetPersistentState(unittest.TestCase):

    def test_without_jar(self):
        class P(object):
            _p_state = persistent.UPTODATE
            _p_jar = None

        assert_that(getPersistentState(P), is_(persistent.CHANGED))

    def test_with_proxy_p_changed(self):
        from zope.proxy import ProxyBase
        class P(object):
            _p_state = persistent.UPTODATE
            _p_jar = None

        class MyProxy(ProxyBase):

            @property
            def _p_changed(self):
                raise AttributeError()

            _p_state = _p_changed

        proxy = MyProxy(P())
        assert_that(getPersistentState(proxy), is_(persistent.CHANGED))

        setPersistentStateChanged(proxy) # Does nothing

    def test_with_proxy_p_state(self):
        from zope.proxy import ProxyBase
        class P(object):
            _p_state = persistent.CHANGED
            _p_jar = None

        class MyProxy(ProxyBase):

            @property
            def _p_state(self):
                raise AttributeError()

        proxy = MyProxy(P())
        assert_that(getPersistentState(proxy), is_(persistent.CHANGED))

        setPersistentStateChanged(proxy) # Does nothing


class TestWeakRef(unittest.TestCase):

    def test_to_externalObject(self):

        class P(Persistent):
            def toExternalObject(self, **kwargs):
                return {'a': 42}

        p = P()
        wref = PWeakRef(P())

        assert_that(wref.toExternalObject(), is_({'a': 42}))

    def test_to_externalOID(self):

        class P(Persistent):
            def toExternalOID(self, **kwargs):
                return b'abc'

        p = P()
        wref = PWeakRef(P())

        assert_that(wref.toExternalOID(), is_(b'abc'))
