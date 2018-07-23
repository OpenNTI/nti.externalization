=============
 Basic Usage
=============

.. sidebar:: History

   This package was originally developed for use in a `Pyramid
   <http://pyramid.readthedocs.io>`_ web application server in 2011.
   The desire was to be able to communicate Python application objects back
   and forth with browsers and native iOS applications using the most
   efficient serialization mechanisms possible.

   This was before Pyramid's built-in `JSON Renderer
   <http://pyramid.readthedocs.io/en/latest/narr/renderers.html#using-the-add-adapter-method-of-a-custom-json-renderer>`_
   supported adapting arbitrary objects to JSON (or even used the
   ``__json__`` method), and before iOS had a native `JSON reader
   <https://developer.apple.com/documentation/foundation/nsjsonserialization>`_.

   So there were two mandates: support adapters for externalizing
   arbitrary objects and support multiple objects representations
   (specifically :mod:`plist <plistlib>` for iOS, which didn't support
   `None`, and JSON for browsers.)

This document provides an overview of ``nti.externalization`` and
shows some simple examples of its usage.

Reading through the :doc:`glossary` before beginning is highly
recommended.


Motivation and Use-cases
========================

This package provides a supporting framework for transforming to and from
Python objects and an arbitrary binary or textual representation. That
representation is self-describing and intended to be stable. Uses for
that representation include:

- Communicating with browsers or other clients over HTTP (e.g., AJAX)
  or sockets;
- Storing persistently on disk for later reconstituting the Python
  objects;
- Using as a human-readable configuration format (with the proper
  choice of representation)

We expect that there will be lots of such objects in an application,
and we want to make it as easy as possible to communicate them.
Ideally, we want to be able to completely automate that, handing the
entire task off to this package.

It is also important that when we read external input, we validate
that it meets any internal constraints before further processing. For
example, numbers should be within their allowed range, or references
to other objects should actually result in an object of the expected
type.

Finally, we don't want to have to intermingle any code for reading and
writing objects with our actual business (application) logic. The two
concerns should be kept as separated as possible from our model
objects. Ideally, we should be able to use third-party objects that we
have no control over seamlessly in external and internal data.

Getting Started
===============

In its simplest form, there are two functions you'll use to
externalize and internalize objects::

  >>> from nti.externalization import to_external_object
  >>> from nti.externalization import update_from_external_object

We can define an object that we want to externalize:

.. code-block:: python

   class InternalObject(object):

       def __init__(self, id=''):
           self._field1 = 'a'
           self._field2 = 42
           self._id = id

       def toExternalObject(self, request=None, **kwargs):
           return {'A Letter': self._field1, 'The Number': self._field2}

       def __repr__(self):
           return '<%s %r letter=%r number=%d>' % (
               self.__class__.__name__, self._id, self._field1, self._field2)

.. caution::

   The signature for ``toExternalObject`` is poorly defined right now.
   The suitable keyword arguments should be enumerated and documented,
   but they are not. See https://github.com/NextThought/nti.externalization/issues/54

And we can externalize it with
`~nti.externalization.to_external_object` (we sort it here to be sure
we get consistent output):

  >>> sorted(to_external_object(InternalObject()).items())
  [('A Letter', 'a'), ('The Number', 42)]

If we want to update it, we need to write the corresponding method:

.. code-block:: python

   class UpdateInternalObject(InternalObject):

       def updateFromExternalObject(self, external_object, context=None):
            self._field1 = external_object['A Letter']
            self._field2 = external_object['The Number']

Updating it uses `~nti.externalization.update_from_external_object`:

  >>> internal = UpdateInternalObject('internal')
  >>> internal
  <UpdateInternalObject 'internal' letter='a' number=42>
  >>> update_from_external_object(internal, {'A Letter': 'b', 'The Number': 3})
  <UpdateInternalObject 'internal' letter='b' number=3>


That's Not Good Enough
----------------------

Notice that we had to define procedurally the input and output steps
in our classes. For some (small) applications, that may be good
enough, but it doesn't come anywhere close to meeting our motivations:

1. By mingling the externalization code into our business objects, it
   makes them larger and muddies their true purpose.
2. There's nothing doing any validation. Any such checking is left up
   to the object itself.
3. It's manual code to write and test for each of the many objects we
   can communicate. There's nothing automatic about it.

Let's see how this package helps us address each of those concerns in turn.
