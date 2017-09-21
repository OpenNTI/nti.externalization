#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import sys
import unittest

import fudge
from zope import component
from zope import interface
from zope.interface.common.idatetime import IDate
from zope.testing.cleanup import CleanUp

from nti.externalization.tests import ExternalizationLayerTest
from nti.schema.interfaces import InvalidValue

from .. import internalization as INT
from ..interfaces import IClassObjectFactory
from ..interfaces import IMimeObjectFactory

from hamcrest import assert_that
from hamcrest import calling
from hamcrest import equal_to
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import has_property
from hamcrest import is_
from hamcrest import is_in
from hamcrest import is_not
from hamcrest import none
from hamcrest import raises
from hamcrest import same_instance

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
# pylint: disable=inherit-non-class


class TestDate(ExternalizationLayerTest):

    def test_exception(self):
        assert_that(calling(IDate).with_args('xx'), raises(InvalidValue))


class TestEvents(CleanUp,
                 unittest.TestCase):

    def _doIt(self, *args, **kwargs):
        from nti.externalization.internalization import notifyModified
        from nti.externalization.interfaces import ObjectModifiedFromExternalEvent

        event = notifyModified(*args, **kwargs)
        self.assertIsInstance(event, ObjectModifiedFromExternalEvent)
        return event

    def test_notify_event_kwargs(self):
        event = self._doIt(self, {'external': True}, a_key=42)
        self.assertEqual(event.kwargs, {'a_key': 42})
        assert_that(event, has_property('external_value', {'external': True}))

    def test_attributes(self):
        class IFoo(interface.Interface):
            attr_foo_1 = interface.Attribute("An attribute")
            attr_foo_2 = interface.Attribute("An attribute")

        class IBar(interface.Interface):
            attr_bar_1 = interface.Attribute("An attribute")
            attr_bar_2 = interface.Attribute("An attribute")
            attr_foo_1 = interface.Attribute("An attribute")

        @interface.implementer(IFoo, IBar)
        class FooBar(object):
            pass

        obj = FooBar()
        keys = {'attr_foo_1', 'attr_bar_1', 'attr_bar_2', 'no_iface_attr'}

        event = self._doIt(obj, {}, external_keys=keys)

        attributes = sorted(event.descriptions,
                            key=lambda attrs: attrs.interface)
        assert_that(attributes, has_length(3))
        assert_that(attributes[0].interface, is_(IBar))
        assert_that(attributes[0].attributes, is_(('attr_bar_1', 'attr_bar_2',)))

        assert_that(attributes[1].interface, is_(IFoo))
        assert_that(attributes[1].attributes, is_(('attr_foo_1',)))

        assert_that(attributes[2].interface, is_(none()))
        assert_that(attributes[2].attributes, is_(('no_iface_attr',)))


class TestFunctions(CleanUp,
                    unittest.TestCase):

    def test_search_for_factory_no_type(self):
        assert_that(INT.find_factory_for_class_name(''), is_(none()))

    def test_search_for_factory_updates_search_set(self):
        INT.LEGACY_FACTORY_SEARCH_MODULES.add(__name__)
        assert_that(INT.find_factory_for_class_name('testfunctions'), is_(none()))
        assert_that(sys.modules[__name__], is_in(INT.LEGACY_FACTORY_SEARCH_MODULES))
        assert_that(__name__, is_not(is_in(INT.LEGACY_FACTORY_SEARCH_MODULES)))

        TestFunctions.__external_can_create__ = True
        try:
            assert_that(INT.find_factory_for_class_name('testfunctions'), equal_to(TestFunctions))
        finally:
            del TestFunctions.__external_can_create__


