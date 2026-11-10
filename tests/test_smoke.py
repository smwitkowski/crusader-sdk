from importlib.metadata import version

import crusader


def test_version_matches_package_metadata():
    assert crusader.__version__ == version("crusader-sdk")
