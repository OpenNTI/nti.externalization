#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for singleton objects that are used as external
object decorators.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# This was originally based on code from sympy.core.singleton

class SingletonDecorator(type):
	"""
	Metaclass for singleton classes to be used as external object
	decorators (adapters). These objects accept one or two context arguments to
	their __init__function, but they do not actually use them (because the same
	object is passed to their decoration method). Thus they can usefully
	be constructed just once and shared. This metaclass ensures the singleton
	property, ensures that the ``__init__`` method is a no-op, and ensures
	that the instance has no dictionary or instance variable.

	A singleton class has only one instance which is returned every time the
	class is instantiated.

	** Developer notes **
		The class is instanciated immediately at the point where it is defined
		by calling cls.__new__(cls). This instance is cached and cls.__new__ is
		rebound to return it directly.

		The original constructor is also cached to allow subclasses to access it
		and have their own instance.
	"""

	def __new__(cls, name, bases, cls_dict):
		cls_dict[str('__slots__')] = () # no ivars

		cls = type.__new__(cls, name, bases, cls_dict)

		ancestor = object
		for ancestor in cls.mro():
			if '__new__' in ancestor.__dict__:
				break
		if isinstance(ancestor, SingletonDecorator) and ancestor is not cls:
			ctor = ancestor._new_instance
		else:
			ctor = cls.__new__
		cls._new_instance = staticmethod(ctor)

		the_instance = ctor(cls)

		def __new__(cls, context=None, request=None):
			return the_instance
		cls.__new__ = staticmethod(__new__)

		def __init__( self, context=None, request=None ):
			pass
		cls.__init__ = __init__

		return cls
