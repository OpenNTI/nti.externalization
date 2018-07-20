#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import unittest
import warnings

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
from hamcrest import contains
from hamcrest import contains_string
from hamcrest import equal_to
from hamcrest import greater_than_or_equal_to
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
        assert_that(attributes[0].attributes, is_({'attr_bar_1', 'attr_bar_2',}))

        assert_that(attributes[1].interface, is_(IFoo))
        assert_that(attributes[1].attributes, is_({'attr_foo_1',}))

        assert_that(attributes[2].interface, is_(none()))
        assert_that(attributes[2].attributes, is_({'no_iface_attr',}))


class TestFunctions(CleanUp,
                    unittest.TestCase):

    def test_search_for_factory_no_type(self):
        assert_that(INT.find_factory_for_class_name(''), is_(none()))

    def test_search_for_factory_updates_search_set(self):
        from zope.testing.loggingsupport import InstalledHandler

        with warnings.catch_warnings(record=True):
            INT.register_legacy_search_module(__name__)
            # The cache is initialized lazily
            assert_that(__name__, is_in(INT.LEGACY_FACTORY_SEARCH_MODULES))

            assert_that(INT.find_factory_for_class_name('testfunctions'), is_(none()))

            # And we have been examined and removed
            assert_that(__name__, is_not(is_in(INT.LEGACY_FACTORY_SEARCH_MODULES)))
            assert_that(INT.LEGACY_FACTORY_SEARCH_MODULES, is_(set()))

            # Now we're going to fiddle with our public classes and try again.
            # This will force re-registration to occur. Note we do this before
            # we make ourself public, so that we can assert it's lazy
            INT.register_legacy_search_module(__name__)

            TestFunctions.__external_can_create__ = True
            handler = InstalledHandler(INT.__name__)
            try:
                assert_that(INT.find_factory_for_class_name('testfunctions'),
                            equal_to(TestFunctions))

                # Now lets register ourself again, to trigger the logged warnings.
                assert_that(__name__, is_not(is_in(INT.LEGACY_FACTORY_SEARCH_MODULES)))
                assert_that(INT.LEGACY_FACTORY_SEARCH_MODULES, is_(set()))

                # Now we're going to fiddle with our public classes and try again.
                # This will force re-registration to occur. Note we do this before
                # we make ourself public, so that we can assert it's lazy
                INT.register_legacy_search_module(__name__)

                assert_that(INT.find_factory_for_class_name('testfunctions'),
                            equal_to(TestFunctions))
                # case doesn't matter
                assert_that(INT.find_factory_for_class_name('TeStfUnctIons'),
                            equal_to(TestFunctions))

                assert_that(str(handler),
                            contains_string("Found duplicate registration for legacy search path."))

                assert_that(INT.legacy_factories.count_legacy_classes_found(),
                            greater_than_or_equal_to)

            finally:
                del TestFunctions.__external_can_create__
                handler.uninstall()


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

    def test_externalized_object_factory_finder(self):
        from ..interfaces import IExternalizedObjectFactoryFinder

        class Foo(TestDefaultExternalizedObjectFactory.TrivialFactory):

            def find_factory(self, e):
                return self

        component.provideAdapter(Foo,
                                 provides=IExternalizedObjectFactoryFinder,
                                 adapts=(dict,))

        result = self._callFUT({})
        assert_that(result, is_(Foo))


class TestResolveExternals(CleanUp,
                           unittest.TestCase):

    def test_both_attrs_optional(self):
        INT.externals.resolve_externals(None, None, None)

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

        INT.externals.resolve_externals(IO(), None, ext_obj)
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

        INT.externals.resolve_externals(IO(), None, ext_obj)
        assert_that(ext_obj, is_({'a': 'a', 'b': 2}))

    def test_oids_nothing_registered(self):
        class IO(object):
            __external_oids__ = ('a', 'b')

        ext_value = {'a': None}
        INT.externals.resolve_externals(IO(), None, ext_value)
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
        INT.externals.resolve_externals(IO(), self, ext_value)
        assert_that(ext_value, is_({'a': 'a'}))

        ext_value = {'a': [1]}
        INT.externals.resolve_externals(IO(), self, ext_value)
        assert_that(ext_value, is_({'a': ['a']}))

        # tuples get wrapped too, which is weird and probably wrong
        # in general. it works because json produces plain lists on reading

        ext_value = {'a': (1,)}
        INT.externals.resolve_externals(IO(), self, ext_value)
        assert_that(ext_value, is_({'a': 'b'}))


