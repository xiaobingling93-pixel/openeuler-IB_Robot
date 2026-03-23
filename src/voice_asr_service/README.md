# voice_asr_service 节点介绍

## 1. 节点作用

`voice_asr_service` 是一个 ROS 2 语音识别节点，负责把麦克风音频或音频文件转换成文本，并将识别结果发布给下游节点。

它在整个系统里的定位是“语音输入入口”，主要负责：

- 采集音频
- 检测语音起止
- 调用 sherpa-onnx 完成语音识别
- 通过 topic / service 向下游暴露文本结果

入口可执行程序定义在 `src/voice_asr_service/setup.py`，节点实现位于 `src/voice_asr_service/voice_asr_service/voice_asr_node.py`。

---

## 2. 启动方式

### 2.1 推荐方式：通过 `robot_config` 统一注入参数

推荐通过 `robot_config` 的统一启动入口启用 ASR，这也是当前主配置入口。

```bash
source .shrc_local
ros2 launch robot_config robot.launch.py \
  robot_config:=so101_single_arm \
  use_sim:=true \
  with_inference:=false
```

对应的参数应写在机器人 YAML 的 `robot.voice_asr` 段中，例如：

```yaml
robot:
  voice_asr:
    enabled: true
    active_mode: manual
    language: zh
    model_path: src/voice_asr_service/model/sherpa-onnx-paraformer-zh-2023-09-14/model.int8.onnx
    tokens_path: src/voice_asr_service/model/sherpa-onnx-paraformer-zh-2023-09-14/tokens.txt
    provider: cpu
    model_type: auto
    max_recording_duration: 10.0
    vad_sensitivity: 0.5
    publish_partial: true
    sample_rate: 16000
    chunk_size: 512
    buffer_seconds: 5.0
    output_topic: /voice_command
    device_index: -1
```

### 2.2 调试方式：直接运行节点

如果只想验证 ASR 节点本身，建议直接运行节点并显式传参：

```bash
source .shrc_local
ros2 run voice_asr_service voice_asr_node --ros-args \
  -p model_path:=src/voice_asr_service/model/sherpa-onnx-paraformer-zh-2023-09-14/model.int8.onnx \
  -p tokens_path:=src/voice_asr_service/model/sherpa-onnx-paraformer-zh-2023-09-14/tokens.txt
```

### 2.3 关于 `voice_asr.launch.py`

`src/voice_asr_service/launch/voice_asr.launch.py` 现在只保留为调试入口提示，不再承载业务参数注入。

也就是说：

- 它会启动 `voice_asr_node`
- 但不会替你传 `model_path`、`tokens_path` 等业务参数
- 主配置入口已经收敛到 `robot_config`

---

## 3. 整体架构

`VoiceASRNode` 本身不直接处理所有细节，而是组合了几个内部模块：

- `AudioCaptureModule`：负责麦克风采集
- `FileInputModule`：负责音频文件读取与重采样
- `VADModule`：负责语音活动检测
- `ASRInferenceModule`：负责 sherpa-onnx 模型初始化和解码
- `StateMachine`：负责节点状态管理

整体链路可以理解为：

```text
麦克风/音频文件
    -> 音频预处理
    -> VAD 检测
    -> ASR 推理
    -> 发布识别文本/状态/置信度
```

---

## 4. 节点支持的输入方式

### 4.1 麦克风实时输入

实时输入由 `AudioCaptureModule` 提供，支持持续采集、暂停、恢复、停止，以及 pre-roll 缓冲。

实时模式下，节点会：

1. 从音频队列读取音频块
2. 用 VAD 判断当前是否有人声
3. 当检测到讲话时启动识别流
4. 在讲话过程中持续产生 partial result
5. 在静音或超时时输出 final result

### 4.2 音频文件输入

音频文件输入由 `FileInputModule` 完成，支持：

- WAV

文件识别支持两种调用方式：

- 通过服务 `~/recognize_file` 同步识别
- 通过话题 `/voice_file_input` 异步提交文件路径

`RecognizeFile` 当前请求体包含：

- `file_path`
- `enable_vad`

识别语言由节点启动参数 `language` 决定，当前版本不支持按单次请求覆盖。

---

## 5. ASR 初始化与就绪状态

节点启动时会读取以下关键参数并尝试初始化模型：

- `model_path`
- `tokens_path`
- `provider`
- `model_type`

当前模型选择逻辑：

- 如果目录内存在 `encoder/decoder/joiner`，认为是流式模型
- 如果是单个 paraformer onnx，认为是离线模型

离线识别和流式识别统一封装在 `src/voice_asr_service/voice_asr_service/asr_inference_module.py`。

### 5.1 当前失败处理行为

最近代码已经补上了初始化失败保护：

