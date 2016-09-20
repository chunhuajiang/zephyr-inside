---
title: Zephys OS nano 内核篇：前言
date: 2016-09-20 23:22:43
categories: ["Zephyr OS"]
tags: [Zephyr]
---
要想深入学习zephyr，内核是一道绕不开的坎，因为无论是系统的哪一部分，驱动、网络、蓝牙、应用，都会使用内核提供的各种服务，因此学习内核，能为学习其它模块奠定一个很好的基础。

zephyr 的内核分为两种：nanokernel 和 microkernel。我们先学习 nanokernel，它也是 microkernel 的基础。

我们将内核提供的一种小功能模块叫做一个服务。内核中的各种服务是相互交错、相互嵌套、相互引用的，因此刚接触的时候，肯定一片茫然，但是只要**坚持**下去，一点一点地学习，勤于思考，回头再看这些内核中的服务时，就会豁然开朗。

此外，不仅 nanokernel 内核的各个服务相互交错，nanokernel 和 microkernel 也相互交错，更增加了学习的难度。因此，为了能更轻松地学习 nanokernel，我们先不考虑 nanokernel 中与 microkernel 相关的内容，即**我们先假设 zephyr 中只有 nanokernel**。