"""xq_classify.version must match the lab's rules-version constants.

Until phase 0 steps 4 and 5 make the lab modules read their versions from
the package, the same value lives in two places. A rule change that bumps one
and not the other would ship labels under the wrong version.
"""
import xq_classify
from app.midgame_tactics import RULES_VERSION
from app.patterns import CHECKMATE_RULES_VERSION


def test_rules_versions_match_lab_modules():
    assert xq_classify.MIDGAME_RULES_VERSION == RULES_VERSION
    assert xq_classify.CHECKMATE_RULES_VERSION == CHECKMATE_RULES_VERSION


def test_package_version_is_exported():
    assert xq_classify.__version__ == xq_classify.PACKAGE_VERSION
    assert xq_classify.SCHEMA_VERSION
