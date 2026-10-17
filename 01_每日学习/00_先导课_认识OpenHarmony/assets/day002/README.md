# Day002 配图源文件

课程正文维护于上层 Markdown。本目录只维护配图源和导出图：

| 源文件 | 课程使用的导出图 | 说明 |
|---|---|---|
| `layers.html` | `layers.png` | 四层职责静图，无调用箭头 |
| `read-display.html` | `read-display.gif` | 读取请求/结果往返，显示职责流程；`read-display.png` 为静态备份 |
| `device-change.html` | `device-change.png` | 存储更换前后对照 |

HTML 自包含 SVG、字体子集和手绘准备脚本，可单独离线打开；动画由 CSS 驱动。PNG/GIF 是课程嵌入物，课程构建不执行这些 HTML 源文件。修改配图应编辑对应 HTML 再导出，不手工修改 `_site/`。

采用 [animated-sketch-diagram](https://github.com/OLDyade/animated-sketch-diagram) 的风格和配方，图标为自绘。内嵌 Rough.js（MIT，Copyright © 2019 Preet Shihn）及 sketchify.js（MIT，animated-sketch-diagram contributors）；许可声明保留在各 HTML 注释中。内嵌 Kalam、Patrick Hand 及按字符子集化的 LXGW WenKai Screen 字体为 SIL OFL 1.1，保留字体原有版权与许可元数据。字体许可正文见 `OFL.txt`。

导出要求：1200px 逻辑画布、2倍截图；动态图3秒、25fps、75帧、无限循环。Windows 可使用现有 Chrome，给 skill 导出器设置 `CHROME_PATH`；ffmpeg 本次由 Python 包 `imageio-ffmpeg` 提供二进制，可通过 `python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"` 查询路径。原导出器的 Windows 文件 URL 兼容性未修改，本次通过项目外临时 Playwright 录制工具导出。

本次已检查实际导出图、GIF间隔帧、普通阅读版及独立目录离线分享版；桌面/窄屏与主题切换由 Chrome 自动化检查。人工试学及不同 Markdown 阅读器表现仍待确认。
