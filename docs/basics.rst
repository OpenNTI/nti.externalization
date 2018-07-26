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
`~nti.externalization.to_external_object`:

  >>> from pprint import pprint
  >>> pprint(to_external_object(InternalObject()))
  {'A Letter': 'a', 'The Number': 42}

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


Adapters and Configuration
==========================

This package makes heavy use of the `Zope Component Architecture`_ to
abstract away details and separate concerns. Most commonly this is
configured using `ZCML <mod:zope.configuration>`_, and this package
ships with a ``configure.zcml`` that you should load:

  >>> from zope.configuration import xmlconfig
  >>> import nti.externalization
  >>> xmlconfig.file('configure.zcml', nti.externalization)
  <zope.configuration.config.ConfigurationMachine ...>

The ``toExternalObject`` method is defined by the
`nti.externalization.interfaces.IInternalObjectExternalizer`
interface, and the ``updateFromExternalObject`` method is defined by
`nti.externalization.interfaces.IInternalObjectUpdater` interface.
Because it is common that one object both reads and writes the
external representation, the two interfaces are joined together in
`nti.externalization.interfaces.IInternalObjectIO`. Let's create a new
internal object:

.. code-block:: python

   class InternalObject(object):
       def __init__(self, id=''):
           self._field1 = 'a'
           self._field2 = 42
           self._id = id

       def __repr__(self):
           return '<%s %r letter=%r number=%d>' % (
               self.__class__.__name__, self._id, self._field1, self._field2)


Now we will write an ``IInternalObjectIO`` adapter for it:

.. code-block:: python

   from zope.interface import implementer
   from zope.component import adapter

   from nti.externalization.interfaces import IInternalObjectIO

   @implementer(IInternalObjectIO)
   @adapter(InternalObject)
   class InternalObjectIO(object):
       def __init__(self, context):
           self.context = context

       def toExternalObject(self, **kwargs):
          return {'Letter': self.context._field1, 'Number': self.context._field2}

       def updateFromExternalObject(self, external_object, context=None):
            self.context._field1 = external_object['Letter']
            self.context._field2 = external_object['Number']


We can register the adapter (normally this would be done in ZCML) and
use it:

.. code-block:: xml

   <configure xmlns="http://namespaces.zope.org/zope">
       <include package="nti.externalization" />
       <adapter factory=".InternalObjectIO" />
   </configure>

Because we don't have a Python package to put this ZCML in, we'll
register it manually.

  >>> from zope import component
  >>> component.provideAdapter(InternalObjectIO)
  >>> internal = InternalObject('original')
  >>> internal
  <InternalObject 'original' letter='a' number=42>
  >>> pprint(to_external_object(internal))
  {'Letter': 'a', 'Number': 42}
  >>> update_from_external_object(internal, {'Letter': 'b', 'Number': 3})
  <InternalObject 'original' letter='b' number=3>

By using adapters like this, we can separate out externalization from
our core logic. Of course, that's still a lot of manual code to write.


Using Schemas for Validation and Automatic Externalization
==========================================================

Most application objects will implement one or more interfaces. When
those interfaces contain attributes from :mod:`zope.schema.field` or
:mod:`nti.schema.field`, they are also called schemas. This package can
automate the entire externalization process, including validation,
based on the schemas an object implements.

Let's start by writing a simple schema.

.. code-block:: python

    from zope.interface import Interface
    from zope.interface import taggedValue

    from nti.schema.field import ValidTextLine

    class IAddress(Interface):

        full_name = ValidTextLine(title=u"First name", required=True)

        street_address_1 = ValidTextLine(title=u"Street line 1",
                                         max_length=75, required=True)

        street_address_2 = ValidTextLine(title=u"Street line 2",
                                         required=False, max_length=75)

        city = ValidTextLine(title=u"City name", required=True)

        state = ValidTextLine(title=u"State name",
                              required=False, max_length=10)

        postal_code = ValidTextLine(title=u"Postal code",
                                    required=False, max_length=30)

        country = ValidTextLine(title=u"Nation name", required=True)

And now an implementation of that interface.

.. code-block:: python

   from nti.schema.fieldproperty import createDirectFieldProperties
   from nti.schema.schema import SchemaConfigured

   @implementer(IAddress)
   class Address(SchemaConfigured):
        createDirectFieldProperties(IAddress)

Externalizing based on the schema is done with `.InterfaceObjectIO`.
We'll create a subclass to configure it.

