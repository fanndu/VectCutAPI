# VectCut 视频草稿配置化生成器

## 📖 概述

这是一个可配置的视频草稿生成系统，通过修改 `draft_config.json` 配置文件即可生成新的草稿，无需修改代码。

## 🚀 快速开始

### 1. 生成草稿

```bash
python generate_draft_from_config.py
```

### 2. 修改配置

编辑 `draft_config.json` 文件，修改你想要的内容，然后重新运行生成脚本。

## 📝 配置文件说明

### 基本设置

```json
{
  "canvas": {
    "width": 1080,      // 画布宽度
    "height": 1920      // 画布高度
  }
}
```

### 📹 替换视频片段

修改 `videos` 部分：

```json
"videos": {
  "folder_path": "/path/to/your/video/folder",  // 视频文件夹路径
  "duration_per_video": 4,                       // 每个视频时长（秒）
  "files": [                                      // 视频文件列表（按顺序）
    "video1.mp4",
    "video2.mp4",
    "video3.mp4"
  ]
}
```

**注意**：
- 视频会按顺序排列在时间线上
- 时间自动计算：第1个从0s开始，第2个从4s开始，以此类推

### 🎤 替换配音文件

修改 `voiceovers` 部分：

```json
"voiceovers": {
  "folder_path": "/path/to/your/audio/folder",  // 配音文件夹路径
  "files": [                                      // 配音文件列表（按顺序）
    "voiceover1.mp3",
    "voiceover2.mp3",
    "voiceover3.mp3"
  ]
}
```

**注意**：
- 配音会自动放在对应视频的第一帧
- 配音1对应视频1，配音2对应视频2，以此类推

### 📝 替换字幕文本

修改 `subtitles` 部分：

```json
"subtitles": {
  "font": "Coolvetica",           // 字体名称
  "font_size": 15,                // 字号
  "font_color": "#FFFFFF",        // 字体颜色
  "background_color": "#000000",  // 背景颜色
  "background_alpha": 0.7,        // 背景透明度 (0.0-1.0)
  "items": [
    {"text": "你的字幕1", "start": 0, "end": 2},
    {"text": "你的字幕2", "start": 4, "end": 6}
  ]
}
```

**注意**：
- `start` 和 `end` 是视频时间线上的时间点
- 字幕会自动放在屏幕底部 (y=-0.8)

### 🔢 替换序号标题

修改 `number_titles` 部分：

```json
"number_titles": {
  "position_x_pixel": -911,     // X坐标（像素值）
  "items": [
    {"text": "1.", "y_pixel": 767, "color": "#fff800"},
    {"text": "2.", "y_pixel": 405, "color": "#2b9eff"}
  ]
}
```

**注意**：
- `position_x_pixel`：所有序号的X坐标（相同）
- `y_pixel`：每个序号的Y坐标（不同）
- 序号会在整个视频时长显示

### 📄 替换描述标题

修改 `description_titles` 部分：

```json
"description_titles": {
  "position_x_pixel": -500,     // X坐标（像素值）
  "order": "reversed",            // 顺序："reversed"=反转，"normal"=正常
  "items": [
    {"text": "描述文本1", "y_pixel": -991, "start": 0, "end": 4},
    {"text": "描述文本2", "y_pixel": -646, "start": 4, "end": 8}
  ]
}
```

**注意**：
- `order`：控制Y坐标的对应顺序
  - `"reversed"`：第1个文本使用第6个Y坐标
  - `"normal"`：第1个文本使用第1个Y坐标

## 🎨 样式调整

### 修改字体样式

**字幕字体**：
```json
"subtitles": {
  "font": "你的字体名称",    // 改成你想要的字体
  "font_size": 20,          // 修改字号
  "font_color": "#FF0000"    // 修改颜色（红色）
}
```

**描述标题样式**：
```json
"description_titles": {
  "font": "Exo",            // 字体
  "font_size": 9,            // 字号
  "font_color": "#FFFFFF",   // 文字颜色（白色）
  "border_color": "#000000", // 描边颜色（黑色）
  "border_width": 50.0       // 描边宽度
}
```

### 修改位置

**X坐标调整**：
- 序号：修改 `number_titles.position_x_pixel`
- 描述：修改 `description_titles.position_x_pixel`

**Y坐标调整**：
- 修改每个项目的 `y_pixel` 值
- 范围：大约-1000到800（-1000在最上面，800在最下面）

## 📊 坐标系统说明

- **X坐标**（水平）：
  - 负数：左侧（-500比-800更靠右）
  - 0：中心
  - 正数：右侧

- **Y坐标**（垂直）：
  - 正数：上方
  - 负数：下方
  - 0：中心

- **相对坐标转换**：
  - 系统会自动将像素坐标转换为相对坐标
  - 公式：`relative = pixel / canvas_size`

## 🔄 工作流程

1. **修改配置文件**
   ```bash
   vim draft_config.json  # 或使用其他编辑器
   ```

2. **生成草稿**
   ```bash
   python generate_draft_from_config.py
   ```

3. **在剪映中查看**
   - 草稿ID会显示在输出中
   - 在剪映中打开对应的草稿ID

## 📁 文件结构

```
VectCutAPI/
├── draft_config.json              # 配置文件（主要修改这个）
├── generate_draft_from_config.py  # 生成脚本
└── README_CONFIG.md               # 本说明文档
```

## 💡 常见使用场景

### 场景1：更换视频

只需修改 `videos.files` 和 `voiceovers.files`，其他保持不变。

### 场景2：修改字幕文本

只需修改 `subtitles.items` 中的 `text` 字段。

### 场景3：调整位置

修改 `position_x_pixel` 或 `y_pixel` 值。

### 场景4：增加更多片段

1. 在 `videos.files` 中添加更多视频文件
2. 在 `voiceovers.files` 中添加对应配音
3. 在 `subtitles.items` 中添加对应字幕
4. 在 `description_titles.items` 中添加对应描述

## ⚠️ 注意事项

1. **数量对应**：视频、配音、字幕、描述的数量应该一致
2. **文件路径**：确保所有文件路径正确
3. **时间协调**：字幕和描述的时间应该在对应视频的时间范围内
4. **坐标范围**：Y坐标建议在-1000到800之间
5. **API服务**：确保API服务器运行在 http://localhost:9001

## 🛠️ 故障排除

### 草稿无法在剪映中打开

- 检查视频/音频文件路径是否正确
- 确保文件存在且可访问

### 文本位置不对

- 检查 `position_x_pixel` 和 `y_pixel` 值
- 尝试调整数值（X：-500比-800更靠右）

### 字体不显示

- 确保字体在 `pyJianYingDraft/metadata/font_meta.py` 中已定义
- 检查字体名称拼写

## 📞 技术支持

如有问题，请检查：
1. API服务器是否运行：`curl http://localhost:9001`
2. 配置文件格式是否正确（JSON语法）
3. 文件路径是否正确
