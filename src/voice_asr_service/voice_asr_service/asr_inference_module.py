#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASRInferenceModule - ASR推理模块

职责边界：管理 sherpa-onnx 识别器的生命周期，执行解码

支持流式识别(OnlineRecognizer)和非流式识别(OfflineRecognizer)
支持热词增强
支持自动检测模型类型
"""

import os
import threading
import numpy as np
from enum import Enum
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass
from pathlib import Path


class ASRState(Enum):
    IDLE = "idle"
    READY = "ready"
    RECOGNIZING = "recognizing"
    ERROR = "error"


class ModelType(Enum):
    STREAMING = "streaming"
    OFFLINE = "offline"
    AUTO = "auto"


@dataclass
class ASRResult:
    text: str
    is_final: bool
    confidence: float = 1.0
    tokens: Optional[List[str]] = None
    timestamps: Optional[List[float]] = None
    start_time: Optional[float] = None
    duration: Optional[float] = None


class ASRInferenceModule:
    """
    ASR推理模块
    
    管理 sherpa-onnx 识别器的生命周期，执行解码
    支持流式识别(OnlineRecognizer)和非流式识别(OfflineRecognizer)
    支持热词增强
    支持自动检测模型类型
    """
    
    def __init__(self):
        self.state = ASRState.IDLE
        self._recognizer: Optional[Any] = None
        self._stream: Optional[Any] = None
        self._model_type: ModelType = ModelType.OFFLINE
        self._hotwords: Dict[str, float] = {}
        self._sample_rate: int = 16000
        
        self._active_stream: Optional[Any] = None
        self._pending_stream: Optional[Any] = None
        
        self._model_path: Optional[str] = None
        self._language: str = "zh"
        self._last_error: Optional[str] = None
        
        self._lock = threading.Lock()
    
    def initialize(
        self,
        model_path: str,
        tokens_path: Optional[str] = None,
        provider: str = "cpu",
        language: str = "zh",
        model_type: str = "auto"
    ) -> bool:
        """
        初始化 ASR 模型
        
        Args:
            model_path: 模型文件路径或目录
            tokens_path: tokens 文件路径（可选，默认在模型目录查找）
            provider: 推理后端 (cpu/cuda/coreml)
            language: 语言 (zh/en)
            model_type: 模型类型 (streaming/offline/auto)
            
        Returns:
            bool: 是否初始化成功
        """
        try:
            import sherpa_onnx
            
            self._recognizer = None
            self._active_stream = None
            self._pending_stream = None
            self._last_error = None
            self._model_path = model_path
            self._language = language
            
            if model_type == "streaming":
                self._model_type = ModelType.STREAMING
            elif model_type == "offline":
                self._model_type = ModelType.OFFLINE
            else:
                self._model_type = self._detect_model_type(model_path)
            
            if self._model_type == ModelType.STREAMING:
                recognizer = self._create_streaming_recognizer(
                    model_path, tokens_path, provider
                )
                sample_rate = recognizer.config.feat_config.sampling_rate
            else:
                recognizer = self._create_offline_recognizer(
                    model_path, tokens_path, provider
                )
                sample_rate = 16000

            if recognizer is None:
                raise RuntimeError(
                    "Recognizer factory returned None. Check model_path, tokens_path, and provider settings."
                )

            self._recognizer = recognizer
            self._sample_rate = sample_rate
            self.state = ASRState.READY
            return True
            
        except ImportError:
            self._last_error = "sherpa_onnx not installed. Install with: pip install sherpa-onnx"
            self.state = ASRState.ERROR
            raise RuntimeError(self._last_error)
        except Exception as e:
            self._recognizer = None
            self._active_stream = None
            self._pending_stream = None
            self._last_error = str(e)
            self.state = ASRState.ERROR
            raise RuntimeError(f"Failed to initialize ASR: {e}")
    
    def _detect_model_type(self, model_path: str) -> ModelType:
        """
        自动检测模型类型
        
        流式模型通常包含: encoder-xxx.onnx, decoder-xxx.onnx, joiner-xxx.onnx
        非流式模型通常只有一个: model.onnx 或 model.int8.onnx
        """
        path = Path(model_path)
        
        if path.is_file():
            model_dir = path.parent
        else:
            model_dir = path
        
        has_encoder = list(model_dir.glob("encoder*.onnx"))
        has_decoder = list(model_dir.glob("decoder*.onnx"))
        has_joiner = list(model_dir.glob("joiner*.onnx"))
        
        if has_encoder and has_decoder and has_joiner:
            return ModelType.STREAMING
        
        streaming_keywords = ['streaming', 'online', 'transducer', 'conformer']
        model_name = model_dir.name.lower()
        for keyword in streaming_keywords:
            if keyword in model_name:
                return ModelType.STREAMING
        
        return ModelType.OFFLINE
    
    def _create_streaming_recognizer(
        self,
        model_path: str,
        tokens_path: Optional[str],
        provider: str
    ) -> Any:
        """
        创建流式识别器 (OnlineRecognizer)
        使用 sherpa-onnx 工厂方法
        """
        import sherpa_onnx
        
        path = Path(model_path)
        if path.is_file():
            model_dir = path.parent
            model_file = str(path)
        else:
            model_dir = path
            model_file = None
        
        if tokens_path is None:
            tokens_path = str(model_dir / "tokens.txt")
        
        encoder = list(model_dir.glob("encoder*.onnx"))
        decoder = list(model_dir.glob("decoder*.onnx"))
        joiner = list(model_dir.glob("joiner*.onnx"))
        
        if encoder and decoder and joiner:
            return sherpa_onnx.OnlineRecognizer.from_transducer(
                encoder=str(encoder[0]),
                decoder=str(decoder[0]),
                joiner=str(joiner[0]),
                tokens=tokens_path,
                num_threads=4,
                provider=provider,
            )
        
        paraformer = list(model_dir.glob("*.onnx"))
        if paraformer:
            return sherpa_onnx.OnlineRecognizer.from_paraformer(
                model=str(paraformer[0]),
                tokens=tokens_path,
                num_threads=4,
                provider=provider,
            )
        
        raise RuntimeError(f"Cannot create streaming recognizer from {model_path}")
    
    def _create_offline_recognizer(
        self,
        model_path: str,
        tokens_path: Optional[str],
        provider: str
    ) -> Any:
        """
        创建非流式识别器 (OfflineRecognizer)
        使用 sherpa-onnx 工厂方法
        """
        import sherpa_onnx
        
        path = Path(model_path)
        if path.is_file():
            model_dir = path.parent
            model_file = str(path)
        else:
            model_dir = path
            model_file = None
        
        if tokens_path is None:
            tokens_path = str(model_dir / "tokens.txt")
        
        onnx_files = list(model_dir.glob("*.onnx"))
        if not onnx_files:
            raise FileNotFoundError(f"No .onnx files found in {model_dir}")
        
        model_file = str(onnx_files[0])
        
        return sherpa_onnx.OfflineRecognizer.from_paraformer(
            paraformer=model_file,
            tokens=tokens_path,
            num_threads=4,
            provider=provider,
            decoding_method="greedy_search",
        )
    
    def create_stream(self) -> Any:
        """创建新的识别流"""
        if self._recognizer is None:
            raise RuntimeError("ASR not initialized")
        return self._recognizer.create_stream()
    
    def _require_recognizer(self, operation: str) -> None:
        """Ensure the underlying recognizer exists before using it."""
        if self._recognizer is not None:
            return

        detail = f": {self._last_error}" if self._last_error else ""
        raise RuntimeError(
            f"Cannot run {operation} because the ASR recognizer is not initialized{detail}"
        )
    
    def is_streaming(self) -> bool:
        """检查是否为流式模型"""
        return self._model_type == ModelType.STREAMING
    
    def start_streaming(self) -> bool:
        """开始流式识别"""
        with self._lock:
            if self.state != ASRState.READY:
                return False
            
            if self._model_type != ModelType.STREAMING:
                raise RuntimeError(
                    "start_streaming() is only for streaming models. "
                    "Current model is offline. Use recognize_file() instead."
                )
            
            self._active_stream = self.create_stream()
            self.state = ASRState.RECOGNIZING
            return True
    
    def accept_waveform(self, audio_data: np.ndarray) -> Optional[ASRResult]:
        """
        输入音频数据并获取识别结果
        
        Args:
            audio_data: 音频数据 (float32, 16kHz)
            
        Returns:
            ASRResult: 识别结果（如果有）
        """
        with self._lock:
            if self._active_stream is None:
                return None
            
            self._recognizer.accept_waveform(self._active_stream, audio_data)
            
            if self._recognizer.is_ready(self._active_stream):
                self._recognizer.decode(self._active_stream)
            
            text = self._active_stream.result.text
            if text:
                return ASRResult(
                    text=text,
                    is_final=False,
                    confidence=1.0
                )
            
            return None
    
    def get_partial_result(self) -> ASRResult:
        """获取当前中间结果"""
        with self._lock:
            if self._active_stream is None:
                return ASRResult(text="", is_final=False)
            
            text = self._active_stream.result.text
            return ASRResult(
                text=text,
                is_final=False,
                confidence=1.0
            )
    
    def get_final_result(self) -> ASRResult:
        """获取最终结果并结束识别"""
        with self._lock:
            if self._active_stream is None:
                return ASRResult(text="", is_final=True)
            
            self._recognizer.decode(self._active_stream)
            text = self._active_stream.result.text
            
            result = ASRResult(
                text=text,
                is_final=True,
                confidence=1.0
            )
            
            self._active_stream = None
            self.state = ASRState.READY
            
            return result
    
    def end_streaming(self) -> ASRResult:
        """结束流式识别并返回最终结果"""
        return self.get_final_result()
    
    def recognize_file(
        self,
        audio_data: np.ndarray,
        enable_vad: bool = True,
        vad_module: Optional[Any] = None
    ) -> List[ASRResult]:
        """
        识别音频文件
        
        支持流式和非流式模型:
        - 流式模型: 使用 OnlineRecognizer 的流式接口
        - 非流式模型: 使用 OfflineRecognizer 的批量接口
        
        Args:
            audio_data: 完整音频数据
            enable_vad: 是否启用 VAD 分段
            vad_module: VAD 模块实例
            
        Returns:
            List[ASRResult]: 识别结果列表
        """
        self._require_recognizer("file recognition")

        results = []
        
        if self._model_type == ModelType.STREAMING:
            results = self._recognize_streaming(audio_data, enable_vad, vad_module)
        else:
            results = self._recognize_offline(audio_data, enable_vad, vad_module)
        
        return results

    def _create_file_result(
        self,
        text: str,
        start_sample: int,
        end_sample: int
    ) -> ASRResult:
        """构造带显式时间边界的文件识别结果"""
        start_time = start_sample / self._sample_rate
        duration = max(end_sample - start_sample, 0) / self._sample_rate
        return ASRResult(
            text=text,
            is_final=True,
            confidence=1.0,
            timestamps=[start_time],
            start_time=start_time,
            duration=duration,
        )
    
    def _recognize_streaming(
        self,
        audio_data: np.ndarray,
        enable_vad: bool,
        vad_module: Optional[Any]
    ) -> List[ASRResult]:
        """使用流式模型识别"""
        self._require_recognizer("streaming file recognition")

        results = []
        
        if not enable_vad or vad_module is None:
            stream = self.create_stream()
            self._recognizer.accept_waveform(stream, audio_data)
            self._recognizer.decode(stream)
            text = stream.result.text
            if text:
                results.append(self._create_file_result(
                    text=text,
                    start_sample=0,
                    end_sample=len(audio_data),
                ))
        else:
            segments = vad_module.segment_audio(audio_data)
            for segment in segments:
                start_sample, end_sample, audio_segment = segment
                stream = self.create_stream()
                self._recognizer.accept_waveform(stream, audio_segment)
                self._recognizer.decode(stream)
                text = stream.result.text
                if text:
                    results.append(self._create_file_result(
                        text=text,
                        start_sample=start_sample,
                        end_sample=end_sample,
                    ))
        
        return results
    
    def _recognize_offline(
        self,
        audio_data: np.ndarray,
        enable_vad: bool,
        vad_module: Optional[Any]
    ) -> List[ASRResult]:
        """使用非流式模型识别"""
        self._require_recognizer("offline file recognition")

        results = []
        
        if not enable_vad or vad_module is None:
            stream = self._recognizer.create_stream()
            stream.accept_waveform(self._sample_rate, audio_data)
            self._recognizer.decode_stream(stream)
            result = stream.result
            if result.text:
                results.append(self._create_file_result(
                    text=result.text,
                    start_sample=0,
                    end_sample=len(audio_data),
                ))
        else:
            segments = vad_module.segment_audio(audio_data)
            for segment in segments:
                start_sample, end_sample, audio_segment = segment
                stream = self._recognizer.create_stream()
                stream.accept_waveform(self._sample_rate, audio_segment)
                self._recognizer.decode_stream(stream)
                result = stream.result
                if result.text:
                    results.append(self._create_file_result(
                        text=result.text,
                        start_sample=start_sample,
                        end_sample=end_sample,
                    ))
        
        return results
    
    def set_hotwords(self, hotwords: Dict[str, float]):
        """
        设置热词
        
        Args:
            hotwords: 热词字典 {word: boost_score}
        """
        self._hotwords = hotwords
        
        if self._recognizer and hasattr(self._recognizer, 'set_hotwords'):
            self._recognizer.set_hotwords(hotwords)
    
    def add_hotword(self, word: str, boost: float = 1.5):
        """添加单个热词"""
        self._hotwords[word] = boost
        self.set_hotwords(self._hotwords)
    
    def remove_hotword(self, word: str):
        """移除热词"""
        if word in self._hotwords:
            del self._hotwords[word]
            self.set_hotwords(self._hotwords)
    
    def clear_hotwords(self):
        """清除所有热词"""
        self._hotwords.clear()
        if self._recognizer and hasattr(self._recognizer, 'set_hotwords'):
            self._recognizer.set_hotwords({})
    
    def reset(self):
        """重置识别状态"""
        with self._lock:
            self._active_stream = None
            self._pending_stream = None
            self.state = ASRState.READY
    
    def cleanup(self):
        """清理资源"""
        with self._lock:
            self._active_stream = None
            self._pending_stream = None
            self._recognizer = None
            self._config = None
            self.state = ASRState.IDLE
    
    @property
    def sample_rate(self) -> int:
        return self._sample_rate
    
    @property
    def is_ready(self) -> bool:
        return self.state in [ASRState.READY, ASRState.RECOGNIZING]