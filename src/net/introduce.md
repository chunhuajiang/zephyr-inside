---
title: Zephys OS 网络篇：前言
date: 2016-10-06 15:08:22
categories: ["Zephyr OS"]
tags: [Zephyr]
---

Zephyr OS 在网络方面提供了两个协议栈：uIP 和 yaip。

- [uIP](#uip)
- [yaip](#yaip)
- [uIP 与 yaip 的比较](#uip-与-yaip-的比较)
- [配置 - 选择协议栈](#配置---选择协议栈)
- [关于网络篇的学习笔记](#关于网络篇的学习笔记)

<!--more-->

# uIP
uIP 的全称是 micro IP，即微型 IP 协议栈。它是 Contiki 操作系统里面所使用的一个协议栈。要完成一个网络协议栈，工作量非常巨大，不是在短时间内能完成的，所以 uIP 被移植到了 Zephyr OS 里面，作为一个过渡的网络协议栈。

uIP 的源码位于目录`net/ip`下。

> 为什么 micro IP 的简写是 uIP？ 具体原因不了解，但是可以做一个类比：微秒(microsecond) 的简写是 us。

# yaip
yaip 的全称是 yet another IP。当 Zephyr 团队希望开发一个新的协议栈时，由于 Zephyr 里面已经有一个协议栈了，且它的源码位于`net/ip`下，所以干脆给新的协议栈起了个名字 yet another IP。呃，好随意的一个名字。

yaip 的源码位于目录`net/yaip`下。

# uIP 与 yaip 的比较
为什么要实现一个新的协议栈？uIP 有什么不尽人意的地方？

不知...

# 配置 - 选择协议栈
在编写网络的应用程序时，我们要么使用 uIP 协议栈，要么使用 yaip 协议栈。

使用 Kconfig 工具选择协议栈：
```
进入一个工程目录
make ARCH=xxx BOARD=yyy menuconfig
然后依次选择：
    Networking  --->
      [*] Link layer and IP networking support
            IP stack (uIP)  --->  // 在这里选择使用哪个协议栈
            uIP stack  --->  // 在这里详细配置所选择的协议栈
```
# 关于网络篇的学习笔记

- uIP 和 yaip 使用了一些通用的数据结构和 API，所以我们先学习这部分东西，再学习 uIP 和 yaip。
- 由于 yaip 本身还在开发之中，很多功能都还没完成，所以我们先学习 uIP，再学习 yaip。
- uIP 和 yaip 虽然是两个协议栈，但是它们里面所实现的协议基本是相同的，不同的只是软件自身的组织架构。所以当我们当我们学习完一个协议栈后，再学习另一个协议栈轻松很多。
- 网络部分所涉及的知识非常庞杂，所以不可能像内核一样讲解到每个函数，所以我只是尽量讲清楚里面的逻辑结构、调用关系，并讲解部分主要的函数，太细节、碎片化的内容请大家自己看代码。
- 从网络篇的目录就可以看出来，网络篇有很大一个特点，**Buffer 特别多**！没办法，想要弄明白数据在协议栈中时怎么转换的，必须搞清楚这些buffer！
