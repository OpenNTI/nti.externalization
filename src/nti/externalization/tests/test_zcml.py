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

from nti.externalization.interfaces import IMimeObjectFactory
from nti.testing.matchers import is_empty

from hamcrest import assert_that
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import none

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
# pylint: disable=inherit-non-class

class TestRegisterMimeFactoriesZCML(PlacelessSetup,
                                    unittest.TestCase):

    SCAN_THIS_MODULE = """
        <configure xmlns:ext="http://nextthought.com/ntp/ext">
           <include package="nti.externalization" file="meta.zcml" />
           <ext:registerMimeFactories module="%s" />
        </configure>
        """ % (__name__)

    def _getModule(self):
        import sys
        return sys.modules[__name__]

    def test_scan_module_with_no_factories(self):
        xmlconfig.string(self.SCAN_THIS_MODULE)
        gsm = component.getGlobalSiteManager()
        assert_that(list(gsm.registeredUtilities()), is_empty())

    def test_scan_module_with_factory(self):
        class O(object):
            __external_can_create__ = True
            mimeType = 'application/foo'

        self._getModule().Factory = O
        try:
            xmlconfig.string(self.SCAN_THIS_MODULE)
            assert_that(component.getUtility(IMimeObjectFactory,
                                             name=O.mimeType),
                        is_not(none()))
        finally:
            del self._getModule().Factory

    def test_scan_module_with_factories(self):
        class O(object):
            __external_can_create__ = True
            mimeType = 'application/foo'

        class P(object):
            __external_can_create__ = True
            mimeType = 'application/foo2'

        self._getModule().Factory = O
        self._getModule().Factory2 = P
        try:
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
        finally:
            del self._getModule().Factory
            del self._getModule().Factory2

    def test_scan_module_with_factories_conflict(self):
        from zope.configuration.config import ConfigurationConflictError
        class O(object):
            __external_can_create__ = True
            mimeType = 'application/foo'

        class P(object):
            __external_can_create__ = True
            mimeType = O.mimeType

        self._getModule().Factory = O
        self._getModule().Factory2 = P
        try:
            with self.assertRaises(ConfigurationConflictError):
                xmlconfig.string(self.SCAN_THIS_MODULE)
        finally:
            del self._getModule().Factory
            del self._getModule().Factory2


    def test_scan_module_with_factory_legacy(self):
        class O(object):
            __external_can_create__ = True
            mime_type = 'application/foo'

        self._getModule().Factory = O
        try:
            xmlconfig.string(self.SCAN_THIS_MODULE)
            assert_that(component.getUtility(IMimeObjectFactory,
                                             name=O.mime_type),
                        is_not(none()))
        finally:
            del self._getModule().Factory

    def test_scan_module_with_factory_no_mime(self):
        class O(object):
            __external_can_create__ = True

        self._getModule().Factory = O
        try:
            xmlconfig.string(self.SCAN_THIS_MODULE)
            gsm = component.getGlobalSiteManager()
            assert_that(list(gsm.registeredUtilities()), is_empty())
        finally:
            del self._getModule().Factory

    def test_scan_module_with_factory_imported(self):
        class O(object):
            __external_can_create__ = True
            mimeType = 'application/foo'

        O.__module__ = '__dynamic__'

        self._getModule().Factory = O
        try:
            xmlconfig.string(self.SCAN_THIS_MODULE)
            gsm = component.getGlobalSiteManager()
            assert_that(list(gsm.registeredUtilities()), is_empty())
        finally:
            del self._getModule().Factory


    def test_scan_module_with_factory_non_create(self):
        class O(object):
            __external_can_create__ = False
            mimeType = 'application/foo'

        self._getModule().Factory = O
        try:
            xmlconfig.string(self.SCAN_THIS_MODULE)
            gsm = component.getGlobalSiteManager()
            assert_that(list(gsm.registeredUtilities()), is_empty())
        finally:
            del self._getModule().Factory

class IExtRoot(interface.Interface):
    pass

class IOBase(object):

    @classmethod
    def _ap_find_package_interface_module(cls):
        import sys
        return sys.modules[__name__]

class TestAutoPackageZCML(PlacelessSetup,
                          unittest.TestCase):
    SCAN_THIS_MODULE = """
        <configure xmlns:ext="http://nextthought.com/ntp/ext">
           <include package="nti.externalization" file="meta.zcml" />
           <ext:registerAutoPackageIO root_interfaces="%s.IExtRoot" modules="%s"
              iobase="%s.IOBase" />
        </configure>
        """ % (__name__, __name__, __name__)

    def test_scan_package_empty(self):
        xmlconfig.string(self.SCAN_THIS_MODULE)
        gsm = component.getGlobalSiteManager()
        # The interfaces IExtRoot and IInternalObjectIO were registered
        assert_that(list(gsm.registeredUtilities()), has_length(2))
        # The root interface was registered
        assert_that(list(gsm.registeredAdapters()), has_length(1))
