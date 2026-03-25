"""Simulation backend registry and factory.

Usage:
    from robot_config.launch_builders.sim_backend import get_sim_backend

    adapter = get_sim_backend("gazebo")      # GazeboAdapter instance
    adapter = get_sim_backend("mujoco")      # MujocoAdapter instance (T6)

The platform string comes from robot_config['simulation']['platform'] in
the robot YAML (e.g., so101_single_arm.yaml).
"""

from .base_adapter import SimBackendAdapter
from .gazebo_adapter import GazeboAdapter
from .mujoco_adapter import MujocoAdapter

__all__ = ["SimBackendAdapter", "GazeboAdapter", "MujocoAdapter", "get_sim_backend"]

_BACKEND_REGISTRY: dict[str, type[SimBackendAdapter]] = {
    "gazebo": GazeboAdapter,
    "mujoco": MujocoAdapter,
}


def get_sim_backend(platform: str) -> SimBackendAdapter:
    """Instantiate a simulation backend adapter by platform name.

    Args:
        platform: Backend identifier, e.g. 'gazebo' or 'mujoco'.
                  Must match a key in _BACKEND_REGISTRY.

    Returns:
        A fresh SimBackendAdapter instance for the requested platform.

    Raises:
        ValueError: If platform is not registered.
    """
    cls = _BACKEND_REGISTRY.get(platform)
    if cls is None:
        available = list(_BACKEND_REGISTRY.keys())
        raise ValueError(
            f"Unknown sim platform: '{platform}'. "
            f"Available platforms: {available}. "
            f"Check simulation.platform in your robot YAML."
        )
    return cls()
