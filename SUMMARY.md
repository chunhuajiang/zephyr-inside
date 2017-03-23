# Summary

* [Introduction](README.md)

## 入门篇
* [Zephyr 简介](get_started/introduce.md)
* [搭建开发环境](get_started/env.md)
   * [开发环境 - Ubuntu](get_started/env_ubuntu.md)
   * [开发环境 - 懒人版](get_started/env_easy.md)
* [入门实验]
   * [实验 - hello world](get_started/hello.md)
   * [实验 - shell](get_started/shell.md)
   * [实验 - led](get_started/led.md)
   * [实验 - ping](get_started/ping.md)
   * [实验 - 自动获取 IP 地址](get_started/dhcp.md)
   * [实验 - 蓝牙](get_started/beacon.md)
   * [实验 - JavaScript ](get_started/js.md)
   * [实验 - Python ](get_started/python.md)

## 调试篇
* [准备工作](debug/prepare.md)
* [Qemu](debug/qemu.md)
* [Arduino 101](debug/arduino_101.md)
* [Arduino Due](debug/arduino_due.md)
* [frdm-k64f](debug/frdm-k64f.md)
* [nRF-51](debug/nrf51.md)
* [cc2538](debug/cc2538.md)
* [96b carbon](debug/96b_carbon.md)
* [stm32](debug/stm32.md)


## 内核篇
* [前言](kernel/pre.md)
* [系统启动](kernel/boot.md)
   * [启动 - 汇编部分](boot-asm.md)
   * [启动 - C 准备阶段](boot-prep.md)
   * [启动 - 多线程阶段](boot-c.md)
* [线程]
   * [线程概述]
   * [线程的本质]
   * [线程的切换 _Swap()]
* [内核大总管 _kernel]
* [基本服务]
   * [内核链表 dlist]
   * [等待队列 wait_q]
   * [超时服务 timeout]
   * [定时器 timer]
* [同步]
   * [信号量]
   * [互斥量]
   * [告警]
* [数据传递]
   * [FIFO]
   * [LIFO]
   * [栈]
   * [消息队列]
   * [邮筒]
   * [管道]
* [内存分配]
   * [内存池]
   * [内存片]
   * [堆内存池]
* [其它服务]
   * [中断]
   * [浮点服务]
   * [环形缓冲]
   * [内核事件日志器]

## 驱动篇

## 网络篇

## 蓝牙篇

## 移植篇

## 应用篇
