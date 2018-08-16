=================
 Internalization
=================

We can create or update an existing object using external data with
the functions :func:`~nti.externalization.new_from_external_object` or
:func:`~nti.externalization.update_from_external_object`, respectively.

In a web framework like Pyramid where an application object is located
by route matching or `traversal`_, ``update_from_external_object``
makes the most sense.

.. _traversal: https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/traversal.html

.. _factories:

Factories
=========

While updating objects, internalization will, by default, create a new
instance for every mapping that contains a ``MimeType`` or ``Class``
key using `Zope Component factories`_. Factories are named utilities,
that implement ``IFactory`` (essentially, a callable of no arguments)
This package uses extensions of that interface, namely
`~nti.externalization.interfaces.IMimeObjectFactory`,
`~nti.externalization.interfaces.IClassObjectFactory` and
`~nti.externalization.interfaces.IAnonymousObjectFactory` (whose
default implementations are found in
:mod:`nti.externalization.factory`).

The factory matching ``MimeType`` is preferred, but we can fall back
to one matching ``Class`` if needed.

Factories are usually registered automatically by
`ext:registerAutoPackageIO
<nti.externalization.zcml.IAutoPackageExternalizationDirective>` at the
same time it creates the ``InterfaceObjectIO`` adapters.

You can manually register factories from particular modules using
`ext:registerMimeFactories
<nti.externalization.zcml.IRegisterInternalizationMimeFactoriesDirective>`.

Lets look at the factories registered for our address:

   >>> from zope import component
   >>> from nti.externalization.interfaces import IMimeObjectFactory
   >>> import nti.externalization.tests.benchmarks
   >>> _ = xmlconfig.file('configure.zcml', nti.externalization.tests.benchmarks)
   >>> factory = component.getUtility(IMimeObjectFactory, 'application/vnd.nextthought.benchmarks.address')
   >>> factory
   <MimeObjectFactory titled 'Address' using <class 'nti.externalization.tests.benchmarks.objects.Address'>...>
   >>> factory()
   <nti.externalization.tests.benchmarks.objects.Address ...>

.. _Zope Component factories: http://muthukadan.net/docs/zca.html#factory

Mime Types are found in the class attribute ``mimeType``;
``ext:registerAutoPackageIO`` will add computed ``mimeType`` values to
factory objects if needed.
