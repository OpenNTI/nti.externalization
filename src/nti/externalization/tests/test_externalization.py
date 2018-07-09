#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import datetime
import json
from numbers import Number
import unittest


from ZODB.broken import Broken
import persistent
from zope import component
from zope import interface
from zope.dublincore import interfaces as dub_interfaces
from zope.testing.cleanup import CleanUp

from nti.externalization.externalization import stripSyntheticKeysFromExternalDictionary
from nti.testing.matchers import verifiably_provides
from nti.testing.matchers import is_true
from nti.testing.matchers import is_false

from . import ExternalizationLayerTest
from ..datastructures import ExternalizableDictionaryMixin
from ..datastructures import ExternalizableInstanceDict
from ..externalization import NonExternalizableObjectError
from ..externalization.replacers import DevmodeNonExternalizableObjectReplacementFactory
from ..externalization import catch_replace_action
from ..externalization import choose_field
from ..externalization import isSyntheticKey
from ..externalization import removed_unserializable
from ..extension_points import set_external_identifiers
from ..externalization import to_standard_external_dictionary
from ..externalization import toExternalObject
from ..externalization.standard_fields import get_creator
from ..interfaces import EXT_REPR_JSON
from ..interfaces import EXT_REPR_YAML
from ..interfaces import IExternalObject
from ..interfaces import IExternalObjectDecorator
from ..interfaces import LocatedExternalDict
from ..interfaces import LocatedExternalList
from ..interfaces import StandardExternalFields
from ..oids import fromExternalOID
from ..oids import toExternalOID
from ..persistence import NoPickle
from ..persistence import PersistentExternalizableWeakList
from ..persistence import getPersistentState
from ..representation import to_external_representation
from ..testing import assert_does_not_pickle

from hamcrest import assert_that
from hamcrest import calling
from hamcrest import contains
from hamcrest import has_entry
from hamcrest import has_items
from hamcrest import has_key
from hamcrest import is_
from hamcrest import is_not
from hamcrest import none
from hamcrest import raises
from hamcrest import same_instance
from hamcrest import has_property as has_attr

try:
    from collections import UserDict
except ImportError:
    from UserDict import UserDict # Python 2


# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
# pylint: disable=attribute-defined-outside-init,inherit-non-class

does_not = is_not


