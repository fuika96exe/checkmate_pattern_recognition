"""Versions of the package, its two rule sets and its output schema.

When to bump which (the package README will spell this out, phase 0 step 8):

- ``MIDGAME_RULES_VERSION`` / ``CHECKMATE_RULES_VERSION``: whenever a label,
  pattern or evidence rule changes.  Update the matching rules document in
  ``docs/`` at the same time.
- ``SCHEMA_VERSION``: whenever the shape of a result's ``to_dict()`` changes.
- ``PACKAGE_VERSION``: for every copy vendored into another repository.

During phase 0 the lab modules still define their own rules-version constants;
``tests/test_xq_classify_version.py`` keeps the two in step until those
modules read the values from here.
"""

PACKAGE_VERSION = '0.1.0'
MIDGAME_RULES_VERSION = 'midgame-tactics-3.1'
CHECKMATE_RULES_VERSION = 'checkmate-patterns-2026.11.05-v15'
SCHEMA_VERSION = '1.0'
