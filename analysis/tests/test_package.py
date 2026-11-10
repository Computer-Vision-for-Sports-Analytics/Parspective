import parspective


def test_package_exposes_versions():
    assert parspective.__version__
    assert parspective.SCHEMA_VERSION == "1.0"
