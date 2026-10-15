# Day003：OpenHarmony 为什么有多种内核？

> 阶段：先导课｜前置：[Day002：OpenHarmony 不只有内核](Day002_OpenHarmony不只有内核.md)
>
> 阅读：预计 5～10 分钟（待试学）｜微练习：约 2 分钟｜扩展实验：无
>
> 环境：无需环境；本课无运行实验
>
> 源码基线：不涉及源码解读

## 今天要解决的问题

既然内核负责基础资源管理，OpenHarmony 为什么不只选一种内核？本课不比较谁“最好”，而是理解不同设备和系统配置会带来不同选择。

## 学习目标

读完后，能解释本课程为何聚焦标准系统 Linux，并判断“所有 OpenHarmony 设备都必须使用 Linux”是否正确。

## 核心解释

设备的处理能力、内存资源和产品功能并不相同。面向资源受限设备的系统与面向更丰富应用能力的标准系统，可能需要不同的内核形态。OpenHarmony 官方内核资料列出 LiteOS-M、LiteOS-A 和 Linux 等路线，并说明内核选择与系统形态相关。具体某个产品采用何种内核，要看其目标版本、产品配置和官方适配资料，不能只凭名称推断。

可以把内核看成提供资源管理机制的一套基础设施：选择时要考虑目标设备与软件需求，而不是把内核排成简单的好坏名次。本课程的目标是理解 Linux 内核通用机制，并走向 OpenHarmony 标准系统内核阅读与集成，因此从 Linux 路线开始。选择 Linux 是课程范围的决定，不表示 LiteOS 不重要，也不要求学习者先学完 LiteOS 才能入门。

官方文档会随项目版本变化。某一份文档列出的分支、产品或适配关系，只能作为该文档对应状态的说明；涉及真实设备时，应再查目标版本资料。本课不要求记忆内核版本号或设备清单。

官方内核教程用三类入口组织学习资料：LiteOS-M 对应轻量系统，适合资源较少的设备；LiteOS-A 对应小型系统，介绍进程、虚拟内存等机制；标准系统 Linux 则面向较丰富的应用和资源管理需求。这里是在解释教程的组织方式，并非所有产品的硬性选型表。

## 简图或例子

```text
不同设备与产品需求
        ↓ 选择适合的系统形态和产品配置
LiteOS-M / LiteOS-A / Linux 等内核路线

本课程目标：标准系统 Linux 内核机制与集成
```

这是路线示意，不是完整产品兼容矩阵，也不表示所有产品只能选择其中某一条。

## 今天动手

判断“所有 OpenHarmony 设备都使用 Linux”，并写一句理由。再补充一句：“我学习 Linux，是因为本课程 ______。”

## 自检

1. 所有 OpenHarmony 设备是否必须使用 Linux？
2. 选择 Linux 与本课程目标有什么关系？

<details>
<summary>参考答案要点</summary>

1. 不能这样概括。官方资料说明存在 LiteOS 与 Linux 等不同路线，选择与设备和系统形态有关。
2. 本课程聚焦 OpenHarmony 标准系统 Linux 内核机制及其集成；这是学习目标的选择，不代表其它内核没有价值，也不代表必须先学完 LiteOS。

</details>

## 一句话总结

多内核路线反映了设备和产品需求的差异；我们学习 Linux，是为了对准标准系统内核目标。下一课从一次文件读取场景看内核怎样参与。

## 官方依据与延伸阅读

- [OpenHarmony 内核文档目录](https://raw.githubusercontent.com/openharmony/docs/master/zh-cn/device-dev/kernel/Readme-CN.md)：列出 LiteOS-M、LiteOS-A 与标准系统 Linux 的文档入口；目录本身不等于所有产品适配情况。
- [OpenHarmony 内核子系统说明](https://raw.githubusercontent.com/openharmony/docs/master/zh-cn/readme/内核子系统.md)：介绍系统形态与内核路线的关系；其中分支信息可能随版本变化。
- [标准系统内核概述](https://raw.githubusercontent.com/openharmony/docs/master/zh-cn/device-dev/kernel/kernel-standard-overview.md)：说明标准系统采用 Linux 内核路线；具体目标版本仍需核验。

**导航：** 上一课：[Day002：OpenHarmony 不只有内核](Day002_OpenHarmony不只有内核.md)｜下一课：[Day004：一次普通操作，内核做了什么](Day004_一次普通操作内核做了什么.md)
