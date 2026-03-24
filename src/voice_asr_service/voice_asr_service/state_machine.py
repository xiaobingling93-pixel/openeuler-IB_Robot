#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StateMachine - 状态管理模块

全局状态管理，支持多种激活模式
"""

from enum import Enum
from typing import Optional, Callable
from dataclasses import dataclass


class NodeState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    RECOGNIZING = "recognizing"
    HOLD = "hold"
    ERROR = "error"


class ActiveMode(Enum):
    MANUAL = "manual"
    CONTINUOUS = "continuous"
    WAKE_WORD = "wake_word"


@dataclass
class StateTransition:
    from_state: NodeState
    to_state: NodeState
    trigger: str
    timestamp: float


class StateMachine:
    """
    状态管理模块
    
    管理 VoiceASRNode 的全局状态
    支持多种激活模式
    """
    
    VALID_TRANSITIONS = {
        NodeState.IDLE: [NodeState.LISTENING, NodeState.ERROR],
        NodeState.LISTENING: [NodeState.RECOGNIZING, NodeState.IDLE, NodeState.ERROR],
        NodeState.RECOGNIZING: [NodeState.LISTENING, NodeState.IDLE, NodeState.HOLD, NodeState.ERROR],
        NodeState.HOLD: [NodeState.IDLE, NodeState.LISTENING, NodeState.ERROR],
        NodeState.ERROR: [NodeState.IDLE],
    }
    
    def __init__(self):
        self._state = NodeState.IDLE
        self._mode = ActiveMode.MANUAL
        self._previous_state: Optional[NodeState] = None
        self._transition_history: list = []
        self._state_callbacks: dict = {}
        self._error_message: str = ""
    
    @property
    def state(self) -> NodeState:
        return self._state
    
    @property
    def mode(self) -> ActiveMode:
        return self._mode
    
    @property
    def error_message(self) -> str:
        return self._error_message
    
    def set_mode(self, mode: ActiveMode):
        """设置激活模式"""
        self._mode = mode
    
    def set_mode_str(self, mode_str: str):
        """通过字符串设置激活模式"""
        mode_map = {
            "manual": ActiveMode.MANUAL,
            "continuous": ActiveMode.CONTINUOUS,
            "wake_word": ActiveMode.WAKE_WORD,
        }
        if mode_str in mode_map:
            self._mode = mode_map[mode_str]
    
    def can_transition_to(self, new_state: NodeState) -> bool:
        """检查是否可以转换到目标状态"""
        return new_state in self.VALID_TRANSITIONS.get(self._state, [])
    
    def transition(self, new_state: NodeState, trigger: str = "") -> bool:
        """
        状态转换
        
        Args:
            new_state: 目标状态
            trigger: 触发原因
            
        Returns:
            bool: 是否转换成功
        """
        if not self.can_transition_to(new_state):
            return False
        
        old_state = self._state
        self._previous_state = old_state
        self._state = new_state
        
        import time
        transition = StateTransition(
            from_state=old_state,
            to_state=new_state,
            trigger=trigger,
            timestamp=time.time()
        )
        self._transition_history.append(transition)
        
        if len(self._transition_history) > 100:
            self._transition_history = self._transition_history[-100:]
        
        self._notify_callbacks(old_state, new_state)
        
        return True
    
    def force_transition(self, new_state: NodeState, trigger: str = ""):
        """强制状态转换（忽略有效性检查）"""
        old_state = self._state
        self._previous_state = old_state
        self._state = new_state
        
        import time
        transition = StateTransition(
            from_state=old_state,
            to_state=new_state,
            trigger=trigger,
            timestamp=time.time()
        )
        self._transition_history.append(transition)
        
        self._notify_callbacks(old_state, new_state)
    
    def set_error(self, message: str):
        """设置错误状态"""
        self._error_message = message
        self.transition(NodeState.ERROR, f"error: {message}")
    
    def clear_error(self):
        """清除错误状态"""
        self._error_message = ""
        if self._state == NodeState.ERROR:
            self.transition(NodeState.IDLE, "error_cleared")
    
    def reset(self):
        """重置状态机"""
        self._state = NodeState.IDLE
        self._previous_state = None
        self._error_message = ""
    
    def register_callback(self, state: NodeState, callback: Callable[[NodeState, NodeState], None]):
        """注册状态变化回调"""
        if state not in self._state_callbacks:
            self._state_callbacks[state] = []
        self._state_callbacks[state].append(callback)
    
    def _notify_callbacks(self, old_state: NodeState, new_state: NodeState):
        """通知状态变化回调"""
        if new_state in self._state_callbacks:
            for callback in self._state_callbacks[new_state]:
                try:
                    callback(old_state, new_state)
                except Exception as e:
                    pass
    
    def is_idle(self) -> bool:
        return self._state == NodeState.IDLE
    
    def is_listening(self) -> bool:
        return self._state == NodeState.LISTENING
    
    def is_recognizing(self) -> bool:
        return self._state == NodeState.RECOGNIZING
    
    def is_hold(self) -> bool:
        return self._state == NodeState.HOLD
    
    def is_error(self) -> bool:
        return self._state == NodeState.ERROR
    
    def get_state_string(self) -> str:
        return self._state.value