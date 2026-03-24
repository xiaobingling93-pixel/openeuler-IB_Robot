#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VADModule - 语音活动检测模块

职责边界：检测语音起点和终点，过滤无效音频

两级检测策略：
- 第一级：silero-vad 检测人声活动（粗筛）
- 第二级：基于能量的自适应阈值（精确定位端点）
"""

import numpy as np
from enum import Enum
from typing import Optional, List, Tuple
from dataclasses import dataclass


class VADState(Enum):
    SILENCE = "silence"
    STARTING = "starting"
    SPEAKING = "speaking"
    ENDING = "ending"


@dataclass
class VADConfig:
    sample_rate: int = 16000
    frame_size: int = 512
    pre_roll_ms: float = 300.0
    post_roll_ms: float = 500.0
    speech_threshold: float = 0.5
    silence_threshold: float = 0.3
    min_speech_duration: float = 0.3
    min_silence_duration: float = 0.5
    energy_threshold: float = 0.01
    adaptive_threshold: bool = True


@dataclass
class VADResult:
    is_speech: bool
    state: VADState
    confidence: float = 0.0
    energy: float = 0.0


class VADModule:
    """
    语音活动检测模块
    
    检测语音起点和终点，过滤无效音频
    支持两级检测策略和自适应阈值
    """
    
    def __init__(self, config: Optional[VADConfig] = None):
        self.config = config or VADConfig()
        self.state = VADState.SILENCE
        
        self._model: Optional[Any] = None
        self._model_loaded = False
        
        self._noise_floor: float = 0.0
        self._noise_samples: int = 0
        self._calibration_frames: int = int(2.0 * self.config.sample_rate / self.config.frame_size)
        
        self._speech_start_sample: int = 0
        self._speech_frames: int = 0
        self._silence_frames: int = 0
        self._total_samples: int = 0
        
        self._pre_roll_buffer: List[np.ndarray] = []
        self._pre_roll_samples: int = 0
        self._max_pre_roll_samples: int = int(
            self.config.sample_rate * self.config.pre_roll_ms / 1000
        )
        
        self._post_roll_frames: int = 0
        self._max_post_roll_frames: int = int(
            self.config.sample_rate * self.config.post_roll_ms / 1000 / self.config.frame_size
        )
    
    def initialize(self) -> bool:
        """初始化 VAD 模型"""
        try:
            import torch
            
            model_path = self._download_silero_model()
            self._model, _ = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                source='local',
                force_reload=False,
                onnx=False,
                trust_repo=True
            )
            self._model.eval()
            self._model_loaded = True
            return True
            
        except Exception as e:
            print(f"Warning: Failed to load silero-vad: {e}")
            print("Falling back to energy-based VAD")
            self._model_loaded = False
            return True
    
    def _download_silero_model(self) -> str:
        """下载 silero 模型（如果需要）"""
        import torch
        import os
        
        torch.hub.set_dir(os.path.expanduser('~/.cache/torch/hub'))
        return ""
    
    def process(self, audio_frame: np.ndarray) -> VADResult:
        """
        处理音频帧，返回 VAD 结果
        
        Args:
            audio_frame: 音频帧 (float32)
            
        Returns:
            VADResult: VAD 检测结果
        """
        if len(audio_frame) == 0:
            return VADResult(is_speech=False, state=self.state)
        
        energy = self._compute_energy(audio_frame)
        confidence = self._get_speech_probability(audio_frame)
        
        self._update_noise_floor(energy)
        
        if self.config.adaptive_threshold:
            threshold = self._get_adaptive_threshold()
        else:
            threshold = self.config.speech_threshold
        
        result = self._update_state(confidence, energy, threshold)
        
        self._update_pre_roll(audio_frame)
        self._total_samples += len(audio_frame)
        
        return result
    
    def _compute_energy(self, audio_frame: np.ndarray) -> float:
        """计算音频帧能量"""
        return float(np.sqrt(np.mean(audio_frame ** 2)))
    
    def _get_speech_probability(self, audio_frame: np.ndarray) -> float:
        """获取语音概率"""
        if not self._model_loaded or self._model is None:
            energy = self._compute_energy(audio_frame)
            return min(1.0, energy / max(self._noise_floor * 2, 0.01))
        
        try:
            import torch
            
            if len(audio_frame) < 512:
                audio_frame = np.pad(audio_frame, (0, 512 - len(audio_frame)))
            
            audio_tensor = torch.from_numpy(audio_frame).unsqueeze(0)
            
            with torch.no_grad():
                confidence = self._model(audio_tensor, self.config.sample_rate).item()
            
            return confidence
            
        except Exception:
            energy = self._compute_energy(audio_frame)
            return min(1.0, energy / max(self._noise_floor * 2, 0.01))
    
    def _update_noise_floor(self, energy: float):
        """更新噪声底估计"""
        if self._noise_samples < self._calibration_frames:
            if self.state == VADState.SILENCE:
                alpha = 0.9 if self._noise_samples > 0 else 0.0
                self._noise_floor = alpha * self._noise_floor + (1 - alpha) * energy
                self._noise_samples += 1
    
    def _get_adaptive_threshold(self) -> float:
        """获取自适应阈值"""
        base_threshold = self.config.speech_threshold
        
        if self._noise_floor > 0:
            snr_factor = min(2.0, max(0.5, self._noise_floor / 0.01))
            return base_threshold * snr_factor
        
        return base_threshold
    
    def _update_state(self, confidence: float, energy: float, threshold: float) -> VADResult:
        """更新 VAD 状态"""
        is_speech = confidence > threshold
        
        if self.state == VADState.SILENCE:
            if is_speech:
                self.state = VADState.STARTING
                self._speech_start_sample = self._total_samples
                self._speech_frames = 1
                self._silence_frames = 0
            
        elif self.state == VADState.STARTING:
            if is_speech:
                self._speech_frames += 1
                speech_duration = self._speech_frames * self.config.frame_size / self.config.sample_rate
                
                if speech_duration >= self.config.min_speech_duration:
                    self.state = VADState.SPEAKING
            else:
                self.state = VADState.SILENCE
                self._speech_frames = 0
        
        elif self.state == VADState.SPEAKING:
            if is_speech:
                self._speech_frames += 1
                self._silence_frames = 0
            else:
                self._silence_frames += 1
                silence_duration = self._silence_frames * self.config.frame_size / self.config.sample_rate
                
                if silence_duration >= self.config.min_silence_duration:
                    self.state = VADState.ENDING
                    self._post_roll_frames = 0
        
        elif self.state == VADState.ENDING:
            self._post_roll_frames += 1
            
            if is_speech:
                self.state = VADState.SPEAKING
                self._silence_frames = 0
            elif self._post_roll_frames >= self._max_post_roll_frames:
                self.state = VADState.SILENCE
                self._speech_frames = 0
                self._silence_frames = 0
        
        return VADResult(
            is_speech=is_speech,
            state=self.state,
            confidence=confidence,
            energy=energy
        )
    
    def _update_pre_roll(self, audio_frame: np.ndarray):
        """更新预录缓冲区"""
        self._pre_roll_buffer.append(audio_frame.copy())
        self._pre_roll_samples += len(audio_frame)
        
        while self._pre_roll_samples > self._max_pre_roll_samples and self._pre_roll_buffer:
            removed = self._pre_roll_buffer.pop(0)
            self._pre_roll_samples -= len(removed)
    
    def get_pre_roll_audio(self) -> np.ndarray:
        """获取预录音频"""
        if not self._pre_roll_buffer:
            return np.array([], dtype=np.float32)
        return np.concatenate(self._pre_roll_buffer)
    
    def is_speech_started(self) -> bool:
        """检测是否语音开始"""
        return self.state in [VADState.STARTING, VADState.SPEAKING, VADState.ENDING]
    
    def is_speech_ended(self) -> bool:
        """检测是否语音结束"""
        return self.state == VADState.SILENCE and self._speech_frames == 0
    
    def get_speech_start_time(self) -> float:
        """获取语音开始时间"""
        return self._speech_start_sample / self.config.sample_rate
    
    def segment_audio(
        self,
        audio_data: np.ndarray,
        min_segment_duration: float = 0.5
    ) -> List[Tuple[int, int, np.ndarray]]:
        """
        对音频进行分段
        
        Args:
            audio_data: 完整音频数据
            min_segment_duration: 最小分段时长
            
        Returns:
            List of (start_sample, end_sample, audio_segment)
        """
        segments = []
        current_start = None
        current_audio = []
        
        frame_size = self.config.frame_size
        n_frames = len(audio_data) // frame_size
        
        for i in range(n_frames):
            start = i * frame_size
            end = start + frame_size
            frame = audio_data[start:end]
            
            result = self.process(frame)
            
            if result.state == VADState.SPEAKING:
                if current_start is None:
                    current_start = start
                    pre_roll = self.get_pre_roll_audio()
                    if len(pre_roll) > 0:
                        current_audio.append(pre_roll)
                current_audio.append(frame)
            
            elif result.state == VADState.SILENCE and current_start is not None:
                if current_audio:
                    segment_audio = np.concatenate(current_audio)
                    duration = len(segment_audio) / self.config.sample_rate
                    
                    if duration >= min_segment_duration:
                        segments.append((
                            current_start,
                            current_start + len(segment_audio),
                            segment_audio
                        ))
                
                current_start = None
                current_audio = []
                self.reset()
        
        if current_start is not None and current_audio:
            segment_audio = np.concatenate(current_audio)
            duration = len(segment_audio) / self.config.sample_rate
            
            if duration >= min_segment_duration:
                segments.append((
                    current_start,
                    current_start + len(segment_audio),
                    segment_audio
                ))
        
        return segments
    
    def reset(self):
        """重置 VAD 状态"""
        self.state = VADState.SILENCE
        self._speech_start_sample = 0
        self._speech_frames = 0
        self._silence_frames = 0
        self._total_samples = 0
        self._post_roll_frames = 0
        self._pre_roll_buffer = []
        self._pre_roll_samples = 0
    
    def set_sensitivity(self, sensitivity: float):
        """
        设置 VAD 灵敏度
        
        Args:
            sensitivity: 灵敏度 (0.0-1.0)，越高越灵敏
        """
        self.config.speech_threshold = 0.7 - sensitivity * 0.4
        self.config.silence_threshold = self.config.speech_threshold - 0.1