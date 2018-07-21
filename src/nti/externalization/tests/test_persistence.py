#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import unittest
import warnings

import persistent
from persistent import Persistent
from persistent.wref import WeakRef as PWeakRef

from nti.externalization.persistence import PersistentExternalizableList
from nti.externalization.persistence import PersistentExternalizableDictionary
from nti.externalization.persistence import PersistentExternalizableWeakList
from nti.externalization.persistence import getPersistentState
from nti.externalization.persistence import setPersistentStateChanged
from nti.externalization.persistence import NoPickle
from nti.externalization.tests import ExternalizationLayerTest

from hamcrest import assert_that
from hamcrest import calling
from hamcrest import is_
from hamcrest import is_not
from hamcrest import raises
from hamcrest import has_length

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

    def test_equality(self):

        obj = PersistentExternalizableWeakList()
        pers = Persistent()
        obj.append(pers)

        assert_that(obj, is_([pers]))
        assert_that(obj, is_not([pers, pers]))
        assert_that(obj, is_not([]))
        assert_that(obj, is_not([self]))

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

        wref = PWeakRef(P())

        assert_that(wref.toExternalObject(), is_({'a': 42}))

    def test_to_externalOID(self):

        class P(Persistent):
            def toExternalOID(self, **kwargs):
                return b'abc'

        wref = PWeakRef(P())

        assert_that(wref.toExternalOID(), is_(b'abc'))

with warnings.catch_warnings():
    warnings.simplefilter('ignore')

    @NoPickle
    class GlobalPersistentNoPickle(Persistent):
        pass

class GlobalSubclassPersistentNoPickle(GlobalPersistentNoPickle):
    pass

@NoPickle
class GlobalNoPickle(object):
    pass

class GlobalSubclassNoPickle(GlobalNoPickle):
    pass

class GlobalNoPicklePersistentMixin1(GlobalNoPickle,
                                     Persistent):
    pass

class GlobalNoPicklePersistentMixin2(Persistent,
                                     GlobalNoPickle):
    pass

class GlobalNoPicklePersistentMixin3(GlobalSubclassNoPickle,
                                     Persistent):
    pass

class TestNoPickle(unittest.TestCase):

    def _persist_zodb(self, obj):
        from ZODB import DB
        from ZODB.MappingStorage import MappingStorage
        import transaction

        db = DB(MappingStorage())
        conn = db.open()
        try:
            conn.root.key = obj

            transaction.commit()
        finally:
            conn.close()
            db.close()
            transaction.abort()

    def _persist_pickle(self, obj):
        import pickle
        pickle.dumps(obj)

    def _persist_cpickle(self, obj):
        try:
            import cPickle
        except ImportError: # pragma: no cover
            # Python 3
            raise TypeError("Not allowed to pickle")
        else:
            cPickle.dumps(obj)

    def _all_persists_fail(self, factory):

        for meth in (self._persist_zodb,
                     self._persist_pickle,
                     self._persist_cpickle):
            __traceback_info__ = meth
            assert_that(calling(meth).with_args(factory()),
                        raises(TypeError, "Not allowed to pickle"))

    def test_plain_object(self):
        self._all_persists_fail(GlobalNoPickle)

    def test_subclass_plain_object(self):
        self._all_persists_fail(GlobalSubclassNoPickle)

    def test_persistent(self):
        self._all_persists_fail(GlobalPersistentNoPickle)

    def test_subclass_persistent(self):
        self._all_persists_fail(GlobalSubclassPersistentNoPickle)

    def test_persistent_mixin1(self):
        self._all_persists_fail(GlobalNoPicklePersistentMixin1)

    def test_persistent_mixin2(self):
        # Putting Persistent first works for zodb.
        factory = GlobalNoPicklePersistentMixin2
        self._persist_zodb(factory())
        # But plain pickle still fails
        with self.assertRaises(TypeError):
            self._persist_pickle(factory())


    def test_persistent_mixin3(self):
        self._all_persists_fail(GlobalNoPicklePersistentMixin3)

    def _check_emits_warning(self, kind):
        with warnings.catch_warnings(record=True) as w:
            NoPickle(kind)

        assert_that(w, has_length(1))
        assert_that(w[0].message, is_(RuntimeWarning))
        self.assertIn("Using @NoPickle",
                      str(w[0].message))

    def test_persistent_emits_warning(self):
        class P(Persistent):
            pass
        self._check_emits_warning(P)

    def test_getstate_emits_warning(self):
        class P(object):
            def __getstate__(self):
                "Does nothing"

        self._check_emits_warning(P)

    def test_reduce_emits_warning(self):
        class P(object):
            def __reduce__(self):
                "Does nothing"

        self._check_emits_warning(P)

    def test_reduce_ex_emits_warning(self):
        class P(object):
            def __reduce_ex__(self):
                "Does nothing"

        self._check_emits_warning(P)
