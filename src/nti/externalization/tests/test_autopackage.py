# -*- coding: utf-8 -*-
"""
Tests for autopackage.py

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import unittest

from zope import interface
from zope.mimetype.interfaces import IContentTypeAware

from nti.testing.matchers import implements

from ..autopackage import AutoPackageSearchingScopedInterfaceObjectIO as AutoPackage

from hamcrest import assert_that
from hamcrest import has_key
from hamcrest import has_property
from hamcrest import is_
from hamcrest import is_not as does_not
from hamcrest import none

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
# pylint: disable=no-member
# pylint: disable=inherit-non-class

class TestAutoPackageIO(unittest.TestCase):

    def test_init_itself_does_nothing(self):
        self.assertIs(AutoPackage.__class_init__(), False)
        self.assertIs(AutoPackage.__class_init__(), False)

    def test_external_class_name(self):
        assert_that(AutoPackage._ap_compute_external_class_name_from_interface_and_instance(None,
                                                                                            self),
                    is_(type(self).__name__))

        class Foo(object):
            __external_class_name__ = 'Biz'

        assert_that(AutoPackage._ap_compute_external_class_name_from_interface_and_instance(None,
                                                                                            Foo()),
                    is_(Foo.__external_class_name__))

    def test_external_mimetype(self):

        assert_that(AutoPackage._ap_compute_external_mimetype('nti.externalization.tests',
                                                              None,
                                                              'AClassName'),
                    is_('application/vnd.nextthought.tests.aclassname'))

    def test_find_package_name(self):
        assert_that(AutoPackage._ap_find_package_name(),
                    is_('nti.externalization'))

    def test_find_factories_sets_name(self):
        class AP(AutoPackage):
            @classmethod
            def _ap_enumerate_module_names(cls):
                return ()

        reg = AP._ap_find_factories('nti.externalization.tests')
        assert_that(reg, has_property('__name__', 'nti.externalization.tests'))

    def test_find_interfaces(self):
        from nti.externalization import interfaces
        assert_that(AutoPackage._ap_find_package_interface_module(),
                    is_(interfaces))

    def test_assigns_mimeType_and_mime_type(self):

        class IExt(interface.Interface):
            interface.taggedValue('__external_class_name__', 'Ext')

        @interface.implementer(IExt)
        class E(object):
            pass

        AutoPackage._ap_handle_one_potential_factory_class(E, 'nti.package', E)

        assert_that(E, has_property("mimeType", 'application/vnd.nextthought.package.e'))
        assert_that(E, has_property("mime_type", 'application/vnd.nextthought.package.e'))
        assert_that(E, has_property("containerId", none()))
        assert_that(E, has_property('__external_can_create__', True))
        assert_that(E, implements(IContentTypeAware))
        assert_that(E, has_property('E', E))
        del E.E

    def test_copies_mimeType_from_mime_type(self):

        class IExt(interface.Interface):
            interface.taggedValue('__external_class_name__', 'Ext')

        @interface.implementer(IExt)
        class E(object):
            mime_type = None

        AutoPackage._ap_handle_one_potential_factory_class(E, 'nti.package', E)

        assert_that(E, has_property("mimeType", none()))
        assert_that(E, has_property("mime_type", none()))
        del E.E

        @interface.implementer(IExt)
        class F(object):
            mime_type = 'app/mime'

        AutoPackage._ap_handle_one_potential_factory_class(F, 'nti.package', F)

        assert_that(F, has_property("mimeType", 'app/mime'))
        assert_that(F, has_property("mime_type", 'app/mime'))
        del F.F

    def test_does_nothing_if_mimeType_present(self):
        class IExt(interface.Interface):
            interface.taggedValue('__external_class_name__', 'Ext')

        @interface.implementer(IExt)
        class E(object):
            mimeType = 'foo'

        AutoPackage._ap_handle_one_potential_factory_class(E, 'nti.package', E)
        assert_that(E, has_property("mimeType", 'foo'))
        assert_that(E, does_not(has_property("mime_type")))
        assert_that(E, does_not(implements(IContentTypeAware)))
        del E.E

    def test_inherits_external_can_create(self):
        class IExt(interface.Interface):
            interface.taggedValue('__external_class_name__', 'Ext')

        class Base(object):
            __external_can_create__ = False

        @interface.implementer(IExt)
        class E(Base):
            pass

        AutoPackage._ap_handle_one_potential_factory_class(E, 'nti.package', E)

        assert_that(E, has_property('__external_can_create__', False))

        assert_that(E.__dict__, does_not(has_key('__external_can_create__')))
