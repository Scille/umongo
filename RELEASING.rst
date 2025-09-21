================
Releasing μMongo
================

Steps
-----

#. Add an entry to ``CHANGELOG.rst``, or update the ``Unreleased`` entry, with the
   new version and the date of release. Include any bug fixes, features, or
   backwards incompatibilities included in this release.
#. Commit the changes to ``CHANGELOG.rst``.
#. Update ``messages.pot`` file and examples .po and .mo files.
#. Update version number in ``pyproject.toml``.
#. Run ``git push`` to push the release commits to github.
#. Once the CI tests pass, run ``git push --tags`` to push the tag to github and
   trigger the release to pypi.
