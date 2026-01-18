from importlib.metadata import version, PackageNotFoundError

def get_version() -> str:
    try:
        return version("puny-manager")
    except PackageNotFoundError:
        return "unknown"
