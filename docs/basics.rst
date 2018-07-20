=============
 Basic Usage
=============

This document provides an overview of ``nti.externalization`` and
shows some simple examples of its usage.

Reading through the :doc:`glossary` before beginning is highly
recommended.

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


Motivation
==========

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
