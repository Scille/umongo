================
Releasing μMongo
================

Prerequisites
-------------

- Install bumpversion_. The easiest way is to create and activate a virtualenv,
  and then run ``pip install -r requirements_dev.txt``.

Steps
-----

#. Add an entry to ``CHANGELOG.rst``, or update the ``Unreleased`` entry, with the
   new version and the date of release. Include any bug fixes, features, or
   backwards incompatibilities included in this release.
#. Commit the changes to ``CHANGELOG.rst``.
#. Run bumpversion_ to update the version string in ``umongo/__init__.py`` and
   ``setup.py``.

   * You can combine this step and the previous one by using the ``--allow-dirty``
     flag when running bumpversion_ to make a single release commit.

#. Run ``git push`` to push the release commits to github.
#. Once the CI tests pass, run ``git push --tags`` to push the tag to github and
   trigger the release to pypi.

.. _bumpversion: https://pypi.org/project/bumpversion/
