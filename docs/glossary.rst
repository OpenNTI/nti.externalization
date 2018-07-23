==========
 Glossary
==========

.. glossary::

   schema
       A `zope.interface.Interface` interface, whose attributes are
       `zope.schema.Field` instances. ``zope.schema`` defines
       a number of useful field types such as `zope.schema.Date`.
       `nti.schema.field` provides even more, such as
       `nti.schema.field.Variant`.

       See :doc:`schemas` for more information.

   internal object

       A Python object in the application domain (sometimes known as a
       "model" object). This may be a complex object consisting of
       multiple nested objects. It may use inheritance. It will
       implement one or more :term:`schema`.

   external object

       A dictionary with string keys, and values that are strings,
       numbers (including booleans), None, lists of external objects,
       or external objects.

       In other words, a simplified interchange format capable of
       being represented by many programming languages and text
       formats.

   standard external object

       An external object produced by this package and having some
       defined keys and values. The most important of these is
       `.StandardExternalFields.MIMETYPE`, which helps identify
       the class of the :term:`internal object`.

   anonymous external object

       An external object often not produced by this package and
       lacking the defining metadata this package produces.

   external representation

       The byte string resulting from converting an :term:`external
       object` into a particular textual interchange format such as
       JSON or YAML.

       External representations are read and written using
       :class:`~nti.externalization.interfaces.IExternalObjectIO` utilities.

   externalization

       The process of creating a :term:`external object` from a
       :term:`internal object`. The API for this is
       :func:`nti.externalization.to_external_object`, and it is
       customized with
       :class:`~nti.externalization.interfaces.IInternalObjectExternalizer` adapters.

       Sometimes this also means creating the :term:`external
       representation`. If done at the same time, the API for this is
       :func:`nti.externalization.to_external_representation`.

   internalization

       The process of taking an :term:`external object` and using it
       to mutate an :term:`internal object`. The API for this is
       :func:`nti.externalization.update_from_external_object`.

       Sub-objects are freshly created using :term:`factories
       <factory>`.

   factory

       A callable object taking no arguments and returning a
       particular type of :term:`internal object`. Typically these are
       (wrappers around) Python classes; the classes typically need to
       have an attribute ``__external_can_create__`` set to a true
       value.

       .. seealso:: :doc:`api/factory`.