.. code-block:: python

   from nti.externalization.datastructures import InterfaceObjectIO

   @adapter(IAddress)
   class AddressIO(InterfaceObjectIO):
       _ext_iface_upper_bound = IAddress


Now we can register and use it as before:


   >>> component.provideAdapter(AddressIO)
   >>> address = Address(full_name=u'Steve Jobs',
   ...    street_address_1=u'One Infinite Loop',
   ...    city=u'Cupertino',
   ...    state=u'CA',
   ...    postal_code=u'95014',
   ...    country=u'USA')
   >>> external = to_external_object(address)
   >>> pprint(external)
   {u'Class': 'Address',
     'city': u'Cupertino',
     'country': u'USA',
     'full_name': u'Steve Jobs',
     'postal_code': u'95014',
     'state': u'CA',
     'street_address_1': u'One Infinite Loop',
     'street_address_2': None}

Oops, One Infinte Loop was Apple's old address. They've since moved
into `their new headquarters`_:

   >>> external['street_address_1'] = u'One Apple Park Way'
   >>> _ = update_from_external_object(address, external)
   >>> address.street_address_1
   'One Apple Park Way'

Notice that our schema declared a number of constraints. For instance,
the ``full_name`` is required, and the ``state`` cannot be longer than
ten characters. Let's see what happens when we try to violate these
conditions:

   >>> external['state'] = u'Commonwealth of Massachusetts'
   >>> update_from_external_object(address, external)
   Traceback (most recent call last):
   ...
   TooLong: ('State is too long.', 'state', u'Commonwealth of Massachusetts')
   >>> external['state'] = u'CA'
   >>> external['full_name'] = None
   >>> update_from_external_object(address, external)
   Traceback (most recent call last):
   ...
   zope.schema._bootstrapinterfaces.RequiredMissing: full_name

Much better! We get validation of our constraints and we didn't have
to write much code. But, we still had to write *some* code, one class
for each object we're externalizing. Can we do better?

.. _Zope Component Architecture: http://muthukadan.net/docs/zca.html
.. _their new headquarters: https://appleinsider.com/articles/18/02/16/apple-park-now-apples-official-corporate-address

.. _autoPackageIO:

autoPackageIO: Handing responsibility to the framework
======================================================

The answer is yes, we can do much better, with the
:class:`ext:registerAutoPackageIO
<nti.externalization.zcml.IAutoPackageExternalizationDirective>`
ZCML directive.

.. note::
   ``ext:registerAutoPackageIO`` is biased for a conventional setup of
   a single package: one or more root interfaces in ``interfaces.py``,
   one or more modules defining factories (classes) implementing those
   interfaces. To an extent this can be changed using the ``iobase``
   argument.

The above example schema is taken from the tests distributed with this
package in ``nti.externalization.tests.benchmarks``. That package
provides the schema (as shown above), an implementation of it, and
the ZCML file that pulls it all together with one directive.

Here's the schema, along with several other schema to define a rich
user profile, in ``interfaces.py``:

.. literalinclude:: ../src/nti/externalization/tests/benchmarks/profileinterfaces.py
   :language: python

They are implemented in ``objects.py`` very simply (as above):

.. ignore-next-block

.. code-block:: python

   @interface.implementer(interfaces.IAddress)
   @EqHash('full_name', 'street_address_1', 'postal_code')
   @WithRepr
   class Address(SchemaConfigured):
       createDirectFieldProperties(interfaces.IAddress)

   @interface.implementer(interfaces.IUserProfile)
   @EqHash('addresses', 'alias', 'phones', 'realname')
   @WithRepr
   class UserProfile(SchemaConfigured):
        createFieldProperties(interfaces.IUserProfile)


Finally, the ZCML file contains one directive that ties everything together:

.. literalinclude:: ../src/nti/externalization/tests/benchmarks/profileconfigure.zcml
   :language: xml


