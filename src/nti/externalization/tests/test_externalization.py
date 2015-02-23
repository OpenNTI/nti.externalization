#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import raises
from hamcrest import calling
from hamcrest import has_key
from hamcrest import contains
from hamcrest import has_entry
from hamcrest import has_items
from hamcrest import assert_that
from hamcrest import same_instance
from hamcrest import has_property as has_attr

does_not = is_not

import sys
import json
import plistlib
import unittest
import UserDict

import persistent

from zope import component

from ZODB.broken import Broken

from nti.externalization import externalization
from nti.externalization.internalization import _search_for_external_factory

from nti.externalization.interfaces import EXT_REPR_YAML
from nti.externalization.interfaces import LocatedExternalList
from nti.externalization.interfaces import LocatedExternalDict

from nti.externalization.externalization import EXT_FORMAT_PLIST
from nti.externalization.externalization import EXT_FORMAT_JSON
from nti.externalization.externalization import toExternalObject
from nti.externalization.externalization import catch_replace_action
from nti.externalization.externalization import to_standard_external_dictionary

from nti.externalization.datastructures import ExternalizableDictionaryMixin
from nti.externalization.datastructures import ExternalizableInstanceDict

from nti.externalization.persistence import getPersistentState
from nti.externalization.persistence import PersistentExternalizableWeakList

from nti.externalization.oids import toExternalOID, fromExternalOID

from nti.externalization.representation import to_external_representation

from nti.externalization.tests import ExternalizationLayerTest

class TestFunctions(ExternalizationLayerTest):

	def test_getPersistentState(self):
		# Non-persistent objects are changed
		assert_that( getPersistentState( None ), is_(persistent.CHANGED ) )
		assert_that( getPersistentState( object() ), is_(persistent.CHANGED) )

		# Object with _p_changed are that
		class T(object):
			_p_changed = True

		assert_that( getPersistentState( T() ), is_(persistent.CHANGED) )
		T._p_changed = False
		assert_that( getPersistentState( T() ), is_( persistent.UPTODATE ) )

		# _p_state is trumped by _p_changed
		T._p_state = None
		assert_that( getPersistentState( T() ), is_( persistent.UPTODATE ) )

		# _p_state is used if _p_changed isn't
		del T._p_changed
		T._p_state = 42
		assert_that( getPersistentState( T() ), is_( 42 ) )

		def f(s): return 99
		T.getPersistentState = f
		del T._p_state
		assert_that( getPersistentState( T() ), is_( 99 ) )

	def test_toExternalID( self ):
		class T(object): pass
		assert_that( toExternalOID( T() ), is_(None) )

		t = T()
		t._p_oid = '\x00\x01'
		assert_that( toExternalOID( t ), is_( '0x01' ) )

		t._p_jar = t
		db = T()
		db.database_name = 'foo'
		t.db = lambda: db
		del t._v_to_external_oid
		assert_that( toExternalOID( t ), is_( '0x01:666f6f' ) )

		assert_that( fromExternalOID( '0x01:666f6f' )[0], is_( b'\x00\x00\x00\x00\x00\x00\x00\x01' ) )
		assert_that( fromExternalOID( '0x01:666f6f' )[0], is_( bytes ) )
		assert_that( fromExternalOID( '0x01:666f6f' )[1], is_( 'foo' ) )

		# Given a plain OID, we return just the plain OID
		oid = b'\x00\x00\x00\x00\x00\x00\x00\x01'
		assert_that( fromExternalOID( oid ), contains( same_instance( oid ),'',None) )


	def test_to_external_representation_none_handling( self ):
		d = {'a': 1, 'None': None}
		# JSON keeps None
		assert_that( json.loads( to_external_representation( d, EXT_FORMAT_JSON ) ),
					 is_( d ) )
		# PList strips it
		assert_that( plistlib.readPlistFromString( to_external_representation( d, EXT_FORMAT_PLIST ) ),
					 is_( { 'a': 1 } ) )

	def test_to_external_representation_yaml(self):
		l = LocatedExternalList()
		l.append(LocatedExternalDict(k='v'))
		class SubUnicode(unicode):
			pass
		l.append(LocatedExternalDict(k2=SubUnicode('foo')))

		assert_that( to_external_representation(l, EXT_REPR_YAML),
					 is_('- {k: v}\n- {k2: foo}\n') )

	def test_external_class_name( self ):
		class C(UserDict.UserDict,ExternalizableDictionaryMixin):
			pass
		assert_that( toExternalObject( C() ), has_entry( 'Class', 'C' ) )
		C.__external_class_name__ = 'ExternalC'
		assert_that( toExternalObject( C() ), has_entry( 'Class', 'ExternalC' ) )

	def test_broken(self):
		# Without the devmode hooks
		gsm = component.getGlobalSiteManager()
		gsm.unregisterAdapter( factory=externalization._DevmodeNonExternalizableObjectReplacer, required=() )
		gsm.unregisterAdapter( factory=externalization._DevmodeNonExternalizableObjectReplacer, required=(interface.Interface,) )

		assert_that( toExternalObject( Broken(), registry=gsm ),
					 has_entry( "Class", "NonExternalizableObject" ) )

		assert_that( toExternalObject( [Broken()], registry=gsm ),
					 has_items( has_entry( "Class", "NonExternalizableObject" ) ) )

	def test_catching_component(self):
		class Raises(object):
			def toExternalObject(self, **kwargs):
				assert False

		assert_that( toExternalObject( [Raises()], catch_components=(AssertionError,), catch_component_action=catch_replace_action ),
					 is_( [catch_replace_action(None,None)] ) )

		# Default doesn't catch
		assert_that( calling(toExternalObject).with_args([Raises()]),
					 raises(AssertionError) )

	def test_search_for_external(self):
		class Y(object):
			__external_can_create__ = True
		class X(object): pass
		x = X()
		x.FooBar = Y

		# Something with a __dict__ already
		assert_that( _search_for_external_factory( 'FooBar', search_set=[x] ), same_instance( Y ) )

		# Something in sysmodules
		n = 'MyTestModule'
		assert n not in sys.modules
		sys.modules[n] = x

		assert_that( _search_for_external_factory( 'FooBar', search_set=[n] ), same_instance( Y ) )

		del sys.modules[n]
		# something unresolvable
		assert_that( _search_for_external_factory( 'FooBar', search_set=[n] ), is_( none() ) )