class TestFunctions(ExternalizationLayerTest):

    def test_getPersistentState(self):
        # Non-persistent objects are changed
        assert_that(getPersistentState(None), is_(persistent.CHANGED))
        assert_that(getPersistentState(object()), is_(persistent.CHANGED))

        # Object with _p_changed are that
        class T(object):
            _p_changed = True

        assert_that(getPersistentState(T()), is_(persistent.CHANGED))
        T._p_changed = False
        assert_that(getPersistentState(T()), is_(persistent.UPTODATE))

        # _p_state is trumped by _p_changed
        T._p_state = None
        assert_that(getPersistentState(T()), is_(persistent.UPTODATE))

        # _p_state is used if _p_changed isn't
        del T._p_changed
        T._p_state = 42
        assert_that(getPersistentState(T()), is_(42))

        def f(unused_s):
            return 99
        T.getPersistentState = f
        del T._p_state
        assert_that(getPersistentState(T()), is_(99))

    def test_toExternalID(self):
        class T(object):
            pass
        assert_that(toExternalOID(T()), is_(None))

        t = T()
        t._p_oid = b'\x00\x01'
        assert_that(toExternalOID(t), is_(b'0x01'))

        t._p_jar = t
        db = T()
        db.database_name = 'foo'
        t.db = lambda: db
        del t._v_to_external_oid # pylint:disable=no-member
        assert_that(toExternalOID(t), is_(b'0x01:666f6f'))

        assert_that(fromExternalOID('0x01:666f6f')[0],
                    is_(b'\x00\x00\x00\x00\x00\x00\x00\x01'))
        assert_that(fromExternalOID('0x01:666f6f')[0], is_(bytes))
        assert_that(fromExternalOID('0x01:666f6f')[1], is_(b'foo'))

        # Given a plain OID, we return just the plain OID
        oid = b'\x00\x00\x00\x00\x00\x00\x00\x01'
        assert_that(fromExternalOID(oid),
                    contains(same_instance(oid), '', None))

    def test_hookable_set_external_identifiers(self):
        assert_that(set_external_identifiers,
                    has_attr('implementation', is_not(none())))

    def test_set_external_identifiers(self):
        class T(object):
            def toExternalOID(self):
                return b'abc'

        result = {}
        set_external_identifiers(T(), result)
        assert_that(result, is_({'OID': u'abc', 'NTIID': u'abc'}))

    def test_to_external_representation_none_handling(self):
        d = {'a': 1, 'None': None}
        # JSON keeps None
        assert_that(json.loads(to_external_representation(d, EXT_REPR_JSON)),
                    is_(d))

    def test_to_external_representation_yaml(self):
        l = LocatedExternalList()
        l.append(LocatedExternalDict(k='v'))

        class SubUnicode(str if bytes is not str else unicode):
            pass
        l.append(LocatedExternalDict(k2=SubUnicode(u'foo')))

        assert_that(to_external_representation(l, EXT_REPR_YAML),
                    is_('- {k: v}\n- {k2: foo}\n'))

    def test_external_class_name(self):
        class C(UserDict, ExternalizableDictionaryMixin):
            pass
        assert_that(toExternalObject(C()), has_entry('Class', 'C'))
        C.__external_class_name__ = 'ExternalC'
        assert_that(toExternalObject(C()), has_entry('Class', 'ExternalC'))

    def test_broken(self):
        # Without the devmode hooks
        gsm = component.getGlobalSiteManager()
        gsm.unregisterAdapter(factory=DevmodeNonExternalizableObjectReplacementFactory,
                              required=())
        gsm.unregisterAdapter(factory=DevmodeNonExternalizableObjectReplacementFactory,
                              required=(interface.Interface,))

        assert_that(toExternalObject(Broken(), registry=gsm),
                    has_entry("Class", "NonExternalizableObject"))

        assert_that(toExternalObject([Broken()], registry=gsm),
                    has_items(has_entry("Class", "NonExternalizableObject")))

    def test_catching_component(self):
        class MyCustomException(Exception):
            pass

        class Raises(object):
            def toExternalObject(self, **unused_kwargs):
                raise MyCustomException

        assert_that(toExternalObject([Raises()],
                                     catch_components=(MyCustomException,),
                                     catch_component_action=catch_replace_action),
                    is_([catch_replace_action(None, None)]))

        # Default doesn't catch
        assert_that(calling(toExternalObject).with_args([Raises()]),
                    raises(MyCustomException))


    def test_removed_unserializable(self):
        import warnings
        marker = object()
        ext = {'x': 1, 'y': [1, 2, marker], 'z': marker,
               'a': {3, 4}, 'b': {'c': (marker, 1)}}
        with warnings.catch_warnings(record=True): # removed_unserializable is deprecated
            assert_that(removed_unserializable((1, 2, 3)),
                        is_([1, 2, 3]))

            assert_that(removed_unserializable([[(1, 2, 3)]]),
                        is_([[[1, 2, 3]]]))
            removed_unserializable(ext)
        assert_that(ext, has_entry('x', is_(1)))
        assert_that(ext, has_entry('y', is_([1, 2, None])))
        assert_that(ext, has_entry('a', is_([3, 4])))
        assert_that(ext, has_entry('z', is_(none())))
        assert_that(ext, has_entry('b', has_entry('c', is_([None, 1]))))


    def test_devmode_non_externalizable_object_replacer(self):
        assert_that(calling(DevmodeNonExternalizableObjectReplacementFactory(None)).with_args(self),
                    raises(NonExternalizableObjectError, "Asked to externalize non-externalizable"))


    def test_stripSyntheticKeysFromExternalDictionary(self):
        assert_that(stripSyntheticKeysFromExternalDictionary({'Creator': 42}),
                    is_({}))

    def test_isSyntheticKey(self):
        assert_that(isSyntheticKey('OID'), is_true())
        assert_that(isSyntheticKey('key'), is_false())

    def test_choose_field_POSKeyError_not_ignored(self):
        from ZODB.POSException import POSKeyError
        class Raises(object):
            def __getattr__(self, name):
                raise POSKeyError(name)

        with self.assertRaises(POSKeyError):
            choose_field({}, Raises(), u'ext_name',
                         fields=('a', 'b'))

    def test_choose_field_system_user_not_special(self):
        from zope.security.interfaces import IPrincipal
        from zope.security.management import system_user

        @interface.implementer(IPrincipal)
        class MySystemUser(object):
            id = system_user.id


        class WithSystemUser(object):
            user = MySystemUser()

        result = {}
        choose_field(result, WithSystemUser,
                     StandardExternalFields.CREATOR, fields=('user',))
        assert_that(result, is_({StandardExternalFields.CREATOR: WithSystemUser.user}))

    def test_get_creator_system_user(self):
        from nti.externalization.externalization import SYSTEM_USER_NAME
        from zope.security.interfaces import IPrincipal
        from zope.security.management import system_user

        @interface.implementer(IPrincipal)
        class MySystemUser(object):
            id = system_user.id


        class WithSystemUser(object):
            creator = MySystemUser()

        result = {}

        value = get_creator(WithSystemUser, None, result)
        assert_that(value, is_(SYSTEM_USER_NAME))
        assert_that(result, is_({StandardExternalFields.CREATOR: SYSTEM_USER_NAME}))



