from importlib.metadata import PackageNotFoundError, version


def get_version() -> str:
    try:
        return version("puny-manager")
    except PackageNotFoundError:
        return "unknown"