class TestPersistentExternalizableWeakList(unittest.TestCase):

	def test_plus_extend( self ):
		class C( persistent.Persistent ): pass
		c1 = C()
		c2 = C()
		c3 = C()
		l = PersistentExternalizableWeakList()
		l += [c1, c2, c3]
		assert_that( l, is_( [c1, c2, c3] ) )
		assert_that( [c1, c2, c3], is_(l) )

		# Adding things that are already weak refs.
		l += l
		assert_that( l, is_( [c1, c2, c3, c1, c2, c3] ) )

		l = PersistentExternalizableWeakList()
		l.extend( [c1, c2, c3] )
		assert_that( l, is_( [c1, c2, c3] ) )
		assert_that( l, is_(l) )

class TestExternalizableInstanceDict(ExternalizationLayerTest):

	class C(ExternalizableInstanceDict):
		def __init__( self ):
			super(TestExternalizableInstanceDict.C,self).__init__()
			self.A1 = None
			self.A2 = None
			self.A3 = None
			self._A4 = None
			# notice no A5

	def test_simple_roundtrip( self ):
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

		ext = toExternalObject( obj )

		newObj = self.C()
		newObj.updateFromExternalObject( ext )

		for attr in set(obj._excluded_out_ivars_) | set(['A5']):
			assert_that( newObj, does_not( has_attr( attr ) ) )
		assert_that( ext, does_not( has_key( "A5" ) ) )
		#assert_that( ext, does_not( has_key( 'A3' ) ) )
		assert_that( ext, does_not( has_key( '_A4' ) ) )
		assert_that( newObj.A1, is_( 1 ) )
		assert_that( newObj.A2, is_( "2" ) )

import datetime
from numbers import Number

from zope import interface
from zope.dublincore import interfaces as dub_interfaces

from nti.externalization.interfaces import IExternalObject
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalObjectDecorator

from nti.testing.matchers import verifiably_provides

class TestToExternalObject(ExternalizationLayerTest):

	def test_decorator(self):
		class ITest(interface.Interface): pass
		class Test(object):
			interface.implements(ITest,IExternalObject)

			def toExternalObject(self, **kwargs):
				return {}

		test = Test()

		assert_that( toExternalObject( test ), is_( {} ) )

		class Decorator(object):
			interface.implements(IExternalObjectDecorator)
			def __init__( self, o ): pass
			def decorateExternalObject( self, obj, result ):
				result['test'] = obj

		component.provideSubscriptionAdapter( Decorator, adapts=(ITest,) )

		assert_that( toExternalObject( test ), is_( {'test': test } ) )

	def test_memo(self):

		@interface.implementer(IExternalObject)
		class Test(object):

			def toExternalObject(self, **kwargs):
				# a new dict each time we're called;
				# we only want to be called once
				return {}

		test = Test()

		tests = [test, test]

		ext_val = toExternalObject(tests)
		assert_that( ext_val[0],
					 is_(same_instance(ext_val[1]) ) )

	def test_memo_changes_names(self):
		# if we're called with a different name,
		# the memo changes too
		@interface.implementer(IExternalObject)
		class Test(object):
			def toExternalObject(self, **kwargs):
				# a new dict each time we're called;
				# we only want to be called once
				return {}


		@interface.implementer(IExternalObject)
		class Parent(object):
			def __init__(self):
				self.test = Test()

			def toExternalObject(self, **kwargs):

				return [toExternalObject(self.test),
						toExternalObject(self.test, name="other")]


		ext_val = toExternalObject(Parent())
		assert_that( ext_val[0],
					 is_not(same_instance(ext_val[1]) ) )

	def test_to_stand_dict_uses_dubcore(self):

		@interface.implementer(dub_interfaces.IDCTimes)
		class X(object):
			created = datetime.datetime.now()
			modified = datetime.datetime.now()

		assert_that( X(), verifiably_provides( dub_interfaces.IDCTimes ) )

		ex_dic = to_standard_external_dictionary( X() )
		assert_that( ex_dic, has_entry( StandardExternalFields.LAST_MODIFIED, is_( Number ) ) )
		assert_that( ex_dic, has_entry( StandardExternalFields.CREATED_TIME, is_( Number ) ) )

from nti.externalization.persistence import NoPickle

from nti.externalization.tests import assert_does_not_pickle

@NoPickle
class Foo(object):
	pass

class TestNoPickle(unittest.TestCase):

	def test_decorator(self):
		assert_does_not_pickle(Foo())
