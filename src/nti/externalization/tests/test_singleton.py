#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import same_instance

from nti.externalization.singleton import SingletonDecorator

from nose.tools import assert_raises

from nti.externalization.tests import ExternalizationLayerTest

class TestSingleton(ExternalizationLayerTest):
	
	def test_singleton_decorator(self):

		class X(object):
			__metaclass__ = SingletonDecorator

		# No context
		assert_that( X(), is_( same_instance( X() ) ) )

		# context ignored
		assert_that( X('context'), is_( same_instance( X('other_context') ) ) )

		# two contexts for the common multi-adapter case
		assert_that( X('context', 'request'), 
					 is_( same_instance( X('other_context', 'other_request') ) ) )

		x = X()
		with assert_raises(AttributeError):
			x.b = 1

		with assert_raises(AttributeError):
			getattr( x, '__dict__' )
