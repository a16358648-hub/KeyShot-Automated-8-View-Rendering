# KeyShot Automated 8-View Rendering

**KeyShot 一键八视图渲染 · v2.4**

[中文介绍](#中文介绍) · [English](#english) · [Release / 下载](https://github.com/a16358648-hub/KeyShot-Automated-8-View-Rendering/releases/tag/v2.4)

## 中文介绍

面向产品设计与模型展示的 KeyShot Python 脚本。运行一次即可自动切换相机、按当前可见模型居中取景，并依次输出八张正交视图，减少重复调整相机和逐张渲染的操作。

脚本在 KeyShot 内运行，无需另外安装 Python 库。

### 主要功能

- **一键八视图**：前、后、左、右、顶、底、上方 45°、下方 45°。两个斜视角同样使用正交投影。
- **只对可见模型取景**：隐藏模型、隐藏父组及未激活模型集不参与取景计算，避免远处隐藏模型让主体变小。
- **兼容 CAD/NURBS 几何结构**：能够识别被 KeyShot 暴露为分组叶节点的曲面实体，修复误报“没有可见零件”的问题。
- **按模型组命名文件夹**：在场景文件旁建立“当前可见模型组名称＋八视图”，例如 `模型A八视图`；多个组同时可见时使用 `模型A+模型B八视图`。
- **输出位置明确**：无法确认场景完整路径时，弹出文件夹选择框。已有同名图片时，在输出目录内新建 `run_日期_时间` 子目录保留旧图。
- **默认 PNG，沿用当前场景渲染尺寸**：保持场景画幅比例，并检查手动尺寸，避免输出被拉伸。可在脚本顶部修改格式及画面占比。运行信息只显示在脚本控制台，不生成 `.log` 文件。

### 安装与使用

1. 从 Release 的 **Assets** 下载 `KeyShot-Automated-8-View-Rendering-v2.4.zip` 并解压。ZIP 内包含脚本和本说明。
2. 将 `KeyShot Automated 8-View Rendering.py` 放入 KeyShot 资源文件夹的 `Scripts` 目录。Windows 上 KeyShot 11 的常见位置是用户文档中的 `KeyShot 11/Scripts`；以实际资源目录为准。
3. 在 KeyShot 中打开并保存场景，显示需要渲染的模型，隐藏其他模型，并设置好材质、环境和渲染质量。
4. 打开 KeyShot 的脚本窗口，选择 **KeyShot Automated 8-View Rendering**，点击“运行”。如果列表没有刷新，关闭再打开脚本窗口。
5. 渲染结束后，根据提示中的保存位置查看八张图片。

也可下载 Release 中的独立 `.py` 文件；其内容与 ZIP 内脚本相同，只是下载文件名使用连字符。

### 输出示例

场景文件为 `Product.bip`，当前可见模型组为 `模型A`：

```text
Product.bip
模型A八视图/
  Product_01_front.png
  Product_02_back.png
  Product_03_left.png
  Product_04_right.png
  Product_05_top.png
  Product_06_bottom.png
  Product_07_up45.png
  Product_08_down45.png
```

文件夹名称来自可见模型组；图片文件名前缀默认来自场景文件名。

### 常用设置

编辑脚本顶部的配置后保存，再运行：

| 设置 | 默认值 | 用途 |
| --- | --- | --- |
| `RENDER_WIDTH_OVERRIDE` / `RENDER_HEIGHT_OVERRIDE` | `0` / `0` | 自动读取场景渲染尺寸；手动指定时，宽高比必须与场景画幅一致 |
| `FRAME_FILL_RATIO` | `0.85` | 取景包围范围的画面占比；建议 `0.80`～`0.90` |
| `OUTPUT_EXT` | `png` | 输出格式；支持 PNG、JPEG、TIFF、EXR、PSD |
| `OUTPUT_DIR_OVERRIDE` | 空 | 可填写绝对路径，直接指定最终输出目录 |
| `FILE_PREFIX_OVERRIDE` | 空 | 可指定图片文件名前缀 |

若要固定输出为某个尺寸，请先在 KeyShot 的“项目 > 图像”中把场景画幅设置为相同比例，再设置输出尺寸。自动模式下，若保存的渲染尺寸与场景画幅不一致，会保留输出宽度并调整高度。

脚本在渲染期间锁定比例和分辨率，完成或报错后恢复原来的锁定状态。脚本使用当前渲染质量设置，以本地逐张方式渲染；会关闭队列、网络、后台渲染和区域裁切。它创建或复用工作相机，结束后切回原相机，不移动模型、不更改模型显隐，也不保存或覆盖场景文件。

### 适用环境与说明

- 需要支持 Python 脚本的 KeyShot；已在 **Windows / KeyShot 11.1 Pro** 中验证，其他版本尚未验证。
- 基于几何包围盒取景，斜视图或不规则模型可能留有额外空白，可调整 `FRAME_FILL_RATIO`。
- 前、后、左、右等方向采用 KeyShot 标准视图；需要特定产品朝向时，请先调整模型方向。
- v2.4 修复部分场景的大图输出拉伸：默认沿用场景尺寸，校验宽高比，并在渲染期间稳定画幅。仍不生成日志文件。

## English

**KeyShot Automated 8-View Rendering** is a Python script for product design and model presentation. Run it once to switch camera views, center and frame the currently visible geometry, and render eight orthographic images in sequence.

The script runs inside KeyShot and requires no additional Python packages.

### Features

- **Eight views in one run:** front, back, left, right, top, bottom, upper 45°, and lower 45°. Both angled views are also orthographic.
- **Framing based on visible geometry:** hidden models, hidden parent groups, and inactive model sets are excluded, so distant hidden geometry does not shrink the subject.
- **CAD/NURBS support:** recognizes geometric entities that KeyShot exposes as group leaf nodes, avoiding a false “no visible parts” error.
- **Folders named after visible model groups:** creates `<visible model group name>八视图` beside the scene file. `八视图` means “eight views.” Multiple visible groups are joined with `+`.
- **Explicit output location:** asks you to choose a folder if the scene path is unavailable. When image names already exist, it creates a `run_YYYYMMDD_HHMMSS` subfolder to preserve previous images.
- **PNG using the scene’s render dimensions by default:** preserves the scene aspect ratio and validates manual dimensions to prevent stretching. Format and framing ratio remain configurable. Progress is printed to the scripting console; no `.log` file is created.

### Installation and use

1. Download `KeyShot-Automated-8-View-Rendering-v2.4.zip` from the Release **Assets** and extract it. The ZIP includes the script and this bilingual guide.
2. Copy `KeyShot Automated 8-View Rendering.py` into the `Scripts` directory of your KeyShot resource folder. For KeyShot 11 on Windows, this is commonly `KeyShot 11/Scripts` inside your Documents folder; use your configured resource location.
3. Open and save your scene in KeyShot. Show the models you want to render, hide the others, and configure materials, lighting, and render quality.
4. Open KeyShot’s scripting window, select **KeyShot Automated 8-View Rendering**, and click **Run**. Reopen the scripting window if the list needs refreshing.
5. When rendering finishes, open the folder shown in the completion message.

The standalone `.py` asset has identical contents to the script in the ZIP, with a hyphenated download filename. Script dialogs and console messages are currently in Chinese.

### Configuration and output

Edit and save the settings near the top of the script:

| Setting | Default | Purpose |
| --- | --- | --- |
| `RENDER_WIDTH_OVERRIDE` / `RENDER_HEIGHT_OVERRIDE` | `0` / `0` | Read the scene’s render dimensions automatically; manual dimensions must match the scene aspect ratio |
| `FRAME_FILL_RATIO` | `0.85` | Fraction of the frame occupied by the geometry bounds; `0.80`–`0.90` is a useful range |
| `OUTPUT_EXT` | `png` | Output format: PNG, JPEG, TIFF, EXR, or PSD |
| `OUTPUT_DIR_OVERRIDE` | Empty | An absolute path overriding the final output folder |
| `FILE_PREFIX_OVERRIDE` | Empty | A custom image filename prefix |

For `Product.bip` with a visible group named `ModelA`, the folder is `ModelA八视图`, and filenames run from `Product_01_front.png` through `Product_08_down45.png`, as shown in the example above. Folder names come from visible model groups; image prefixes default to the scene filename.

To use fixed output dimensions, first set the same aspect ratio in KeyShot’s **Project > Image** panel. In automatic mode, if the saved render dimensions disagree with the scene aspect ratio, the script preserves the output width and adjusts the height.

Aspect and resolution locks are enabled during rendering and restored on completion or failure. Rendering is local and sequential, using the current quality settings. Queue, network, background rendering, and region cropping are disabled for this run. The script creates or reuses a work camera and switches back to the original camera afterward. It does not move models, change their visibility, or save or overwrite the scene file.

### Compatibility and notes

- Requires KeyShot with Python scripting support. Verified on **Windows with KeyShot 11.1 Pro**; other versions have not been verified.
- Bounding-box framing may leave extra space around irregular objects or angled views. Adjust `FRAME_FILL_RATIO` as needed.
- View directions follow KeyShot’s standard views. Orient the model before running if a specific product-facing direction is required.
- v2.4 fixes stretched full-resolution output in affected scenes by using scene dimensions, validating aspect ratios, and keeping the image frame stable during rendering. No log files are generated.