If we configure this file, we can create and update addresses. We'll
do so through their container object, the ``UserProfile``, thus
demonstrating that nested schemas and objects are possible.

   >>> import nti.externalization.tests.benchmarks
   >>> _ = xmlconfig.file('configure.zcml', nti.externalization.tests.benchmarks)
   >>> from nti.externalization.tests.benchmarks.objects import Address
   >>> from nti.externalization.tests.benchmarks.objects import UserProfile
   >>> home_address = Address(
   ...     full_name=u'Steve Jobs',
   ...     street_address_1=u'1313 Mockingbird Lane',
   ...     city=u'Salem',
   ...     state=u'MA',
   ...     postal_code=u'6666',
   ...     country=u'USA',
   ... )
   >>> work_address = Address(
   ...     full_name=u'Apple',
   ...     street_address_1=u'1 Infinite Loop',
   ...     city=u'Cupertino',
   ...     state=u'CA',
   ...     postal_code=u'55555',
   ...     country=u'USA',
   ...  )
   >>> user_profile = UserProfile(
   ...     addresses={u'home': home_address, u'work': work_address},
   ...     phones={u'home': u'405-555-1212', u'work': u'405-555-2323'},
   ...     contact_emails={u'home': u'steve.jobs@gmail.com', u'work': u'steve@apple.com'},
   ...     avatarURL='http://apple.com/steve.png',
   ...     backgroundURL='https://apple.com/bg.jpeg',
   ...     alias=u'Steve',
   ...     realname=u'Steve Jobs',
   ... )
   >>> external = to_external_object(user_profile)
   >>> pprint(external)
   {u'Class': 'UserProfile',
     u'MimeType': 'application/vnd.nextthought.benchmarks.userprofile',
     'addresses': {u'home': {u'Class': 'Address',
                             u'MimeType': 'application/vnd.nextthought.benchmarks.address',
                             'city': u'Salem',
                             'country': u'USA',
                             'full_name': u'Steve Jobs',
                             'postal_code': u'6666',
                             'state': u'MA',
                             'street_address_1': u'1313 Mockingbird Lane',
                             'street_address_2': None},
                   u'work': {u'Class': 'Address',
                             u'MimeType': 'application/vnd.nextthought.benchmarks.address',
                             'city': u'Cupertino',
                             'country': u'USA',
                             'full_name': u'Apple',
                             'postal_code': u'55555',
                             'state': u'CA',
                             'street_address_1': u'1 Infinite Loop',
                             'street_address_2': None}},
     'alias': u'Steve',
     'avatarURL': 'http://apple.com/steve.png',
     'backgroundURL': 'https://apple.com/bg.jpeg',
     'contact_emails': {u'home': u'steve.jobs@gmail.com',
                        u'work': u'steve@apple.com'},
     'phones': {u'home': u'405-555-1212', u'work': u'405-555-2323'},
     'realname': u'Steve Jobs'}

Notice that there are some additional bits of data in the external
form that are not specified in the interface. Here, that's ``Class``
and ``MimeType``. These are two of the :ref:`standard_fields`.

Let's make a change to the work address:

    >>> external['addresses'][u'work']['street_address_1'] = u'One Apple Park Way'
    >>> _ = update_from_external_object(user_profile, external)
    >>> user_profile.addresses['work'].street_address_1
    u'One Apple Park Way'

Importantly, note that, by default, the nested objects are created
fresh and *not* mutated.

    >>> user_profile.addresses['work'] is work_address
    False

This is described in more detail in :ref:`factories`.

Representations
===============

Being able to get a Python dictionary from an object, and update an
object given a Python dictionary, is nice, but it doesn't go all the
way toward solving the goals of this package, interoperating with
remote clients using a text (or byte) based stream.

For that, we have the :mod:`nti.externalization.representation`
module, and its key interface
`~nti.externalization.interfaces.IExternalObjectIO`.

A *representation* is a format that can serialize Python dictionaries
to text, and given that text, produce a Python dictionary. This
package provides two representations by default, JSON and YAML. These
are named utilities providing ``IExternalObjectIO``. The function
`nti.externalization.to_external_representation` is a shortcut for dumping to a string:

    >>> from nti.externalization import to_external_representation
    >>> from nti.externalization.interfaces import EXT_REPR_JSON, EXT_REPR_YAML
    >>> to_external_representation(address, EXT_REPR_JSON)
    '{"Class": "Address", "city": "Cupertino",...
    >>> to_external_representation(address, EXT_REPR_YAML)
    "{Class: Address, city: Cupertino, country: USA,...

Loading from a string doesn't have a shortcut, we need to use the
utility:

    >>> from nti.externalization.interfaces import IExternalObjectIO
    >>> external = to_external_object(address)
    >>> yaml_io = component.getUtility(IExternalObjectIO, EXT_REPR_YAML)
    >>> ext_yaml_str = yaml_io.dump(external)
    >>> external_from_yaml = yaml_io.load(ext_yaml_str)
    >>> external_from_yaml == external
    True
