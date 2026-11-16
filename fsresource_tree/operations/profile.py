"""Profile physical metadata through an explicit provider."""

from ..core.directory import Directory
from ..core.file import File
from ..profile import PhysicalProfile
from ..providers import FilesystemProviderProtocol, require_provider_operation


def profile(
    resource: Directory | File,
    *,
    provider: FilesystemProviderProtocol,
    update_cache: bool = False,
) -> PhysicalProfile:
    """Return a point-in-time physical metadata observation.

    By default this does not mutate the resource. Set update_cache=True to
    store the returned immutable snapshot on the resource as its latest
    cached physical observation. Query errors are propagated.
    """
    if not isinstance(resource, (Directory, File)):
        raise TypeError("resource must be a Directory or File")
    profile_physical = require_provider_operation(provider, "profile")
    observation = profile_physical(resource)
    if update_cache:
        resource._physical_profile = observation
    return observation


__all__ = ["profile"]