class TestDecorators(CleanUp,
                     unittest.TestCase):

    def test_decorate_external_mapping(self):
        from nti.externalization.interfaces import IExternalMappingDecorator
        from nti.externalization.externalization import decorate_external_mapping
        class IRequest(interface.Interface):
            pass

        @interface.implementer(IRequest)
        class Request(object):
            pass


        @component.adapter(object)
        @interface.implementer(IExternalMappingDecorator)
        class Decorator(object):

            def __init__(self, result):
                pass

            def decorateExternalMapping(self, orig_object, result):
                result['decorated'] = True

        @component.adapter(object, IRequest)
        @interface.implementer(IExternalMappingDecorator)
        class RequestDecorator(object):
            def __init__(self, result, request):
                pass

            def decorateExternalMapping(self, orig_object, result):
                result['req_decorated'] = True


        gsm = component.getGlobalSiteManager()
        gsm.registerSubscriptionAdapter(Decorator)
        gsm.registerSubscriptionAdapter(RequestDecorator)

        result = {}
        decorate_external_mapping(self, result)
        assert_that(result, is_({'decorated': True}))

        result = {}
        decorate_external_mapping(self, result, request=Request())
        assert_that(result, is_({'decorated': True, 'req_decorated': True}))

    def test_decorators_for_requests_toExternalObject(self):
        class IRequest(interface.Interface):
            pass
        @interface.implementer(IRequest)
        class Request(object):
            pass

        @component.adapter(object, IRequest)
        @interface.implementer(IExternalObjectDecorator)
        class Decorator(object):

            decorated = []

            def __init__(self, orig_object, request):
                pass

            def decorateExternalObject(self, *args):
                Decorator.decorated.append(args)

        component.getGlobalSiteManager().registerSubscriptionAdapter(Decorator)

        toExternalObject({}, request=Request())

        assert_that(Decorator.decorated,
                    is_([({}, {})]))

        component.getGlobalSiteManager().unregisterSubscriptionAdapter(Decorator)


class TestPersistentExternalizableWeakList(unittest.TestCase):

    def test_plus_extend(self):
        class C(persistent.Persistent):
            pass
        c1 = C()
        c2 = C()
        c3 = C()
        l = PersistentExternalizableWeakList()
        l += [c1, c2, c3]
        assert_that(l, is_([c1, c2, c3]))
        assert_that([c1, c2, c3], is_(l))

        # Adding things that are already weak refs.
        l += l
        assert_that(l, is_([c1, c2, c3, c1, c2, c3]))

        l = PersistentExternalizableWeakList()
        l.extend([c1, c2, c3])
        assert_that(l, is_([c1, c2, c3]))
        assert_that(l, is_(l))


