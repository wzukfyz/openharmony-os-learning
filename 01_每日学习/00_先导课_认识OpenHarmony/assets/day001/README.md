# Day001 配图源文件

课程正文维护于上层 Markdown。配图在本目录保留可编辑 HTML 源和 PNG 导出物：

| 源文件 | 课程使用图 | 教学任务 |
|---|---|---|
| `objects.html` | `objects.png` | 对照开源项目、操作系统平台、内核与具体产品 |
| `scope.html` | `scope.png` | 区分 OpenHarmony、Linux 内核、Linux 发行版和商业 HarmonyOS，并呈现本课范围 |

源文件为自包含 HTML/SVG/CSS，可离线打开；课程构建只读取 Markdown 引用的 PNG，不执行这些 HTML 源文件。修改插图请编辑源文件并重新导出图片，不手工修改 `_site/`。

图标为自绘；线条处理采用 Rough.js（MIT，Copyright © 2019 Preet Shihn）和 sketchify.js（MIT，animated-sketch-diagram contributors），许可说明写在 HTML 源注释中。内嵌 Kalam、Patrick Hand 与按字符子集化的 LXGW WenKai Screen 字体遵循 SIL Open Font License 1.1，保留字体版权与许可元数据；许可正文见同级 Day002 配图目录的 [`OFL.txt`](../day002/OFL.txt)。

导出和验收不要求安装指定绘图工具。使用任意本地浏览器或静态绘图程序都可重建；确认标签准确、关系表达清楚、字体易读、输出在窄屏缩放后仍可辨认。课程中实际使用的 PNG 均应在当前网页构建器限制内。
