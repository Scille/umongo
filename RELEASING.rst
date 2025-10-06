================
Releasing μMongo
================

Steps
-----

#. Add an entry to ``CHANGELOG.rst``, or update the ``Unreleased`` entry, with the
   new version and the date of release. Include any bug fixes, features, or
   backwards incompatibilities included in this release.

#. Commit the changes to ``CHANGELOG.rst``.

    $ git add CHANGELOG.rst
    $ git commit -m "Update CHANGELOG.rst"

#. Update ``messages.pot`` file using ``extract`` command and manual edition.

    $ pybabel extract  -o messages.pot . --project=umongo --copyright-holder="Scille SAS and contributors"

#. Update .po and .mo files.

    $ pybabel update -d examples/flask/translations/ -i messages.pot
    $ pybabel compile -d examples/flask/translations/

#. Update version number in ``pyproject.toml`` then commit.

    $ git add pyproject.toml
    $ git commit -m "Bump version"

#. Create the new version tag (replace with actual version).

    $ git tag x.y.z

#. Push the release commits and tag.

    $ git push
    $ git push origin x.y.z