class TestUpdateFromExternaObject(CleanUp,
                                  unittest.TestCase):

    def _callFUT(self, *args, **kwargs):
        return INT.update_from_external_object(*args, **kwargs)

    def test_update_sequence_of_primitives(self):
        ext = [1, 2, 3]
        result = self._callFUT(None, ext)
        assert_that(result, is_(same_instance(ext)))
        assert_that(result, is_([1, 2, 3]))

    def test_update_sequence_of_primitives_persistent_contained(self):
        from persistent import Persistent
        ext = [1, 2, 3]
        class O(Persistent):
            pass
        contained = O()
        result = self._callFUT(contained, ext)
        assert_that(result, is_(same_instance(ext)))
        assert_that(result, is_([1, 2, 3]))
        assert_that(contained,
                    has_property('_v_updated_from_external_source',
                                 is_(same_instance(ext))))

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
        assert_that(ext['b'], is_(same_instance(b)))

    def test_update_mapping_with_update_on_contained_object(self):
        class ContainedObject(object):
            updated = False
            def updateFromExternalObject(self, ext):
                self.updated = True
                return True

        contained = ContainedObject()
        self._callFUT(contained, {})
        assert_that(contained, has_property('updated', True))

    def test_update_persistent_object(self):
        from persistent import Persistent
        external = {}

        class Obj(Persistent):
            updated = False
            def updateFromExternalObject(self, ext):
                self.updated = True

        contained = Obj()
        self._callFUT(contained, external)
        assert_that(contained, has_property('updated', True))
        assert_that(contained,
                    has_property('_v_updated_from_external_source',
                                 is_(same_instance(external))))


    def test_update_mapping_with_update_on_contained_object_ignored(self):

        class ContainedObjectIgnoreDeprecated(object):
            updated = False
            __ext_ignore_updateFromExternalObject__ = True

            def updateFromExternalObject(self, ext):
                raise AssertionError("Should not be called")

        contained = ContainedObjectIgnoreDeprecated()
        with warnings.catch_warnings(record=True) as w:
            self._callFUT(contained, {})
        assert_that(contained, has_property('updated', False))
        assert_that(w, has_length(1))

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
        class ContainedObjectDSArg(object):
            updated = False
            def updateFromExternalObject(self, ext, dataserver):
                self.updated = True
                return True

        contained = ContainedObjectDSArg()
        self._callFUT(contained, {})
        assert_that(contained, has_property('updated', True))

    def test_update_mapping_with_kwargs_only(self):
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

    def test_update_mapping_with_kwargs_context(self):
        class ContainedObject(object):
            updated = False
            args = None
            context = None
            def updateFromExternalObject(self, ext, context=None, **kwargs):
                self.updated = True
                self.args = kwargs
                self.context = context
                return True

        contained = ContainedObject()
        self._callFUT(contained, {}, context=42)
        assert_that(contained, has_property('updated', True))
        assert_that(contained, has_property('args', {}))
        assert_that(contained, has_property('context', 42))

    def test_update_mapping_with_unused_kwargs(self):
        class ContainedObject(object):
            updated = False
            args = None
            def updateFromExternalObject(self, ext, **unused_kwargs):
                self.updated = True
                self.args = unused_kwargs
                return True

        contained = ContainedObject()
        self._callFUT(contained, {})
        assert_that(contained, has_property('updated', True))
        assert_that(contained, has_property('args', {}))

    def test_update_mapping_with_ds_arg_kwarg(self):
        class ContainedObjectDSArg(object):
            updated = False
            def updateFromExternalObject(self, ext, dataserver=None):
                self.updated = True
                return True

        contained = ContainedObjectDSArg()
        with warnings.catch_warnings(record=True) as w:
            self._callFUT(contained, {})
        assert_that(contained, has_property('updated', True))
        __traceback_info__ = [repr(i.__dict__) for i in w]
        assert_that(w, has_length(1))

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


class TestNewFromExternalObject(CleanUp,
                                unittest.TestCase):

    def _callFUT(self, external_object):
        return INT.new_from_external_object(external_object)

    def test_no_factory(self):
        from zope.interface.interfaces import ComponentLookupError
        with self.assertRaises(ComponentLookupError):
            self._callFUT({})

    def test_new_mapping_with_registered_factory(self):
        ext = {'MimeType': 'mime'}
        ext_wrapper = {'a': ext, 'MimeType': 'type'}

        class TrivialFactory(object):

            def __init__(self, ctx):
                pass

            def __call__(self):
                return self

        component.provideAdapter(TrivialFactory,
                                 provides=IMimeObjectFactory,
                                 adapts=(object,))

        self._callFUT(ext_wrapper)

        assert_that(ext_wrapper, has_entry('a', is_(TrivialFactory)))


