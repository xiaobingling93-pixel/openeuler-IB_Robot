# camera_alignment

基于 ArUco 标记的相机对齐工具。它通过检测当前画面中的多个 ArUco 角点，计算相对参考帧的平均像素误差，并提供实时颜色反馈和“虚影对齐”界面，帮助你把摄像头恢复到训练或基准采集时的位置。

## 适用场景

- 推理前需要确认相机视角没有漂移
- 摄像头支架刚拆装过，担心视角偏了
- 需要快速对齐本机 USB 摄像头或视频设备视角

## 工具能力

当前工具保持原始迁移工具的输入方式：

- `--cameras_index_or_path`：直接从本机摄像头或视频设备读取

工具支持如下交互：

- `s`：保存当前画面中的 ArUco 角点作为参考基准
- `v`：进入虚影对齐模式
- `q`：退出

默认会生成两个文件：

- `camera_reference_multi.json`：保存参考角点
- `reference_img.png`：保存参考图像

## 运行前提

推荐在 IB_Robot 仓根目录执行：

```bash
cd /path/to/IB_Robot
source .shrc_local
```

如果 `dataset_tools` 尚未编译，先执行：

```bash
cd /path/to/IB_Robot
source .shrc_local
colcon build --merge-install --symlink-install --packages-select dataset_tools
```

工具依赖：

- `python3-opencv`
- OpenCV ArUco 模块 `cv2.aruco`
- `python3-numpy`

如果使用窗口界面，还需要有可用显示环境，例如：

- 物理桌面环境
- 开发容器中的 X11 转发
- VNC / 远程桌面

## ROS 2 中的使用方式

在 ROS 2 环境中直接读取本机视频设备：

```bash
cd /path/to/IB_Robot
source .shrc_local

ros2 run dataset_tools camera_alignment \
  --cameras_index_or_path /dev/video0 \
  --reference-path /tmp/camera_reference_multi.json \
  --reference-image-path /tmp/reference_img.png
```

如果设备号是整数，也可以写成：

```bash
ros2 run dataset_tools camera_alignment --cameras_index_or_path 0
```

## 使用步骤

### 1. 保存参考基准

把摄像头调到你认可的“黄金位置”，确保画面里能看到 ArUco 码，然后按：

```text
s
```

### 2. 观察误差状态

主界面会持续显示误差状态：

- 绿色：误差小于 3 像素
- 红色：误差大于等于 3 像素
- 黄色：还没有保存参考基准，或当前丢失了 marker

### 3. 进入虚影模式

按：

```text
v
```

退出虚影模式按：

```text
q
```

## 参数说明

| 参数 | 说明 |
| --- | --- |
| `--cameras_index_or_path` | 本机摄像头索引或设备路径，如 `0`、`/dev/video0` |
| `--reference-path` | 参考角点 JSON 输出路径 |
| `--reference-image-path` | 参考图输出路径 |

## 常见问题

### 1. 提示 OpenCV 没有 aruco

说明当前 OpenCV 构建不包含 `cv2.aruco`。需要安装带 ArUco 模块的 OpenCV 版本。

### 2. 看得到图像，但一直检测不到 marker

请检查：

- 使用的是否为 `DICT_4X4_50` 字典族的 ArUco 码
- marker 是否过小、反光、模糊或被遮挡
- 画面中是否只露出了一部分 marker

### 3. 保存了参考，但下次运行找不到参考文件

建议在调用时显式传入：

- `--reference-path`
- `--reference-image-path`