- 如果 `model_path` 为空，节点会记录 warning
- 如果模型初始化失败，节点会记录 error 并保存失败原因
- 节点不会因为后续 `recognize_file` 请求而直接崩溃
- 当 ASR 尚未 ready 时，服务请求会返回失败响应，异步文件输入会记录错误日志并拒绝处理

这意味着 `VoiceASRNode initialized` 并不等于“模型已经可用”，还需要结合是否出现 `ASR model loaded: ...` 日志一起判断。

---

## 6. 当前已接入的模型类型

当前 `voice_asr_service` 的代码并没有把 sherpa-onnx 官网列出的所有模型家族都接入完成，而是以以下两类为主：

- 流式 transducer / paraformer
- 离线 paraformer

如果后续要扩展到 Whisper、SenseVoice、WeNet CTC、NeMo CTC 等模型，需要继续在 `ASRInferenceModule` 中补充对应的工厂方法和模型路径解析逻辑。

---

## 7. VAD 的作用

`VADModule` 用于判断“什么时候开始说话、什么时候结束说话”。

它的作用不是识别文字，而是给 ASR 提供分段边界，避免：

- 一直解码无效静音
- 句子切分不合理
- 前后音频被截断

当前实现包含两层策略：

- 优先尝试 `silero-vad`
- 失败时回退到基于能量的 VAD

---

## 8. 状态机设计

节点内部维护了一个简单状态机，主要状态包括：

- `IDLE`：空闲
- `LISTENING`：监听中
- `RECOGNIZING`：识别中
- `HOLD`：保留态
- `ERROR`：错误态

当前主要工作流是：

```text
IDLE -> LISTENING -> RECOGNIZING -> LISTENING/IDLE
```

其中：

- 手动模式下，一般由服务或控制话题触发进入 `LISTENING`
- 识别到讲话后进入 `RECOGNIZING`
- 讲话结束后回到 `LISTENING` 或 `IDLE`

---

## 9. ROS 接口说明

### 9.1 发布话题

当前节点会发布以下话题：

| 话题 | 类型 | 作用 |
|---|---|---|
| `output_topic` 参数指定的话题，默认 `/voice_command` | `std_msgs/String` | 最终识别文本 |
| `/voice_partial` | `std_msgs/String` | 中间识别结果 |
| `/voice_status` | `std_msgs/String` | 当前状态 |
| `/voice_confidence` | `std_msgs/Float32` | 识别置信度 |
| `/voice_file_progress` | `std_msgs/Float32` | 文件处理进度 |

### 9.2 订阅话题

| 话题 | 类型 | 作用 |
|---|---|---|
| `/voice_control` | `std_msgs/String` | 控制开始/停止监听 |
| `/voice_file_input` | `std_msgs/String` | 输入待识别音频文件路径 |

### 9.3 服务

| 服务 | 类型 | 作用 |
|---|---|---|
| `~/start_recognition` | `std_srvs/Empty` | 开始一次识别 |
| `~/stop_recognition` | `std_srvs/Empty` | 停止当前识别 |
| `~/set_hotwords` | `ibrobot_msgs/srv/SetHotwords` | 设置热词 |
| `~/recognize_file` | `ibrobot_msgs/srv/RecognizeFile` | 同步识别音频文件 |

服务定义位于：

- `src/ibrobot_msgs/srv/RecognizeFile.srv`
- `src/ibrobot_msgs/srv/SetHotwords.srv`

---

## 10. 关键参数

这些参数定义在 `voice_asr_node.py` 内部的 `declare_parameter()` 中，由 `robot_config` 或命令行运行时注入。

| 参数名 | 默认值 | 说明 |
|---|---|---|
| `active_mode` | `manual` | 激活模式 |
| `language` | `zh` | 默认识别语言 |
| `model_path` | `""` | 模型路径 |
| `tokens_path` | `""` | tokens 文件路径 |
| `provider` | `cpu` | 推理后端 |
| `model_type` | `auto` | 自动判断流式/离线模型 |
| `max_recording_duration` | `10.0` | 最大录音时长 |
| `vad_sensitivity` | `0.5` | VAD 灵敏度 |
| `publish_partial` | `true` | 是否发布中间结果 |
| `output_topic` | `/voice_command` | 最终文本发布话题 |
| `sample_rate` | `16000` | 采样率 |
| `chunk_size` | `512` | 音频块大小 |
| `buffer_seconds` | `5.0` | 音频缓冲时长 |
| `device_index` | `-1` | 输入设备编号 |

---

## 11. 一个典型工作流程

以“手动启动麦克风识别”为例：

1. 外部调用 `~/start_recognition`
2. 节点初始化音频设备并开始采集
3. 状态切换到 `LISTENING`
4. VAD 检测到讲话
5. 节点启动 ASR 流并不断接收音频块
6. 如果开启 `publish_partial`，则持续发布 `/voice_partial`
7. 当检测到讲话结束或达到超时时间
8. 节点输出最终文本到 `output_topic`
9. 同时发布置信度到 `/voice_confidence`
