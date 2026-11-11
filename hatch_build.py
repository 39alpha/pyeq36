"""Provide a hatch build hook to tag wheels for their platform, but not their Python version."""

import sys

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from packaging.tags import sys_tags


class CustomHook(BuildHookInterface):
    """
    Tag wheels as `py3-none-<platform>`.

    The wheels bundle compiled EQ3/6 executables, so they are specific to a
    platform. However, they contain no Python extension modules, so a single
    wheel works with any version of Python 3. This lets cibuildwheel build one
    wheel per platform and reuse it for every Python version.
    """

    def initialize(self, version, build_data):
        """
        Set the wheel tag to `py3-none-<platform>`.

        The platform is chosen as hatchling does when inferring a tag: the
        first supported platform which is neither manylinux nor musllinux
        (auditwheel repairs the tag later), adjusted on macOS to respect
        `MACOSX_DEPLOYMENT_TARGET`.

        @param version    The version of the target being built
        @param build_data The build data, updated in place
        """
        tag = next(t for t in sys_tags() if "manylinux" not in t.platform and "musllinux" not in t.platform)
        platform = tag.platform
        if sys.platform == "darwin":
            from hatchling.builders.macos import process_macos_plat_tag

            platform = process_macos_plat_tag(platform, compat=False)

        build_data["tag"] = f"py3-none-{platform}"
        build_data["pure_python"] = False
