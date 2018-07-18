# -*- coding: utf-8 -*-
"""
Tests for zcml.py.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import unittest

from zope import component
from zope import interface
from zope.component.testing import PlacelessSetup
from zope.configuration import xmlconfig

from nti.externalization.interfaces import IClassObjectFactory
from nti.externalization.interfaces import IMimeObjectFactory
from nti.externalization.interfaces import _ILegacySearchModuleFactory
from nti.testing.matchers import is_empty

from hamcrest import assert_that
from hamcrest import same_instance
from hamcrest import equal_to
from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import has_property
from hamcrest import none

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
# pylint: disable=inherit-non-class

class RegistrationMixin(object):

    assertRaisesRegex = getattr(unittest.TestCase,
                                'assertRaisesRegex',
                                unittest.TestCase.assertRaisesRegexp)

    def _getModule(self):
        import sys
        return sys.modules[__name__]

    def _addFactory(self, factory, name='Factory'):
        module = self._getModule()
        setattr(module, name, factory)
        self.addCleanup(delattr, module, name)


class TestRegisterMimeFactoriesZCML(PlacelessSetup,
                                    RegistrationMixin,
                                    unittest.TestCase):

    SCAN_THIS_MODULE = """
        <configure xmlns:ext="http://nextthought.com/ntp/ext">
           <include package="nti.externalization" file="meta.zcml" />
           <ext:registerMimeFactories module="%s" />
        </configure>
        """ % (__name__)

    def test_scan_module_with_no_factories(self):
        xmlconfig.string(self.SCAN_THIS_MODULE)
        gsm = component.getGlobalSiteManager()
        assert_that(list(gsm.registeredUtilities()), is_empty())

    def test_scan_module_with_factory(self):
        class O(object):
            __external_can_create__ = True
            mimeType = 'application/foo'
        self._addFactory(O)

        xmlconfig.string(self.SCAN_THIS_MODULE)
        assert_that(component.getUtility(IMimeObjectFactory,
                                         name=O.mimeType),
                    is_not(none()))

    def test_scan_module_with_factories(self):
        class O(object):
            __external_can_create__ = True
            mimeType = 'application/foo'

        class P(object):
            __external_can_create__ = True
            mimeType = 'application/foo2'

        self._addFactory(O)
        self._addFactory(P, 'Factory2')
        xmlconfig.string(self.SCAN_THIS_MODULE)
        o = component.getUtility(IMimeObjectFactory,
                                 name=O.mimeType)
        p = component.getUtility(IMimeObjectFactory,
                                 name=P.mimeType)
        assert_that(o,
                    is_not(none()))
        assert_that(p,
                    is_not(none()))
        assert_that(o, is_not(p))

    def test_scan_module_with_factories_conflict(self):
        from zope.configuration.config import ConfigurationConflictError
        class O(object):
            __external_can_create__ = True
            mimeType = 'application/foo'

        class P(object):
            __external_can_create__ = True
            mimeType = O.mimeType

        self._addFactory(O)
        self._addFactory(P, 'Factory2')

        with self.assertRaises(ConfigurationConflictError):
            xmlconfig.string(self.SCAN_THIS_MODULE)

    def test_scan_module_with_factory_legacy(self):
        class O(object):
            __external_can_create__ = True
            mime_type = 'application/foo'

        self._addFactory(O)
        xmlconfig.string(self.SCAN_THIS_MODULE)
        assert_that(component.getUtility(IMimeObjectFactory,
                                         name=O.mime_type),
                    is_not(none()))

    def test_scan_module_with_factory_no_mime(self):
        class O(object):
            __external_can_create__ = True

        self._addFactory(O)
        xmlconfig.string(self.SCAN_THIS_MODULE)
        gsm = component.getGlobalSiteManager()
        assert_that(list(gsm.registeredUtilities()), is_empty())

    def test_scan_module_with_factory_imported(self):
        class O(object):
            __external_can_create__ = True
            mimeType = 'application/foo'

        O.__module__ = '__dynamic__'

        self._addFactory(O)
        xmlconfig.string(self.SCAN_THIS_MODULE)
        gsm = component.getGlobalSiteManager()
        assert_that(list(gsm.registeredUtilities()), is_empty())

    def test_scan_module_with_factory_non_create(self):
        class O(object):
            __external_can_create__ = False
            mimeType = 'application/foo'

        self._addFactory(O)
        xmlconfig.string(self.SCAN_THIS_MODULE)
        gsm = component.getGlobalSiteManager()
        assert_that(list(gsm.registeredUtilities()), is_empty())

class IExtRoot(interface.Interface):
    pass

class IOBase(object):

    @classmethod
    def _ap_find_package_interface_module(cls):
        import sys
        return sys.modules[__name__]

class TestAutoPackageZCML(PlacelessSetup,
                          RegistrationMixin,
                          unittest.TestCase):
    SCAN_THIS_MODULE = """
        <configure xmlns:ext="http://nextthought.com/ntp/ext">
           <include package="nti.externalization" file="meta.zcml" />
           <ext:registerAutoPackageIO root_interfaces="%s.IExtRoot" modules="%s"
              iobase="%s.IOBase"
              register_legacy_search_module="yes" />
        </configure>
        """ % (__name__, __name__, __name__)

    def test_scan_package_empty(self):
        from nti.externalization import internalization as INT
        xmlconfig.string(self.SCAN_THIS_MODULE)
        gsm = component.getGlobalSiteManager()
        # The interfaces IExtRoot and IInternalObjectIO were registered
        assert_that(list(gsm.registeredUtilities()), has_length(2))
        # The root interface was registered
        assert_that(list(gsm.registeredAdapters()), has_length(1))

        # The module was added to the legacy search list directly,
        # now, producing the factories it needed (which was none)
        assert_that(INT.LEGACY_FACTORY_SEARCH_MODULES,
                    is_empty())


    def test_scan_package_legacy_utility(self):
        @interface.implementer(IExtRoot)
        class O(object):
            __external_can_create__ = True
            mimeType = 'application/foo'

        self._addFactory(O)
        xmlconfig.string(self.SCAN_THIS_MODULE)
        gsm = component.getGlobalSiteManager()
        # The interfaces IExtRoot and IInternalObjectIO were registered,
        # as well as an IMimeObjectFactory and that interface,
        # two variants on ILegacySearchModuleFactory and its interface.
        assert_that(list(gsm.registeredUtilities()), has_length(7))

        factory = gsm.getUtility(IMimeObjectFactory, 'application/foo')
        assert_that(factory, has_property('_callable', equal_to(O)))

        factory = gsm.getUtility(_ILegacySearchModuleFactory, 'o')
        assert_that(factory, is_(same_instance(O)))

        factory = gsm.getUtility(_ILegacySearchModuleFactory, 'O')
        assert_that(factory, is_(same_instance(O)))

class TestClassObjectFactory(PlacelessSetup,
                             RegistrationMixin,
                             unittest.TestCase):

    SCAN_THIS_MODULE = """
        <configure xmlns:ext="http://nextthought.com/ntp/ext"
                   xmlns:i18n="http://namespaces.zope.org/i18n"
                   i18n_domain="zope">
           <include package="nti.externalization" file="meta.zcml" />
           <ext:classObjectFactory
              factory="%s.Factory"
              PLACEHOLDER
              />
        </configure>
    """ % (__name__,)


    def test_scan_no_create(self):
        class O(object):
            pass

        self._addFactory(O)
        with self.assertRaisesRegex(xmlconfig.ZopeXMLConfigurationError,
                                    "must set __external_can_create__ to true"):
            xmlconfig.string(self.SCAN_THIS_MODULE.replace('PLACEHOLDER', ''))

    def test_scan_not_callable(self):
        class O(object):
            __external_can_create__ = True

        self._addFactory(O())

        with self.assertRaisesRegex(xmlconfig.ZopeXMLConfigurationError,
                                    "must be callable"):
            xmlconfig.string(self.SCAN_THIS_MODULE.replace('PLACEHOLDER', ''))

    def test_scan_no_name(self):
        class O(object):
            __external_can_create__ = True

        self._addFactory(O)
        xmlconfig.string(self.SCAN_THIS_MODULE.replace('PLACEHOLDER', ''))
        factory = component.getUtility(IClassObjectFactory, 'O')
        assert_that(factory, has_property('_callable', equal_to(O)))

    def test_scan_name_in_xml(self):
        class O(object):
            __external_class_name__ = "Ignored"
            __external_can_create__ = True

        self._addFactory(O)
        xmlconfig.string(self.SCAN_THIS_MODULE.replace('PLACEHOLDER',
                                                       'name="AName" title="A title"'))
        factory = component.getUtility(IClassObjectFactory, 'AName')
        assert_that(factory, has_property('_callable', equal_to(O)))
        assert_that(factory, has_property('title', equal_to("A title")))

    def test_scan_name_in_class(self):
        class O(object):
            __external_class_name__ = "FromClass"
            __external_can_create__ = True

        self._addFactory(O)
        xmlconfig.string(self.SCAN_THIS_MODULE.replace('PLACEHOLDER', ''))
        factory = component.getUtility(IClassObjectFactory, 'FromClass')
        assert_that(factory, has_property('_callable', equal_to(O)))


class ISchema(interface.Interface):

    field = interface.Attribute("This is a field")
    field2 = interface.Attribute("This is another field")

class IDerived(ISchema):
    pass

class TestAnonymousObjectFactoryZCML(PlacelessSetup,
                                     RegistrationMixin,
                                     unittest.TestCase):

    SCAN_THIS_MODULE = """
        <configure xmlns:ext="http://nextthought.com/ntp/ext"
                   xmlns:i18n="http://namespaces.zope.org/i18n"
                   i18n_domain="zope">
           <include package="nti.externalization" file="meta.zcml" />
           <ext:anonymousObjectFactory
                factory="{0}.Factory"
                for="{0}.ISchema"
                field="field"
             />
            <ext:anonymousObjectFactoryInPlace
                for="{0}.ISchema"
                field="field2"
             />
        </configure>
    """.format(__name__)

    def test_sets_tagged_value(self):
        class O(object):
            __external_can_create__ = True

        self._addFactory(O)

        xmlconfig.string(self.SCAN_THIS_MODULE)

        assert_that(ISchema['field'].getTaggedValue('__external_factory__'),
                    is_('nti.externalization.tests.test_zcml.ISchema:field'))
        assert_that(ISchema['field2'].getTaggedValue('__external_factory__'),
                    is_('nti.externalization.tests.test_zcml.ISchema:field2'))

    def test_scan_no_create(self):
        class O(object):
            pass

        self._addFactory(O)
        with self.assertRaisesRegex(xmlconfig.ZopeXMLConfigurationError,
                                    "must set __external_can_create__ to true"):
            xmlconfig.string(self.SCAN_THIS_MODULE)

    def test_scan_not_callable(self):
        class O(object):
            __external_can_create__ = True

        self._addFactory(O())

        with self.assertRaisesRegex(xmlconfig.ZopeXMLConfigurationError,
                                    "must be callable"):
            xmlconfig.string(self.SCAN_THIS_MODULE)

    def test_scan_not_direct(self):
        class O(object):
            __external_can_create__ = True

        self._addFactory(O)
        zcml = self.SCAN_THIS_MODULE.replace("ISchema", 'IDerived')

        with self.assertRaisesRegex(xmlconfig.ZopeXMLConfigurationError,
                                    "is not directly part of the interface"):
            xmlconfig.string(zcml)

    def test_in_place(self):
        class O(object):
            __external_can_create__ = True

        self._addFactory(O)

        xmlconfig.string(self.SCAN_THIS_MODULE)

        obj = component.createObject('nti.externalization.tests.test_zcml.ISchema:field2',
                                     self)
        assert_that(obj, is_(self))