class TestExternalizableInstanceDict(ExternalizationLayerTest):

    class C(ExternalizableInstanceDict):

        def __init__(self):
            super(TestExternalizableInstanceDict.C, self).__init__()
            self.A1 = None
            self.A2 = None
            self.A3 = None
            self._A4 = None
            # notice no A5

    def test_simple_roundtrip(self):
        obj = self.C()
        # Things that are excluded by default
        obj.containerId = 'foo'
        obj.creator = 'foo2'
        obj.id = 'id'

        # Things that should go
        obj.A1 = 1
        obj.A2 = "2"

        # Things that should be excluded dynamically
        # Functions used to be specifically excluded, but not anymore
        # def l(): pass
        # obj.A3 = l
        obj._A4 = 'A'
        self.A5 = "Not From Init"

        ext = toExternalObject(obj)

        newObj = self.C()
        newObj.updateFromExternalObject(ext)

        for attr in set(obj._excluded_out_ivars_) | set(['A5']):
            assert_that(newObj, does_not(has_attr(attr)))
        assert_that(ext, does_not(has_key("A5")))
        # assert_that( ext, does_not( has_key( 'A3' ) ) )
        assert_that(ext, does_not(has_key('_A4')))
        assert_that(newObj.A1, is_(1))
        assert_that(newObj.A2, is_("2"))


