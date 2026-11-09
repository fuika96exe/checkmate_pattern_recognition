"""The lab's rules-version constants must stay the ones in xq_classify.version.

A second copy on either side would ship labels under the wrong version.
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
