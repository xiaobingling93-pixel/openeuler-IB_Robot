"""Contract synthesis from robot configuration.

This module automatically generates inference service contracts
from robot_config.yaml, eliminating the need to manually maintain
separate contract YAML files.

The synthesized contract includes:
- Observation mappings from peripherals
- Action mappings from controller joints
- Model configuration
- Normalization parameters
"""

import os
from typing import Dict, Any, List
from pathlib import Path


class ContractSynthesisError(Exception):
    """Raised when contract synthesis fails due to architectural errors."""
    pass


def get_contract_output_path(robot_config: Dict, control_mode: str) -> str:
    """Get proper ROS2-compliant path for generated contract.

    Priority order:
    1. Environment variable ROBOT_CONFIG_CACHE_DIR (for containerized deployment)
    2. /tmp/robot_config/contracts/ (standard tmp location)
    3. Fallback to package share if needed

    Args:
        robot_config: Robot configuration dict
        control_mode: Active control mode name

    Returns:
        Absolute path for contract YAML file
    """
    # Option 1: Environment variable (for Docker/K8s)
    cache_dir = os.environ.get('ROBOT_CONFIG_CACHE_DIR')
    if cache_dir:
        return os.path.join(
            cache_dir,
            'contracts',
            f"{robot_config['name']}_{control_mode}.yaml"
        )

    # Option 2: Standard temp directory (recommended for single-machine)
    # Benefits: Auto-cleanup on reboot, not git-tracked, simple permissions
    contract_dir = '/tmp/robot_config/contracts'
    os.makedirs(contract_dir, exist_ok=True)
    return os.path.join(
        contract_dir,
        f"{robot_config['name']}_{control_mode}.yaml"
    )


def validate_control_mode_config(robot_config: Dict, control_mode: str) -> None:
    """Validate control mode configuration BEFORE synthesis.

    This performs architectural validation to catch configuration errors
    at system startup time, not during inference.

    Args:
        robot_config: Full robot configuration dict
        control_mode: Control mode name to validate

    Raises:
        ContractSynthesisError: If configuration is architecturally invalid
    """
    errors = []
    warnings = []

    # Check 1: Control mode exists
    control_modes = robot_config.get('control_modes', {})
    if control_mode not in control_modes:
        errors.append(f"Control mode '{control_mode}' not defined in robot_config")
        raise ContractSynthesisError("\n".join(errors))

    mode_config = control_modes[control_mode]

    # Check 2: Inference configuration
    inference_config = mode_config.get('inference', {})
    if inference_config.get('enabled', False):

        # Check 2.1: Model reference exists
        model_name = inference_config.get('model')
        models = robot_config.get('models', {})
        if model_name not in models:
            errors.append(
                f"Control mode '{control_mode}' requires model '{model_name}' "
                f"but it's not defined in robot_config.models"
            )

        # Check 2.2: Contract observations exist (Single Source of Truth)
        contract_config = robot_config.get('contract', {})
        observations = contract_config.get('observations', [])
        
        if not observations:
            errors.append(
                f"No observations defined in contract section. "
                f"Please add 'contract.observations' to robot_config.yaml"
            )
        else:
            # Validate observation peripheral references
            for obs_spec in observations:
                peripheral_name = obs_spec.get('peripheral')
                if peripheral_name:
                    peripheral = next(
                        (p for p in robot_config.get('peripherals', []) if p['name'] == peripheral_name),
                        None
                    )
                    if not peripheral:
                        errors.append(
                            f"Observation '{obs_spec.get('key')}' references peripheral '{peripheral_name}' "
                            f"but it's not defined in robot_config.peripherals"
                        )

    # Check 3: Executor configuration
    executor_config = mode_config.get('executor', {})
    executor_type = executor_config.get('type')
    if executor_type and executor_type not in ['topic', 'action']:
        errors.append(
            f"Invalid executor type '{executor_type}' in mode '{control_mode}'. "
            f"Must be 'topic' or 'action'"
        )

    # Check 4: Controllers exist
    controllers = mode_config.get('controllers', [])
    ros2_control_config = robot_config.get('ros2_control', {})
    defined_controllers = ros2_control_config.get('controllers', [])

    for ctrl in controllers:
        if ctrl not in defined_controllers:
            warnings.append(
                f"Controller '{ctrl}' used in mode '{control_mode}' "
                f"but not listed in ros2_control.controllers"
            )

    # Report results
    if warnings:
        print(f"[robot_config] ⚠ Configuration warnings for mode '{control_mode}':")
        for warning in warnings:
            print(f"  - {warning}")

    if errors:
        error_msg = (
            f"❌ Architectural errors in control mode '{control_mode}':\n" +
            "\n".join(f"  - {e}" for e in errors)
        )
        print(f"[robot_config] {error_msg}")
        raise ContractSynthesisError(error_msg)


