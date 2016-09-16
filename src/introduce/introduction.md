---
title: Zephyr OS 基础篇： 系统简介
date: 2016-07-20 20:35:05
categories: ["Zephyr OS"]
tags: [Zephyr]
---
本文主要介绍 Zephyr OS 的基本知识，带你进入 Zephyr 的世界，主要内容：

- [火热的物联网](#火热的物联网)
- [Zephyr OS 简介](#zephyr-os-简介)
- [Zephyr OS 架构](#zephyr-os-架构)
- [Zephyr OS 内核](#zephyr-os-内核)
- [Zephyr OS 的特征](#zephyr-os-的特征)
- [Zephyr OS 源码结构](#zephyr-os-源码结构)
- [学习资料](#学习资料)

<!--more-->
# 火热的物联网

话说，人类再也无法阻挡人工智能和物联网的发展趋势了，google, intel, cisco, TI, IBM, 苹果, 微软, 三星, 华为, 阿里, 百度... 大型科技公司都瞄准了物联网，准备分享这上万亿美元的大蛋糕。甚至连日本的软银也盯上物联网了(前几天的新闻，软银卖掉了阿里巴巴等若干公司的股份，以 320 亿美元的价格把 ARM 公司给收购了，OMG)。

物联网的架构主要分为三层：
- 感知层：采集周围环境数据的嵌入式设备
- 网络层：用于传输感知层采集的数据的网络，比如因特网、3G/4G网络，甚至将来的5G网络等
- 应用层：处理数据，即数据分析、处理

Zephyr OS 就是运行在感知层的嵌入式设备之上的操作系统。

# Zephyr OS 简介

Zephyr 是一个用于物联网的开源操作系统，受到 Linux 基金会支持（参考 [这里](http://www.cinic.org.cn/site951/hwcj/2016-02-18/812129.shtml)），在今年二月份刚发布 1.0 版本，目前开发到 1.4 版本。Zephyr 的目标非常远大，即一统物联网操作系统。

Zephyr 目前还处于初期阶段，项目开发非常活跃，代码托管在 Linux 基金会自己搭建的 Girret 服务器上，而不是在 Github 上。Girret 相比 Github 的一个好处是它能很方便地进行代码检查，但熟悉 Girret 的人不多，因此增加了学习成本。也正是由于它还是在初期阶段，所以我对它充满了期望。这是机遇呀！！

# Zephyr OS 架构
图 1 从系统的角度展示了 Zephyr OS 的架构：
- 最下层是硬件设备。
- 在硬件设备之上是 Zephyr 的内核，包括 nanokernle 和 microkernel 两种内核。
- 内核之上是设备驱动。由于物联网设备具有低功耗要求，Zephyr 单独将电源管理抽取出来了。
- 设备驱动之上是设备管理器、网络层、应用层、C 库和三方库。

<center>![](/images/zephyr/introduce/introduction/1.png)</center>

<center>图 1. Zephyr OS 架构</center>

图 2 从网络互联的角度展示了 Zephyr OS 的架构：
- 最底层是网络接口层(具体而言包括物理层和数据链路层)，支持 IEEE 802.15.4、Bluetooth 4.0(低功耗蓝牙)、WiFi、NFC(近距离无线通信)和 3GPP(3G网络)。
- 网络接口层之上是网络层，包括 6LoWPAN 适配层、IPv4/IPv6、Thread 协议。
- 网络层之上是传输层，支持 TCP 和 UDP。
- 传输层之上是应用层，包含各种适用于物联网的应用层协议。

<center>![](/images/zephyr/introduce/introduction/2.png)</center>

<center>图 2. Zephyr OS 网络架构</center>

# Zephyr OS 内核

Zephyr 的中文翻译是“和风；西风；轻薄织物”，由此可以看出 zephyr 是一个轻量级的操作系统。事实上，它提供了两种内核：微内核 microkernel 和超微内核 nanokernel，用户可以在编译时通过配置文件配置使用哪种内核：同时使用微内核和超微内核，或者只使用超微内核(参考图 1)。

超微内核具有内核的一系列基础特征，是一个高性能、多线程的执行环境。超微内核适用于内存很少（最少为 2KB）的系统或者简单的多线程系统（比如只有一些列中断处理和单后台 task）。这样的系统主要包括：嵌入式传感器 hub、传感器、简单 LED 可穿戴设备以及商店库存的标签。

微内核比超微内核的功能更加丰富。超微内核适用于这样的系统：内存更多（50 ~ 900 KB）、多通信设备（比如WIFI、低功耗蓝牙）、多 task。这样的系统主要包括：可穿戴设备、智能手表、物联网无线网关。
# Zephyr OS 的特征

Zephyr 内核是一个微型内核，被设计用于资源受限的系统：从简单的嵌入式传感器、可穿戴 LED，到复杂的智能手表、物联网无线网关。

Zephyr 支持多架构，包括：ARM Cortex-M、Intel x86 和 ARC。在 [这里](https://www.zephyrproject.org/doc/board/board.html)可以查看 Zephyr 支持的所有平台。

与其它微型内核相比，Zephyr 内核有很多独特的优秀特性：

 1. **单地址空间操作系统**。将应用程序相关的代码与内核结合在一起，创建一个在硬件上加载、运行的单一镜像。应用程序代码和内核代码运行在同一个共享地址空间。
 2. **高度可配置**。允许应用程序只包含它们需要的功能。
 3. **编译时定义资源**。所有系统资源都在编译时定义，以减小代码量、增强代码性能。
 4. **最小错误检查**。提供最小化的运行时错误检查，以减小代码量、增强代码性能。提供一个可选的错误检查基础，以协助应用程序的开发和调试。
 5. **广泛的服务**。提供了许多耳熟能详的服务：
  - 多线程服务：为基于优先级的、非抢占式的 fiber 和基于优先级的、抢占式的 task 提供可选的时间片。
  - 中断服务：在编译时、运行时均可注册中断处理函数。
  - 线程间同步服务：包括二元信号量、计数信号量和互斥信号量。
  - 线程间数据传递服务：包括基本消息队列、增强型消息队列和字节流。
  - 内存分配服务：动态地分配固定尺寸、可变尺寸的内存块。
  - 电源管理服务：包括无滴答 CPU 空转和高级 CPU 空转。

# Zephyr OS 源码结构
Zephyr 源码树的顶层目录如下所述，每个顶层目录都包括一级或多级子目录。

- **arch**: 架构相关的超微内核代码和平台代码。Zephyr 支持的每个架构都有一个子目录，且这些子目录还包括下面子目录：
 - 架构相关的超微内核源文件。
 - 架构相关的超微内核的私有 API 的头文件。
 - 平台相关的代码。
- **boards**: board 相关的代码和配置文件。
- **doc**: Zephyr 文档相关的材料和工具。
- **drivers**: 设备驱动代码。
- **include**: 所有（不包括 `lib` 目录）公有 API 的头文件。
- **kernel**: 微内核代码，以及架构无关的超微内核代码。
- **lib**: 库代码，包括最小的 C 库。
- **misc**: 杂项代码。
- **net**: 网络相关的代码，包括蓝牙协议栈和网络协议栈。
- **samples**: 微内核、超微内核、蓝牙协议栈和网络协议栈的应用程序举例。
- **tests**: 内核各个特性的测试代码。
- **scripts**: 用于编译、测试 Zephyr 应用程序的程序和文件。

# 学习资料
- [Zephyr Project 官网](https://www.zephyrproject.org/)
- [Zephyr OS 文档](https://www.zephyrproject.org/doc)
- Zephyr OS 源码

　　源码是最好的学习资料，这是毋容置疑的。

　　获取源码： `git clone https://gerrit.zephyrproject.org/r/zephyr `
- 一些 PPT
 - [Zephyr Project Security - OIS_2016_Updated](http://events.linuxfoundation.org/sites/events/files/slides/Zephyr%20Project%20Security%20-%20OIS_2016_Updated.pdf)
 - [Zephyr Overview - OpenIOT Summit 2016](http://events.linuxfoundation.org/sites/events/files/slides/Zephyr%20Overview%20-%20OpenIOT%20Summit%202016.pdf)








