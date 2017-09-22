=========
 Changes
=========


1.0.0 (unreleased)
==================

- First PyPI release.
- Add support for Python 3.
- Drop support for externalizing to plists. See
  https://github.com/NextThought/nti.externalization/issues/21
- Reach 100% test coverage and ensure we remain there through CI.
- Introduce ``nti.externalization.extension_points`` to hold hook
  functions. Move the Pyramid integration there (and deprecate that).
  Also move the NTIID support there (but the old name works too).
  See https://github.com/NextThought/nti.externalization/issues/27