def synthesize_contract(robot_config: Dict, control_mode: str) -> Dict[str, Any]:
    """Synthesize inference contract from robot configuration.

    This function automatically builds the contract by using the contract section
    from robot_config.yaml as the Single Source of Truth for observations and actions.

    Args:
        robot_config: Full robot configuration dict
        control_mode: Active control mode name

    Returns:
        Contract dictionary compatible with inference_service

    Raises:
        ContractSynthesisError: If configuration is architecturally invalid
    """
    print(f"[robot_config] ========== Contract Synthesis ==========")
    print(f"[robot_config] Control mode: {control_mode}")

    # Step 1: Validate configuration FIRST
    try:
        validate_control_mode_config(robot_config, control_mode)
    except ContractSynthesisError as e:
        print(f"[robot_config] ✗ Contract synthesis FAILED")
        raise

    # Step 2: Get mode configuration
    mode_config = robot_config['control_modes'][control_mode]
    inference_config = mode_config.get('inference', {})

    if not inference_config.get('enabled', False):
        print(f"[robot_config] Inference not enabled for mode '{control_mode}'")
        return None

    # Step 3: Get model configuration
    model_name = inference_config['model']
    models = robot_config.get('models', {})
    if model_name not in models:
        print(f"[robot_config] ERROR: Model '{model_name}' not found")
        return None

    model_config = models[model_name]

    # Step 4: Get contract configuration (Single Source of Truth)
    contract_config = robot_config.get('contract', {})
    
    # Use contract.observations directly (Single Source of Truth)
    observations = contract_config.get('observations', [])
    if not observations:
        print(f"[robot_config] ERROR: No observations defined in contract section")
        return None
    
    print(f"[robot_config] Observations from contract section (Single Source of Truth):")
    for obs in observations:
        print(f"[robot_config]   - {obs.get('key')} ← {obs.get('topic')}")

    # Use contract.actions directly (Single Source of Truth)
    actions = contract_config.get('actions', [])
    if not actions:
        print(f"[robot_config] ERROR: No actions defined in contract section")
        return None
    
    print(f"[robot_config] Actions from contract section (Single Source of Truth):")
    for act in actions:
        pub = act.get('publish', {})
        print(f"[robot_config]   - {act.get('key')} → {pub.get('topic', 'N/A')}")

    # Step 5: Assemble contract with rosetta-compliant structure
    contract = {
        'name': f"{robot_config['name']}_{control_mode}",
        'version': 1,
        'robot_type': robot_config.get('robot_type', 'so_101'),
        'rate_hz': contract_config.get('rate_hz', 20),
        'max_duration_s': contract_config.get('max_duration_s', 90.0),
        'model': {
            'policy_type': model_config.get('policy_type', 'act'),
            'path': model_config['path']
        },
        'observations': observations,
        'actions': actions,
        'metadata': {
            'robot_name': robot_config['name'],
            'control_mode': control_mode,
            'generated_by': 'robot_config.contract_builder',
            'version': '1.0'
        }
    }

    # Optional: Add normalization if specified
    if 'normalization' in model_config:
        contract['normalization'] = model_config['normalization']
        print(f"[robot_config] Normalization: {model_config['normalization']}")

    print(f"[robot_config] ✓ Contract synthesis SUCCESS")
    print(f"[robot_config]   Observations: {len(observations)}")
    print(f"[robot_config]   Actions: {len(actions)}")
    return contract


def save_contract(contract: Dict, output_path: str) -> None:
    """Save synthesized contract to YAML file.

    Args:
        contract: Contract dictionary
        output_path: Path to save contract YAML
    """
    import yaml

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        yaml.dump(contract, f, default_flow_style=False, sort_keys=False)

    print(f"[robot_config] Contract saved to: {output_path}")
