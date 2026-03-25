from depscan.registry import npm_license_from_payload, pypi_license_from_payload


def test_npm_license_string():
    lic, err = npm_license_from_payload({"license": "MIT"})
    assert lic == "MIT"
    assert not err


def test_npm_license_object():
    lic, err = npm_license_from_payload({"license": {"type": "ISC"}})
    assert lic == "ISC"
    assert not err


def test_npm_license_from_latest_version():
    data = {
        "dist-tags": {"latest": "1.0.0"},
        "versions": {"1.0.0": {"license": "Apache-2.0"}},
    }
    lic, err = npm_license_from_payload(data)
    assert lic == "Apache-2.0"
    assert not err


def test_pypi_license_field():
    lic, err = pypi_license_from_payload(
        {"info": {"license": "BSD-3-Clause", "classifiers": []}}
    )
    assert lic == "BSD-3-Clause"
    assert not err


def test_pypi_license_from_classifiers():
    lic, err = pypi_license_from_payload(
        {
            "info": {
                "license": "",
                "classifiers": ["License :: OSI Approved :: MIT License"],
            }
        }
    )
    assert lic == "MIT License"
    assert not err