class TestDefaultExternalizedObjectFactory(CleanUp,
                                           unittest.TestCase):

    @interface.implementer(IMimeObjectFactory, IClassObjectFactory)
    class TrivialFactory(object):

        def __init__(self, context):
            self.context = context

    def _callFUT(self, ext_obj):
        from ..internalization import default_externalized_object_factory_finder_factory as f
        return f(None)(ext_obj)

    def test_with_none(self):
        assert_that(self._callFUT(None), is_(none()))

    def test_with_empty_sequences_and_mappings_find_nothing(self):
        assert_that(self._callFUT({}), is_(none()))
        assert_that(self._callFUT(set()), is_(none()))
        assert_that(self._callFUT([]), is_(none()))
        assert_that(self._callFUT(()), is_(none()))

    @fudge.patch('nti.externalization.internalization.find_factory_for_class_name')
    def test_with_blank_mime_type(self, _):
        assert_that(self._callFUT({'MimeType': ''}), is_(none()))

    @fudge.patch('nti.externalization.internalization.find_factory_for_class_name')
    def test_with_black_class(self, _):
        assert_that(self._callFUT({'Class': ''}), is_(none()))

    @fudge.patch('nti.externalization.internalization.find_factory_for_class_name')
    def test_with_mime_type_no_registrations(self, _):
        assert_that(self._callFUT({'MimeType': 'mime'}), is_(none()))

    def test_with_class_no_registrations(self):
        assert_that(self._callFUT({'Class': 'no class'}), is_(none()))

    def test_with_mime_type_registered_adapter_by_name(self):
        ext = {'MimeType': 'mime'}
        component.provideAdapter(self.TrivialFactory,
                                 provides=IMimeObjectFactory,
                                 adapts=(object,),
                                 name=ext['MimeType'])

        assert_that(self._callFUT(ext), is_(self.TrivialFactory))

    def test_with_mime_type_registered_adapter_default(self):
        ext = {'MimeType': 'mime'}
        component.provideAdapter(self.TrivialFactory,
                                 provides=IMimeObjectFactory,
                                 adapts=(object,))

        assert_that(self._callFUT(ext), is_(self.TrivialFactory))

    def test_with_mime_type_registered_utility(self):
        ext = {'MimeType': 'mime'}
        component.provideUtility(self.TrivialFactory(None),
                                 provides=IMimeObjectFactory,
                                 name=ext['MimeType'])

        assert_that(self._callFUT(ext), is_(self.TrivialFactory))

    def test_with_class_registered_adapter(self):
        ext = {'Class': 'mime'}
        component.provideAdapter(self.TrivialFactory,
                                 provides=IClassObjectFactory,
                                 adapts=(object,),
                                 name=ext['Class'])

        assert_that(self._callFUT(ext), is_(self.TrivialFactory))


    def test_with_class_registered_utility(self):
        ext = {'Class': 'mime'}
        component.provideUtility(self.TrivialFactory(None),
                                 provides=IClassObjectFactory,
                                 name=ext['Class'])

        assert_that(self._callFUT(ext), is_(self.TrivialFactory))

class TestFindFactoryFor(TestDefaultExternalizedObjectFactory):

    def _callFUT(self, ext_obj):
        from ..internalization import find_factory_for
        return find_factory_for(ext_obj)

class TestResolveExternals(CleanUp,
                           unittest.TestCase):

    def test_both_attrs_optional(self):
        INT._resolve_externals(None, None, None)

    def test_resolvers_classmethod(self):
        class IO(object):

            @classmethod
            def a(cls, context, extobj, extvalue):
                assert extvalue == 1
                return 'a'

            @staticmethod
            def b(context, extobj, extvalue):
                assert extvalue == 2
                return 'b'

            __external_resolvers__ = {
                'a': a,
                'b': b,
                'c': None, # missing keys aren't called
            }

        ext_obj = {'a': 1, 'b': 2}

        INT._resolve_externals(IO(), None, ext_obj)
        assert_that(ext_obj, is_({'a': 'a', 'b': 'b'}))

    def test_resolvers_instancemethod(self):
        class IO(object):

            def a(self, context, extobj, extvalue):
                assert extvalue == 1
                return 'a'

            __external_resolvers__ = {
                'a': a,
            }

        ext_obj = {'a': 1, 'b': 2}

        INT._resolve_externals(IO(), None, ext_obj)
        assert_that(ext_obj, is_({'a': 'a', 'b': 2}))

    def test_oids_nothing_registered(self):
        class IO(object):
            __external_oids__ = ('a', 'b')

        ext_value = {'a': None}
        INT._resolve_externals(IO(), None, ext_value)
        assert_that(ext_value, is_({'a': None}))

    def test_oids_registered(self):
        from nti.externalization.interfaces import IExternalReferenceResolver

        class IO(object):
            __external_oids__ = ('a', 'b')

        class Resolver(object):

            def __init__(self, *args):
                pass

            def resolve(self, value):
                if value == 1:
                    return 'a'
                return 'b'

        component.provideAdapter(Resolver,
                                 provides=IExternalReferenceResolver,
                                 adapts=(object, object))

        ext_value = {'a': 1}
        INT._resolve_externals(IO(), self, ext_value)
        assert_that(ext_value, is_({'a': 'a'}))

        ext_value = {'a': [1]}
        INT._resolve_externals(IO(), self, ext_value)
        assert_that(ext_value, is_({'a': ['a']}))

        # tuples get wrapped too, which is weird and probably wrong
        # in general. it works because json produces plain lists on reading

        ext_value = {'a': (1,)}
        INT._resolve_externals(IO(), self, ext_value)
        assert_that(ext_value, is_({'a': 'b'}))


