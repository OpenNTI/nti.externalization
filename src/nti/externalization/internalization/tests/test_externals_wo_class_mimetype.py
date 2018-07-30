# -*- coding: utf-8 -*-
"""
Tests for reading data into objects from external data *not* following
the conventions of this package, e.g., missing Class and MimeType values.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
# pylint:disable=inherit-non-class
import sys
import unittest

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import has_property as has_attr
from hamcrest import has_length
from hamcrest import contains_string

from zope import interface
from zope import component

from zope.schema import Object
from zope.schema import Int
from zope.schema import List

from zope.testing.cleanup import CleanUp

from nti.externalization import interfaces
from nti.externalization.internalization import update_from_external_object
from nti.externalization.internalization import updater
from nti.externalization.datastructures import InterfaceObjectIO


class TestExternals(CleanUp,
                    unittest.TestCase):

    def test_single_object_field_names_match_non_primitive(self):
        class INestedThing(interface.Interface):
            value = Int(title=u"An integer")

        class IRoot(interface.Interface):
            field = Object(INestedThing)


        class IO(InterfaceObjectIO):
            _ext_iface_upper_bound = IRoot
        component.provideAdapter(IO, adapts=(IRoot,))

        class IO2(InterfaceObjectIO):
            _ext_iface_upper_bound = INestedThing

        component.provideAdapter(IO2, adapts=(INestedThing,))

        @interface.implementer(IRoot)
        class Root(object):

            def __init__(self):
                self.field = None

        @interface.implementer(INestedThing)
        class NestedThing(object):

            def __init__(self):
                self.value = -1

        IRoot['field'].setTaggedValue('__external_factory__', NestedThing)

        external = {'field': {'value': 42}}

        root = Root()

        update_from_external_object(root, external, require_updater=True)

        assert_that(root, has_attr('field', is_(NestedThing)))
        assert_that(root.field, has_attr('value', 42))


    def test_sequence_object_field_names_match_non_primitive(self):
        class INestedThing(interface.Interface):
            value = Int(title=u"An integer")

        class IRoot(interface.Interface):
            field = List(Object(INestedThing))


        class IO(InterfaceObjectIO):
            _ext_iface_upper_bound = IRoot
        component.provideAdapter(IO, adapts=(IRoot,))

        class IO2(InterfaceObjectIO):
            _ext_iface_upper_bound = INestedThing

        component.provideAdapter(IO2, adapts=(INestedThing,))

        @interface.implementer(IRoot)
        class Root(object):

            def __init__(self):
                self.field = ()

        @interface.implementer(INestedThing)
        class NestedThing(object):

            def __init__(self):
                self.value = -1

        IRoot['field'].setTaggedValue('__external_factory__', NestedThing)

        external = {'field': [{'value': 42}, {'value': 2018}]}

        root = Root()

        update_from_external_object(root, external, require_updater=True)

        assert_that(root, has_attr('field', is_(list)))
        assert_that(root.field[0], has_attr('value', 42))
        assert_that(root.field[1], has_attr('value', 2018))


    def test_nested_single_object_field_names_match_non_primitive(self):
        class INestedThing(interface.Interface):
            value = Int(title=u"An integer")

        class IMiddleThing(interface.Interface):
            nested = Object(INestedThing)

        class IRoot(interface.Interface):
            field = Object(IMiddleThing)


        class IO(InterfaceObjectIO):
            _ext_iface_upper_bound = IRoot
        component.provideAdapter(IO, adapts=(IRoot,))

        class IO2(InterfaceObjectIO):
            _ext_iface_upper_bound = INestedThing
        component.provideAdapter(IO2, adapts=(INestedThing,))

        class IO3(InterfaceObjectIO):
            _ext_iface_upper_bound = IMiddleThing
        component.provideAdapter(IO3, adapts=(IMiddleThing,))


        @interface.implementer(IRoot)
        class Root(object):

            def __init__(self):
                self.field = None

        @interface.implementer(IMiddleThing)
        class MiddleThing(object):
            def __init__(self):
                self.nested = None

        @interface.implementer(INestedThing)
        class NestedThing(object):

            def __init__(self):
                self.value = -1

        IRoot['field'].setTaggedValue('__external_factory__', MiddleThing)
        IMiddleThing['nested'].setTaggedValue('__external_factory__', NestedThing)

        external = {'field': {'nested': {'value': 42}}}

        root = Root()

        update_from_external_object(root, external, require_updater=True)

        assert_that(root, has_attr('field', is_(MiddleThing)))
        assert_that(root.field, has_attr('nested', is_(NestedThing)))
        assert_that(root.field, has_attr('nested', has_attr('value', 42)))


    def test_nested_single_object_field_names_match_non_primitive_zcml(self):
        # The same as test_nested_single_object_field_names_match_non_primitive
        # but configured through ZCML using global objects.
        from zope.configuration import xmlconfig
        zcml = """
        <configure xmlns:ext="http://nextthought.com/ntp/ext">
           <include package="nti.externalization" file="meta.zcml" />
           <ext:registerAutoPackageIO
              root_interfaces=".IGlobalNestedThing .IGlobalMiddleThing .IGlobalRoot"
              iobase=".IOBase"
              modules="{0}"
              />
            <ext:anonymousObjectFactory
               for=".IGlobalRoot"
               field="field"
               factory=".GlobalMiddleThing"
               />
            <ext:anonymousObjectFactory
               for=".IGlobalMiddleThing"
               field="nested"
               factory=".GlobalNestedThing"
               />
        </configure>
        """.format(__name__)

        context = xmlconfig.ConfigurationMachine()
        xmlconfig.registerCommonDirectives(context)
        context.package = sys.modules[__name__]
        xmlconfig.string(zcml, context)


        external = {'field': {'nested': {'value': 42}}}

        root = GlobalRoot()

        update_from_external_object(root, external, require_updater=True)

        assert_that(root, has_attr('field', is_(GlobalMiddleThing)))
        assert_that(root.field, has_attr('nested', is_(GlobalNestedThing)))
        assert_that(root.field, has_attr('nested', has_attr('value', 42)))


class TestLookups(CleanUp,
                  unittest.TestCase):

    def test_InterfaceObjectIO_subclass_registered_as_IInternalObjectIO(self):
        # We still find it even if it's registered with the legacy interface.
        import warnings

        class Derived(InterfaceObjectIO):
            def __init__(self, context): # pylint:disable=super-init-not-called
                pass

        component.provideAdapter(Derived, (object,), provides=interfaces.IInternalObjectIO)

        with warnings.catch_warnings(record=True) as w:
            found = updater._find_INamedExternalizedObjectFactoryFinder(self, component)

        assert_that(found, is_(Derived))
        assert_that(w, has_length(1))
        assert_that(str(w[0].message), contains_string('was registered as IInternalObjectIO'))


class IOBase(object):

    @classmethod
    def _ap_find_package_interface_module(cls):
        return sys.modules[__name__]


class IGlobalNestedThing(interface.Interface):
    value = Int(title=u"An integer")

class IGlobalMiddleThing(interface.Interface):
    nested = Object(IGlobalNestedThing)

class IGlobalRoot(interface.Interface):
    field = Object(IGlobalMiddleThing)

@interface.implementer(IGlobalRoot)
class GlobalRoot(object):
    def __init__(self):
        self.field = None

@interface.implementer(IGlobalMiddleThing)
class GlobalMiddleThing(object):
    def __init__(self):
        self.nested = None

@interface.implementer(IGlobalNestedThing)
class GlobalNestedThing(object):
    def __init__(self):
        self.value = -1
