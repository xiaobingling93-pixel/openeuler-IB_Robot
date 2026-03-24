#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FileInputModule - 音频文件输入模块

职责边界：处理音频文件的读取、解码和格式转换，为 ASR 提供标准输入

支持格式：WAV、MP3、FLAC、OGG 等
"""

import os
import numpy as np
from enum import Enum
from typing import Optional, Tuple, List
from dataclasses import dataclass


class FileState(Enum):
    IDLE = "idle"
    LOADING = "loading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class FileError(Enum):
    FILE_NOT_FOUND = "file_not_found"
    UNSUPPORTED_FORMAT = "unsupported_format"
    DECODE_ERROR = "decode_error"
    CORRUPTED_FILE = "corrupted_file"


@dataclass
class FileResult:
    success: bool
    error_code: Optional[FileError] = None
    error_message: str = ""
    audio_data: Optional[np.ndarray] = None
    sample_rate: int = 16000
    duration: float = 0.0


class FileInputModule:
    """
    音频文件输入模块
    
    处理音频文件的读取、解码和格式转换
    支持 WAV、MP3、FLAC、OGG 等常见格式
    """
    
    SUPPORTED_FORMATS = {'.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac'}
    TARGET_SAMPLE_RATE = 16000
    
    def __init__(self):
        self.state = FileState.IDLE
        self._current_file: Optional[str] = None
        self._progress_callback = None
    
    def set_progress_callback(self, callback):
        self._progress_callback = callback
    
    def load_file(self, file_path: str) -> FileResult:
        """
        加载音频文件并转换为标准格式
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            FileResult: 包含音频数据或错误信息的结果对象
        """
        self.state = FileState.LOADING
        self._current_file = file_path
        
        if not os.path.exists(file_path):
            self.state = FileState.ERROR
            return FileResult(
                success=False,
                error_code=FileError.FILE_NOT_FOUND,
                error_message=f"File not found: {file_path}"
            )
        
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.SUPPORTED_FORMATS:
            self.state = FileState.ERROR
            return FileResult(
                success=False,
                error_code=FileError.UNSUPPORTED_FORMAT,
                error_message=f"Unsupported format: {ext}. Supported: {self.SUPPORTED_FORMATS}"
            )
        
        try:
            audio_data, sample_rate = self._decode_file(file_path, ext)
            
            if sample_rate != self.TARGET_SAMPLE_RATE:
                audio_data = self._resample(audio_data, sample_rate, self.TARGET_SAMPLE_RATE)
            
            duration = len(audio_data) / self.TARGET_SAMPLE_RATE
            
            self.state = FileState.COMPLETED
            return FileResult(
                success=True,
                audio_data=audio_data,
                sample_rate=self.TARGET_SAMPLE_RATE,
                duration=duration
            )
            
        except Exception as e:
            self.state = FileState.ERROR
            return FileResult(
                success=False,
                error_code=FileError.DECODE_ERROR,
                error_message=f"Failed to decode file: {str(e)}"
            )
    
    def load_file_chunked(self, file_path: str, chunk_size: int = 16000) -> Tuple[bool, str, List[np.ndarray]]:
        """
        分块加载音频文件（用于大文件处理）
        
        Args:
            file_path: 音频文件路径
            chunk_size: 每块采样数
            
        Yields:
            Tuple[progress, audio_chunk]: 进度和音频块
        """
        self.state = FileState.LOADING
        self._current_file = file_path
        
        if not os.path.exists(file_path):
            self.state = FileState.ERROR
            return False, "File not found", []
        
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.SUPPORTED_FORMATS:
            self.state = FileState.ERROR
            return False, f"Unsupported format: {ext}", []
        
        try:
            result = self.load_file(file_path)
            if not result.success:
                return False, result.error_message, []
            
            audio_data = result.audio_data
            total_samples = len(audio_data)
            chunks = []
            
            for i in range(0, total_samples, chunk_size):
                chunk = audio_data[i:i + chunk_size]
                chunks.append(chunk)
                
                if self._progress_callback:
                    progress = min(1.0, (i + chunk_size) / total_samples)
                    self._progress_callback(progress)
            
            self.state = FileState.COMPLETED
            return True, "", chunks
            
        except Exception as e:
            self.state = FileState.ERROR
            return False, str(e), []
    
    def _decode_file(self, file_path: str, ext: str) -> Tuple[np.ndarray, int]:
        """解码音频文件"""
        if ext in ['.wav', '.flac']:
            return self._decode_soundfile(file_path)
        else:
            return self._decode_pydub(file_path)
    
    def _decode_soundfile(self, file_path: str) -> Tuple[np.ndarray, int]:
        """使用 soundfile 解码 WAV/FLAC"""
        try:
            import soundfile as sf
            audio_data, sample_rate = sf.read(file_path, dtype='float32')
            
            if audio_data.ndim > 1:
                audio_data = audio_data[:, 0]
            
            return audio_data, sample_rate
            
        except ImportError:
            return self._decode_pydub(file_path)
    
    def _decode_pydub(self, file_path: str) -> Tuple[np.ndarray, int]:
        """使用 pydub + ffmpeg 解码各种格式"""
        try:
            from pydub import AudioSegment
            
            audio = AudioSegment.from_file(file_path)
            audio = audio.set_frame_rate(self.TARGET_SAMPLE_RATE)
            audio = audio.set_channels(1)
            
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            samples = samples / (2 ** 15)
            
            return samples, self.TARGET_SAMPLE_RATE
            
        except ImportError:
            raise RuntimeError(
                "pydub not installed. Install with: pip install pydub\n"
                "Also ensure ffmpeg is installed on your system."
            )
    
    def _resample(self, audio_data: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """重采样音频"""
        if orig_sr == target_sr:
            return audio_data
        
        try:
            import librosa
            return librosa.resample(audio_data, orig_sr=orig_sr, target_sr=target_sr)
        except ImportError:
            try:
                from scipy import signal
                num_samples = int(len(audio_data) * target_sr / orig_sr)
                return signal.resample(audio_data, num_samples)
            except ImportError:
                ratio = target_sr / orig_sr
                num_samples = int(len(audio_data) * ratio)
                indices = np.linspace(0, len(audio_data) - 1, num_samples)
                return np.interp(indices, np.arange(len(audio_data)), audio_data).astype(np.float32)
    
    def get_file_info(self, file_path: str) -> dict:
        """获取音频文件信息"""
        if not os.path.exists(file_path):
            return {"error": "File not found"}
        
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext in ['.wav', '.flac']:
                import soundfile as sf
                info = sf.info(file_path)
                return {
                    "format": ext,
                    "duration": info.duration,
                    "sample_rate": info.samplerate,
                    "channels": info.channels,
                    "frames": info.frames
                }
            else:
                from pydub import AudioSegment
                audio = AudioSegment.from_file(file_path)
                return {
                    "format": ext,
                    "duration": audio.duration_seconds,
                    "sample_rate": audio.frame_rate,
                    "channels": audio.channels,
                    "frames": int(audio.frame_count())
                }
        except Exception as e:
            return {"error": str(e)}
    
    def reset(self):
        self.state = FileState.IDLE
        self._current_file = None