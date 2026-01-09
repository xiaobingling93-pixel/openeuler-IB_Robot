#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VariantPolicyBridge: Simplified policy inference node for VariantsList messages.

This node:
1. Subscribes to rosetta_interfaces/msg/VariantsList
2. Buffers incoming variants using StreamBuffer
3. Samples variants at contract-specified frequency
4. Runs policy inference and publishes actions
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile
from rosidl_runtime_py.utilities import get_message
import torch

from lerobot.policies.factory import get_policy_class, make_pre_post_processors

from rosetta.common.contract_utils import (
    load_contract,
    iter_specs,
    SpecView,
    StreamBuffer,
    encode_value,
)
from rosetta.common.decoders import dec_variant_list


def _device_from_param(requested: Optional[str] = None) -> torch.device:
    """Parse device parameter and return torch device."""
    r = (requested or "auto").lower().strip()

    def mps_available() -> bool:
        return bool(getattr(torch.backends, "mps", None)) and torch.backends.mps.is_available()

    if r == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        if mps_available():
            return torch.device("mps")
        return torch.device("cpu")

    if r.startswith("cuda"):
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA requested but not available.")
        return torch.device(r)

    if r in {"mps", "metal"}:
        if not mps_available():
            raise RuntimeError("MPS requested but not available.")
        return torch.device("mps")

    try:
        return torch.device(r)
    except (TypeError, ValueError, RuntimeError):
        return torch.device("cpu")


class VariantPolicyBridge(Node):
    """Simplified policy bridge for VariantsList input."""

    def __init__(self) -> None:
        super().__init__("variant_policy_bridge")

        # Parameters
        self.declare_parameter("contract_path", "")
        self.declare_parameter("policy_path", "")
        self.declare_parameter("policy_device", "auto")

        # Load contract
        contract_path = str(self.get_parameter("contract_path").value or "")
        if not contract_path:
            raise RuntimeError("contract_path is required")
        self._contract = load_contract(Path(contract_path))

        # Get variant topic from contract
        variant_topic = self._contract.process.get("variant_topic_name", "/rosetta/batch")

        # Setup specs
        self._specs: List[SpecView] = list(iter_specs(self._contract))
        self._action_specs = [s for s in self._specs if s.is_action]

        # Setup device
        self.device = _device_from_param(str(self.get_parameter("policy_device").value))
        self.get_logger().info(f"Using device: {self.device}")

        # Setup execution frequency
        self.fps = int(self._contract.rate_hz)
        if self.fps <= 0:
            raise ValueError("Contract rate_hz must be >= 1")
        self.step_ns = int(round(1e9 / self.fps))
        self.step_sec = 1.0 / self.fps

        # Load policy
        policy_path = str(self.get_parameter("policy_path").value or "")
        if not policy_path:
            raise RuntimeError("policy_path is required")
        
        if not os.path.exists(policy_path):
            raise FileNotFoundError(f"Policy path does not exist: {policy_path}")

        cfg_json = os.path.join(policy_path, "config.json")
        policy_cfg = {}
        policy_type = ""
        try:
            if os.path.exists(cfg_json):
                with open(cfg_json, "r", encoding="utf-8") as f:
                    policy_cfg = json.load(f)
                    policy_type = str(policy_cfg.get("type", "")).lower()
        except (OSError, json.JSONDecodeError) as e:
            self.get_logger().warning(f"Could not read policy config.json: {e!r}")

        # Initialize policy
        if not policy_type:
            raise ValueError("Could not determine policy type from config.json")
        
        policy_class = get_policy_class(policy_type)
        self.policy = policy_class.from_pretrained(policy_path)
        self.get_logger().info(f"Loaded policy: {policy_class.__name__}")

        # Setup pre/post processors
        _, self.postprocessor = make_pre_post_processors(
            policy_cfg=policy_cfg,
            pretrained_path=policy_path,
            preprocessor_overrides={"device_processor": {"device": str(self.device)}},
            postprocessor_overrides={"device_processor": {"device": str(self.device)}},
        )

        # TODO: convert to streambuffer
        self._variant_buffer = {}

        # Setup publishers for actions
        self._act_pubs: Dict[str, Any] = {}
        for spec in self._action_specs:
            msg_cls = get_message(spec.ros_type)
            pub = self.create_publisher(msg_cls, spec.topic, 10)
            self._act_pubs[spec.topic] = pub
            self.get_logger().info(f"Created action publisher: {spec.topic}")

        # Setup subscription
        self._cbg = ReentrantCallbackGroup()
        variant_msg_cls = get_message("rosetta_interfaces/msg/VariantsList")
        self.create_subscription(
            variant_msg_cls,
            variant_topic,
            self._variant_cb,
            10,
            callback_group=self._cbg,
        )
        self.get_logger().info(f"Subscribed to: {variant_topic}")

        # Inference loop timer
        self._timer = self.create_timer(self.step_sec, self._inference_tick, callback_group=self._cbg)

        self.get_logger().info(f"VariantPolicyBridge ready at {self.fps} Hz")

    def _variant_cb(self, msg) -> None:
        """Callback for VariantsList messages."""
        try:
            batch = dec_variant_list(msg, self.device)
            self._variant_buffer = batch
        except Exception as e:
            self.get_logger().error(f"Failed to decode VariantsList: {e!r}")

    def _inference_tick(self) -> None:
        """Main inference loop."""
        batch = self._variant_buffer
        if not batch:
            self.get_logger().warning("No variants in buffer, skipping inference")
            return

        # self.get_logger().info("Sampled batch for inference:")
        # for k in batch:
        #     if isinstance(batch[k], torch.Tensor):
        #         self.get_logger().info(f"Sampled {k}: shape {batch[k].shape}, dtype {batch[k].dtype}")
        #     else:
        #         self.get_logger().info(f"Sampled {k}: {batch[k]}")

        with torch.inference_mode():
            action = self.policy.select_action(batch)
        
        action = self.postprocessor(action)
        
        self._publish_actions(action)

    def _publish_actions(self, action: Any) -> None:
        """Encode and publish action vectors."""
        # Convert action to numpy
        if torch.is_tensor(action):
            action_np = action.detach().cpu().numpy()
        else:
            action_np = np.asarray(action)
        
        # Flatten if needed
        action_np = action_np.ravel()
        
        # Publish each action spec
        start_idx = 0
        for spec in self._action_specs:
            spec_len = len(spec.names) if spec.names else 0
            if spec_len == 0:
                continue
            
            end_idx = start_idx + spec_len
            if end_idx > len(action_np):
                self.get_logger().error(
                    f"Action vector too short for {spec.key}: "
                    f"need {spec_len}, have {len(action_np) - start_idx}"
                )
                break
            
            spec_action = action_np[start_idx:end_idx]
            
            msg = encode_value(
                ros_type=spec.ros_type,
                names=spec.names,
                action_vec=spec_action,
                clamp=getattr(spec, "clamp", None),
            )
            
            pub = self._act_pubs[spec.topic]
            pub.publish(msg)
            
            start_idx = end_idx


def main():
    """Main entry point."""
    try:
        rclpy.init()
        node = VariantPolicyBridge()
        executor = SingleThreadedExecutor()
        executor.add_node(node)
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()


if __name__ == "__main__":
    main()
