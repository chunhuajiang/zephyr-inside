# Zephyr OS 学习笔记 - 内核篇

- **[点击此处切换回 master 分支](../../tree/master/)**
- **在线预览：[http://iot-fans.xyz/zephyr/inside/kernel/index.html](http://iot-fans.xyz/zephyr/inside/kernel/index.html)**

# 目录
- 前言
  - [前言](src/preface.rst)
- 系统启动流程
  - [系统启动 - 汇编阶段](src/boot-asm.rst)
  - [系统启动 - C 准备阶段](src/boot-prep-c.rst)
  - [系统启动 - 多线程阶段](src/boot-multithread.rst)
- 线程
  - [线程概述]
  - [线程的本质]
  - [线程切换 \_Swap()]
- 内核大总管
  - \_kernel
- 基本服务
  - 内核链表 dlist
  - 等待队列 wait_q
  - 超时服务 timeout
  - 定时器 timer
- 同步
  - 信号量
  - 互斥量
  - 告警
- 数据传递
  - FIFO
  - LIFO
  - 栈 STACK
  - 消息队列 message-queue
  - 邮筒 mailbox
  - 管道 PIPE
- 内存分配
  - 内存片 Memory Slab
  - 内存池 Memory Pool
  - 堆 Heap
- 其它服务
  - 中断
  - 原子服务
  - 浮点服务
  - 环形缓冲
  - 内核事件日志器



