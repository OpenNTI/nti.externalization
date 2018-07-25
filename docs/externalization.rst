=================
 Externalization
=================

.. _standard_fields:

Standard Fields
===============

Certain fields are generally useful for almost all objects. The names
of these fields along with descriptions of their expected contents are
contained in the namespace
:class:`~nti.externalization._base_interfaces.StandardExternalFields`.

The function `.to_standard_external_dictionary` is used to find and
populate many of these fields. It is called automatically by the
datastructures such as `~.InterfaceObjectIO`

Decorating
==========

Many times, we have additional information we want to include with an
external object that is somehow derived or not explicitly represented
in the interfaces implemented by an object. For example, in a web
application, we may want to provide an ``href`` value giving the URL
at which a particular object may be found. This URL is derived from
the currently executing request object in addition to the object being
externalized.

For this purpose, we use *decorators*. Decorators are `subscription
adapters`_ (or *subscribers*), meaning that there can be many of them
registered for any given object, that implement
:class:`~nti.externalization.interfaces.IExternalObjectDecorator`.
They can be registered just for the object, or for the object and the
request. Each time an object is externalized by
`~nti.externalization.to_external_object`, the registered decorators
will be invoked before the external object is returned.

Let's continue with the example address we used :ref:`before <autoPackageIO>`.


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

This time we'll create and register a decorator. Let's pretend that we
work in a sensitive system and we need to redact the addresses of
users to meet security concerns. Notice that decorators are usually
stateless, so it is faster to make them inherit from `.Singleton`.

.. code-block:: python

   from zope.interface import implementer
   from zope.component import adapter

   from nti.externalization.interfaces import IExternalObjectDecorator
   from nti.externalization.tests.benchmarks.interfaces import IAddress
   from nti.externalization.singleton import Singleton

   @implementer(IExternalObjectDecorator)
   @adapter(IAddress)
   class PrivateAddressDecorator(Singleton):

       def decorateExternalObject(self, address, external):
           for key in 'street_address_1', 'street_address_2', 'state', 'city', 'postal_code':
               del external[key]


We'll register our adapter and externalize:

   >>> from zope import component
   >>> component.provideSubscriptionAdapter(PrivateAddressDecorator)
   >>> from pprint import pprint
   >>> pprint(to_external_object(home_address))
    {u'Class': 'Address',
     u'MimeType': 'application/vnd.nextthought.benchmarks.address',
     'country': u'USA',
     'full_name': u'Steve Jobs'}


If we provide a request, adapters for the (object, request) are also
found:

.. code-block:: python

   class Request(object):
      url = 'http://example.com/path/'

   @implementer(IExternalObjectDecorator)
   @adapter(IAddress, Request)
   class LinkAddressDecorator(object):

       def __init__(self, context, request):
           self.request = request

       def decorateExternalObject(self, address, external):
           external['href'] = self.request.url + 'address'

We can now provide a request when we externalize (if no request
argument is given, the hook function `.get_current_request` is used to
look for a request):

   >>> component.provideSubscriptionAdapter(LinkAddressDecorator)
   >>> pprint(to_external_object(home_address, request=Request()))
    {u'Class': 'Address',
     u'MimeType': 'application/vnd.nextthought.benchmarks.address',
     'country': u'USA',
     'full_name': u'Steve Jobs',
     'href': 'http://example.com/path/address'}

IExternalMappingDecorator
-------------------------

There is also
`~nti.externalization.interfaces.IExternalMappingDecorator`. It is
called by `.to_standard_external_dictionary`. Typically that's *well
before* most of the object-specific fields have been filled in (e.g.,
from the object schema), and it is always before
``IExternalObjectDecorator`` is used. There may be occasional uses for
this, but it's best to stick to ``IExternalObjectDecorator``.

.. _subscription adapters: http://muthukadan.net/docs/zca.html#subscription-adapter

Dublin Core Metadata
--------------------

Decorators for :mod:`zope.dublincore` metadata are installed for all
objects by default. See :mod:`nti.externalization.dublincore` for more
information.