class TestToExternalObject(ExternalizationLayerTest):

    def test_decorator(self):
        class ITest(interface.Interface): # pylint:disable=inherit-non-class
            pass

        @interface.implementer(ITest, IExternalObject)
        class Test(object):
            def toExternalObject(self, **unused_kwargs):
                return {}

        test = Test()
        assert_that(toExternalObject(test), is_({}))

        @interface.implementer(IExternalObjectDecorator)
        class Decorator(object):
            def __init__(self, o):
                pass

            def decorateExternalObject(self, obj, result):
                result['test'] = obj

        component.provideSubscriptionAdapter(Decorator, adapts=(ITest,))

        assert_that(toExternalObject(test), is_({'test': test}))

    def test_memo(self):

        @interface.implementer(IExternalObject)
        class Test(object):

            def toExternalObject(self, **unused_kwargs):
                # a new dict each time we're called;
                # we only want to be called once
                return {}

        test = Test()
        tests = [test, test]

        ext_val = toExternalObject(tests)
        assert_that(ext_val[0],
                    is_(same_instance(ext_val[1])))

    def test_memo_recursive(self):

        @interface.implementer(IExternalObject)
        class Test(object):
            children = []

            def toExternalObject(self, **unused_kwargs):
                # a new dict each time we're called;
                # we only want to be called once
                result = {}
                for n, x in enumerate(self.children or ()):
                    result[str(n)] = toExternalObject(x)
                return result

        test = Test()
        test.children = [Test(), test]
        ext_val = toExternalObject(test)
        assert_that(ext_val, has_entry('0', is_({})))
        assert_that(ext_val, has_entry('1', has_entry('Class', 'Test')))

    def test_memo_changes_names(self):
        # if we're called with a different name,
        # the memo changes too
        @interface.implementer(IExternalObject)
        class Test(object):
            def toExternalObject(self, **unused_kwargs):
                # a new dict each time we're called;
                # we only want to be called once
                return {}

        @interface.implementer(IExternalObject)
        class Parent(object):
            def __init__(self):
                self.test = Test()

            def toExternalObject(self, **unused_kwargs):

                return [toExternalObject(self.test),
                        toExternalObject(self.test, name="other")]

        ext_val = toExternalObject(Parent())
        assert_that(ext_val[0],
                    is_not(same_instance(ext_val[1])))

    def test_to_stand_dict_uses_dubcore(self):

        @interface.implementer(dub_interfaces.IDCTimes)
        class X(object):
            created = datetime.datetime.now()
            modified = datetime.datetime.now()

        assert_that(X(), verifiably_provides(dub_interfaces.IDCTimes))

        ex_dic = to_standard_external_dictionary(X())
        assert_that(ex_dic,
                    has_entry(StandardExternalFields.LAST_MODIFIED, is_(Number)))
        assert_that(ex_dic,
                    has_entry(StandardExternalFields.CREATED_TIME, is_(Number)))


    def test_stand_ext_props(self):
        self.assertIn(StandardExternalFields.CREATED_TIME,
                      StandardExternalFields.EXTERNAL_KEYS)


        self.assertIn('CREATED_TIME',
                      StandardExternalFields.ALL)

    def test_to_stand_dict_merges(self):
        obj = {}
        result = to_standard_external_dictionary(obj, mergeFrom={'abc': 42})
        assert_that(result, is_({'abc': 42, 'Class': 'dict'}))

    def test_to_minimal_external_dict(self):
        from nti.externalization.externalization import to_minimal_standard_external_dictionary
        class O(object):
            mime_type = 'application/thing'

        result = to_minimal_standard_external_dictionary(O(), mergeFrom={'abc': 42})
        assert_that(result, is_({'abc': 42, 'Class': 'O', 'MimeType': 'application/thing'}))

        result = to_standard_external_dictionary(O(), mergeFrom={'abc': 42})
        assert_that(result, is_({'abc': 42, 'Class': 'O', 'MimeType': 'application/thing'}))

    def test_name_falls_back_to_standard_name(self):
        toExternalObject(self, name='a name')

    def test_toExternalList(self):
        class ExtList(object):
            def toExternalList(self):
                return [42]

        assert_that(toExternalObject(ExtList()), is_([42]))

    def test_sequence_of_primitives(self):
        assert_that(toExternalObject([42]), is_([42]))

    def test_mapping_of_non_primitives(self):
        class Foo(object):
            def toExternalObject(self, **kwargs):
                return 42
        assert_that(toExternalObject({'key': Foo()}),
                    is_({'key': 42}))

    def test_decorate_callback(self):
        # decorate_callback doesn't make much sense.
        calls = []
        def callback(x, y):
            calls.append((x, y))

        # Not by default
        obj = {}
        toExternalObject(obj, decorate_callback=callback)
        assert_that(calls, is_([]))

        # It's only called when we turn off decoration...
        # and it gets passed to every externalizer, which is also
        # weird. It also gets called *twice* for mapping types, which
        # seems wrong too.
        toExternalObject(obj, decorate_callback=callback,
                         decorate=False)
        assert_that(calls, is_([(obj, obj),
                                (obj, obj)]))

    def test_catch_components_top_level(self):
        class MyException(Exception):
            pass

        class Foo(object):
            def toExternalObject(self, *args, **kwargs):
                raise MyException()


        assert_that(calling(toExternalObject).with_args(Foo(), catch_components=MyException),
                    raises(MyException))

    def test_recursive_call_name(self):

        class Top(object):

            def toExternalObject(self, **kwargs):
                assert_that(kwargs, has_entry('name', 'TopName'))

                middle = Middle()

                return toExternalObject(middle) # No name argument

        class Middle(object):

            def toExternalObject(self, **kwargs):
                assert_that(kwargs, has_entry('name', 'TopName'))

                bottom = Bottom()

                return toExternalObject(bottom, name='BottomName')

        class Bottom(object):

            def toExternalObject(self, **kwargs):
                assert_that(kwargs, has_entry('name', 'BottomName'))

                return "Bottom"

        assert_that(toExternalObject(Top(), name='TopName'),
                    is_("Bottom"))

    def test_recursive_call_minimizes_dict(self):

        class O(object):
            ext_obj = None

            def toExternalObject(self, **kwargs):
                return {"Hi": 42,
                        "kid": toExternalObject(self.ext_obj)}

        top = O()
        child = O()
        top.ext_obj = child
        child.ext_obj = top

        result = toExternalObject(top)
        assert_that(result,
                    is_({'Hi': 42,
                         'kid': {'Hi': 42,
                                 'kid': {u'Class': 'O'}}}))

    def test_recursive_call_on_creator(self):
        # Make sure that we properly handle recursive calls on a
        # field we want to pre-convert to a str, creator.

        class O(object):
            def __init__(self):
                self.creator = self

            def __str__(self):
                return "creator"

            def toExternalObject(self, *args, **kwargs):
                return to_standard_external_dictionary(self)

        result = toExternalObject(O())
        assert_that(result, has_entry('Creator', 'creator'))

        # Serialize to JSON too to make sure we get the right thing
        from ..representation import to_json_representation_externalized
        s = to_json_representation_externalized(result)
        assert_that(s, is_('{"Class": "O", "Creator": "creator"}'))


@NoPickle
class DoNotPickleMe(object):
    pass


class TestNoPickle(unittest.TestCase):

    def test_decorator(self):
        assert_does_not_pickle(DoNotPickleMe())