class TestValidateFieldValue(CleanUp,
                             unittest.TestCase):

    class Bag(object):
        pass

    def _callFUT(self, field, value, bag=None):
        bag = bag or self.Bag()
        setter = INT.validate_field_value(bag, field.__name__, field, value)
        return setter, bag

    def test_schema_not_provided_adapts(self):
        from zope.schema import Object

        class IThing(interface.Interface):
            pass

        field = Object(IThing, __name__='field')

        class O(object):

            def __conform__(self, iface):
                assert iface is IThing
                interface.alsoProvides(self, iface)
                return self

        setter, bag = self._callFUT(field, O())

        setter()
        assert_that(bag, has_property('field', is_(O)))

    def test_wrong_type_adapts(self):
        from zope.schema import Field
        from zope.schema.interfaces import WrongType
        from zope.schema.interfaces import ValidationError

        class Iface(interface.Interface):
            pass
        @interface.implementer(Iface)
        class TheType(object):
            pass

        class MyField(Field):
            _type = TheType

        class MyObject(object):
            pass

        field = MyField(__name__='field')

        with self.assertRaises(WrongType):
            self._callFUT(field, MyObject())

        class MyConformingObject(object):
            def __conform__(self, iface):
                assert iface is Iface
                interface.alsoProvides(self, iface)
                # Note that we have to return this exact type, other wise
                # we get stuck in an infinite loop.
                return TheType()

        setter, bag = self._callFUT(field, MyConformingObject())
        setter()
        assert_that(bag, has_property('field', is_(TheType)))

        class MyInvalidObject(object):
            def __conform__(self, iface):
                raise ValidationError()

        with self.assertRaises(ValidationError) as exc:
            self._callFUT(field, MyInvalidObject())

        assert_that(exc.exception, has_property('field', field))

    def test_wrong_contained_type_object_field_adapts(self):
        from zope.schema import Object
        from zope.schema import List


        class IThing(interface.Interface):
            pass

        field = List(value_type=Object(IThing), __name__='field')

        class O(object):
            def __conform__(self, iface):
                assert iface is IThing, iface
                interface.alsoProvides(self, iface)
                return self

        setter, bag = self._callFUT(field, [O()])

        setter()
        assert_that(bag, has_property('field', contains(is_(O))))

    def test_wrong_contained_type_object_field_adapts_fails(self):
        from zope.schema.interfaces import WrongContainedType
        from zope.schema import Object
        from zope.schema import List


        class IThing(interface.Interface):
            pass

        field = List(value_type=Object(IThing), __name__='field')

        class N(object):
            def __conform__(self, iface):
                raise TypeError()

        with self.assertRaises(WrongContainedType):
            self._callFUT(field, [N()])

    def test_wrong_contained_type_no_args(self):
        # In this case we don't know what to do
        from zope.schema.interfaces import WrongContainedType

        class Field(object):
            __name__ = 'thing'

            def validate(self, value):
                raise WrongContainedType

            def bind(self, _):
                return self

        with self.assertRaises(WrongContainedType):
            self._callFUT(Field(), [object()])


    def test_wrong_contained_type_field_fromObject(self):
        from zope.schema import Object
        from zope.schema import List
        from zope.schema.interfaces import WrongContainedType

        class FromList(List):
            def fromObject(self, o):
                assert isinstance(o, list)
                return o

        class IThing(interface.Interface):
            pass

        field = FromList(value_type=Object(IThing))

        # This gets us to the second pass, after we run the fromObject
        # one time.
        with self.assertRaises(WrongContainedType):
            self._callFUT(field, [object()])

    def test_wrong_contained_type_value_type_fromObject(self):
        from zope.schema import Object
        from zope.schema import List

        class IThing(interface.Interface):
            pass


        class FromObject(Object):

            def fromObject(self, o):
                interface.alsoProvides(o, IThing)
                return o

        class O(object):
            pass

        field = List(value_type=FromObject(IThing), __name__='field')

        setter, bag = self._callFUT(field, [O()])
        setter()
        assert_that(bag, has_property('field'))


    def test_readonly_allowed(self):
        from zope.schema import Int

        field = Int(readonly=True, __name__='field', required=False)
        field.setTaggedValue('_ext_allow_initial_set', True)

        setter, bag = self._callFUT(field, 1)
        setter()
        assert_that(bag, has_property('field', 1))

        # Second time it is not allowed
        setter, bag = self._callFUT(field, 2, bag=bag)
        with self.assertRaises(TypeError):
            setter()
        assert_that(bag, has_property('field', 1))

        # If we send none, it is bypassed
        setter, bag = self._callFUT(field, None)
        setter()
        assert_that(bag, is_not(has_property('field')))

    def test_validate_named_field_value_just_attr(self):
        class IFace(interface.Interface):
            thing = interface.Attribute("A thing")

        setter = INT.validate_named_field_value(self.Bag(), IFace, 'thing', 42)
        setter()


    def test_non_convertable_sequence(self):
        from zope.schema.interfaces import WrongContainedType

        class Field(object):
            value_type = None
            def bind(self, obj):
                return self
            def validate(self, obj):
                raise WrongContainedType([])


        with self.assertRaises(WrongContainedType):
            INT.validate_field_value(self, 'name', Field(), [1])

        with self.assertRaises(INT.fields.CannotConvertSequenceError):
            INT.fields._adapt_sequence(Field(), [])
