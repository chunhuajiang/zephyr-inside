# 目录

* [**基础篇**]
   * [Zephyr OS 简介](src/introduce/introduction.md)
   * [Hello World](src/introduce/hello-world.md)
   * [连接硬件 Arduino Due](src/introduce/arduino_due.md)
   * [漫谈Zephyr与Contiki的未来](src/introduce/vs-contiki.md)
* [**内核篇**]
   * [**nanokernel**]
      * [前言](src/kernel/nanokernel/preface.md)
      * [执行上下文](src/kernel/nanokernel/context.md)
	  * [task 服务 - 基础](src/kernel/nanokernel/task_basic.md)
	  * [fiber 服务 - 基础](src/kernel/nanokernel/fiber_basic.md)
	  * [isr 服务 - 基础](src/kernel/nanokernel/isr_basic.md)
      * [初识线程](src/kernel/nanokernel/thread.md)
      * [内核大总管_nanokernel](src/kernel/nanokernel/nanokernel.md)
      * [fiber服务](src/kernel/nanokernel/fiber.md)
	  * [isr 服务]
      * [原子操作 atomic](src/kernel/nanokernel/atomic.md)
      * [内核链表 dlist](src/kernel/nanokernel/dlist.md)
      * [等待队列 wait_q](src/kernel/nanokernel/wait_q.md)
      * [超时服务 timeout](src/kernel/nanokernel/timeout.md)
      * [定时器 timer](src/kernel/nanokernel/timer.md)
      * [信号量 semaphore](src/kernel/nanokernel/sema.md)
      * [FIFO](src/kernel/nanokernel/fifo.md)
      * [LIFO](src/kernel/nanokernel/lifo.md)
      * [栈 Stack](src/kernel/nanokernel/stack.md)
      * [环形缓冲 Ring Buffer](src/kernel/nanokernel/ring_buf.md)
      * [系统启动流程(汇编部分)]
      * [系统启动流程(C语言部分)]
      * [上下文切换 _Swap]
      * [总结]
   * [**microkernel**] 官方正在对kernel部分正在进行整合，所以microkernel这部分暂时先不研究了
      * [前言]
	  * [Task 服务 - 基础]
	  * [Task 服务]
	  * [Fiber 服务 - k_server]
	  * [定时器 Timer]
	  * [内存管理]
	     * [内存映射 Memory Map]
	     * [内存池 Memory Pool]
      * [线程间同步]
	     * [事件 Event]
	     * [信号量 Semaphore]
	     * [互斥 Mutex]
      * [线程间数据传递]
	     * [FIFO]
	     * [邮筒 MailBox]
	     * [管道 Pipe]
* [**驱动篇**]
   * [设备驱动模型](src/driver/device-driver-module.md)
   * [控制台驱动]
   * [串口驱动]
   * [printk]
   * [gpio 驱动]
   * [I2C 驱动]
   * [SPI 驱动]
   * [共享中断]
* [**移植篇**]
   * [cc2538] 计划 12.31日前完成。移植的最终目的：能用它来做网络相关的实验。
      * [前言]
      * [搭建框架]
      * [电源/时钟配置] 主要涉及CC2538芯片手册的第1、2、3、4、7、9章
      * [串口驱动] 主要涉及CC2538芯片手手册的第18章
	  * [RF驱动] 主要涉及CC2538芯片手手册的第23章
      * [SPI 驱动]
	  * [其它驱动...]
* [**网络篇**]
   * [前言](src/net/introduce.md)
   * [缓冲池 Buffer Pool]
      * [简单 Buffer](src/net/common/simply-buf.md)
      * [完整 Buffer](src/net/common/full-buf.md)
   * [uIP]
      * [Contiki 核心概念]
         * [事件]
         * [线程]
         * [packetbuf]
         * [queuebuf]
      * [对 uIP 的封装]
         * [L2 buffer]
         * [net context]
         * [net core - 概念](src/net/uip/netcore-concept.md)
         * [net core - 初始化]
         * [net core - 发送数据]
         * [net core - 接收数据]
      * [底层协议]
         * [net driver]
         * [net driver - 发送数据]
         * [net driver - 接收数据]
         * [6LoWPAN - 压缩与解压缩]
         * [6LoWPAN - 分片与重组]
         * [MAC 层 - 帧的形成]
         * [MAC 层 - 访问信道 CSMA]
         * [物理层]
         * [物理层 - 发送数据]
         * [物理层 - 接收数据]
      * [网络层]
         * [ip buffer]
      * [传输层]
      * [应用层]
   * [yaip]
* [开发者篇]