class TestUpdateFromExternaObject(CleanUp,
                                  unittest.TestCase):

    def _callFUT(self, *args, **kwargs):
        return INT.update_from_external_object(*args, **kwargs)

    def test_update_sequence_of_primitives(self):
        ext = [1, 2, 3]
        result = self._callFUT(None, ext)
        assert_that(result, is_not(same_instance(ext)))
        assert_that(result, is_(ext))

    def test_update_empty_mapping_no_required_updater(self):
        ext = {}
        result = self._callFUT(self, ext)
        assert_that(result, is_(same_instance(self)))
        assert_that(ext, is_({}))

    def test_update_empty_mapping_with_required_updater(self):
        ext = {}
        with self.assertRaises(LookupError):
            self._callFUT(self, ext, require_updater=True)

    def test_update_mapping_of_primitives_and_sequences(self):
        b = [1, 2, 3]
        ext = {'a': 1, 'b': b, 'c': {}}
        result = self._callFUT(self, ext)
        assert_that(result, is_(same_instance(self)))

        assert_that(ext, is_({'a': 1, 'b': b, 'c': {}}))
        # This should change.
        assert_that(ext['b'], is_not(same_instance(b)))

    def test_update_mapping_with_update_on_contained_object(self):
        class ContainedObject(object):
            updated = False
            def updateFromExternalObject(self, ext):
                self.updated = True
                return True

        contained = ContainedObject()
        self._callFUT(contained, {})
        assert_that(contained, has_property('updated', True))

    def test_update_mapping_with_update_on_contained_object_ignored(self):

        class ContainedObject(object):
            updated = False
            __ext_ignore_updateFromExternalObject__ = True

            def updateFromExternalObject(self, ext):
                raise AssertionError("Should not be called")

        contained = ContainedObject()
        self._callFUT(contained, {})
        assert_that(contained, has_property('updated', False))

    def test_update_mapping_with_context_arg(self):
        class ContainedObject(object):
            updated = False
            def updateFromExternalObject(self, ext, context):
                self.updated = True
                return True

        contained = ContainedObject()
        self._callFUT(contained, {})
        assert_that(contained, has_property('updated', True))

    def test_update_mapping_with_ds_arg(self):
        class ContainedObject(object):
            updated = False
            def updateFromExternalObject(self, ext, dataserver):
                self.updated = True
                return True

        contained = ContainedObject()
        self._callFUT(contained, {})
        assert_that(contained, has_property('updated', True))

    def test_update_mapping_with_kwargs(self):
        class ContainedObject(object):
            updated = False
            args = None
            def updateFromExternalObject(self, ext, **kwargs):
                self.updated = True
                self.args = kwargs
                return True

        contained = ContainedObject()
        self._callFUT(contained, {})
        assert_that(contained, has_property('updated', True))
        assert_that(contained, has_property('args', {'context': None}))

    def test_update_mapping_with_registered_factory(self):
        ext = {'MimeType': 'mime'}
        ext_wrapper = {'a': ext}

        class TrivialFactory(object):

            def __init__(self, ctx):
                pass

            def __call__(self):
                return self

        component.provideAdapter(TrivialFactory,
                                 provides=IMimeObjectFactory,
                                 adapts=(object,))

        self._callFUT(None, ext_wrapper)

        assert_that(ext_wrapper, has_entry('a', is_(TrivialFactory)))
