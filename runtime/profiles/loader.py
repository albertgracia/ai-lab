from importlib import import_module


VALID_PROFILES = {
    "sandbox",
    "pilot",
    "observe",
    "production",
}


def load_profile(name: str = "pilot"):

    if name not in VALID_PROFILES:
        raise ValueError(f"Unknown profile: {name}")

    module = import_module(
        f"runtime.profiles.{name}"
    )

    return module.PROFILE
