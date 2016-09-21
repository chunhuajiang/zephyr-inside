---
title: Zephys OS nano 内核篇：isr 服务
date: 2016-09-22 23:23:25
categories: ["Zephyr OS"]
tags: [Zephyr]
---

- [概念](#概念)
- [移交 ISR 的工作](#移交-isr-的工作)
- [安装一个 ISR](#安装一个-isr)
- [ISR 相关的 API 和 宏](#isr-相关的-api-和-宏)
    - [API](#api)
    - [宏](#宏)

<!--more-->
# 概念
ISR 的全称是 Interrupt Service Routine, 即中断服务例程，它主要用于响应硬件(或软件)中断。当一个中断到来时，ISR 会抢占正在执行的 fiber 或者 task。当 ISR 执行完毕后，之前被抢占的 task 或者 fiber 将恢复执行。

> 请注意上一节所说的“fiber是不可抢占”这一概念，它指的是高优先级的 fiber 不可抢占低优先级的 fiber。

每个 ISR 具有如下属性：
- 触发 ISR 的 IRQ 信号
- 与 IRQ 相关联的优先级
- 处理中断的函数的地址
- 传递给该函数的参数

中断向量表 IDT 用于在中断源和中断服务例程之间建立关联。当发生一个中断时，硬件会自动根据中断号查找 IDT 中对应的表项，找到中断服务程序的入口地址，然后跳转到对应的 ISR 去执行。

多个中断源可以利用同一个函数处理中断，即一个函数可以服务于产生多种类型中断的一个设备，或产生同种类型中断的多个设备。传递给 ISR 的参数可以用于区分是哪一个中断源产生的中断。

Zephyr 内核为所有未使用的 IDT 入口提供了一个默认的 ISR。如果捕捉到了一个不期望产生的中断，该 ISR 将主动产生一个系统致命错误。

内核支持中断嵌套，即当一个 ISR 正在执行时，可以被更高优先级的中断所抢占。当高优先级的 ISR 执行完毕后，将恢复执行低优先级的 ISR。

内核允许 task 或 fiber 临时锁定 ISR。中断的锁定和解锁是一对相反的过程。锁定 ISR 的过程也可以是嵌套的，即锁定操作可以多次重复执行，但是之后必须解锁相同的次数，内核才会再次响应中断。

# 移交 ISR 的工作
ISR 程序应当尽量保持短小，以确保系统的行为是可预料的。如果需要处理一个比较耗时的工作，ISR 程序可以将其移交给 fiber 或 task，然后尽快恢复正常执行，以响应其它中断。

如果 ISR 将工作移交给 fiber，那么在 ISR 退出时会进行上下文切换。因此，中断相关的处理通常几乎得以立即执行(但在执行该 fiber 前还需执行中断前被打断的 fiber 以及高优先级的 fiber)。

如果 ISR 将工作移交给 task，那么在 ISR 退出时会进行上下文切换，但是会先切换到 microkernel 的服务 fiber(且在执行该 fiber 前还需执行中断前被打断的 fiber 以及高优先级的 task)，再切换到该 task。

> PS:这里的理解可能还有问题，今后再补充或修正。

# 安装一个 ISR
```
#define MY_DEV_IRQ  24       /* 设备使用的 IRQ 是 24 */
#define MY_DEV_PRIO  2       /* 中断的优先级是 2 */
/* 传递给 my_isr() 的参数，在本例中是一个指向设备的指针 */
#define MY_ISR_ARG  DEVICE_GET(my_device)
#define MY_IRQ_FLAGS 0       /* IRQ 的标志，在非 x86 的架构中是没用的 */

void my_isr(void *arg)
{
   ... /* ISR 相关的代码 */
}

void my_isr_installer(void)
{
   ...
   IRQ_CONNECT(MY_DEV_IRQ, MY_DEV_PRIO, my_isr, MY_ISR_ARG, MY_IRQ_FLAGS);
   irq_enable(MY_DEV_IRQ);            /* 使能 IRQ */
   ...
}

```
# ISR 相关的 API 和 宏
## API
- irq_enable()：使能中断。
- irq_disable()：禁能中断。
- irq_lock()：锁定所有的中断源。
- irq_unlock()：移除对中断源的锁定。

## 宏
- IRQ_connect()：注册一个静态的 ISR 到 IDT 中。



