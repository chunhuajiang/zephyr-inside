---
title: Zephys OS nano 内核篇：task 服务 - 基础
date: 2016-09-21 18:31:12
categories: ["Zephyr OS"]
tags: [Zephyr]
---

- [task 的概念](#task-的概念)
- [task 的生命周期](#task-的生命周期)
- [task 调度](#task-调度)
- [定义后台 task](#定义后台-task)

<!--more-->

# task 的概念
nanokernel 中的 task 是一个**可抢占式**的线程。task 主要用于处理那些太复杂或者执行时间太长而不能由 fiber 和 isr 完成的工作。

nanokernel 的应用程序可以且必须定义一个 task，即所谓的后台(background) task。只有没有 fiber 和 isr 在运行时，后台 task 才会运行。后台 task 的入口函数是 main() 函数。

> 注意，nanokernel 中的后台 task 与 microkernel 中的通用 task 有很大的不同，具体信息请参考 microkernel 相关章节。 

# task 的生命周期

在系统启动进行初始化时，内核会自动运行后台 task，即自动运行 main() 函数。更多信息请参考《Zephyr OS nano 内核篇：系统启动流程(C语言部分)》。

后台 task 一旦被启动，它将永远执行下去(这里的永远执行下去指的是不会被杀死)。如果后台 task 主动从 main() 函数中返回了，内核会将这个 task 放入一个永久的空转状态()。
# task 调度
由于 task 的优先级比 fiber 和 isr 的优先级低，所以只有系统中没有 fiber 和 isr 需要执行时才会执行这个后台 task。

由于 task 是可抢占式的，所以当有新的 fiber 或者 isr 需要执行时，新的 fiber 或者 isr 会抢占当前 task 的 CPU 使用权，这是一个上下文切换的过程。当进行上下文切换时，内核会自动保存后台 task 的 CPU 的寄存器的值到内存中。当后台 task 在后来恢复执行时，这些值将从恢复到寄存器中。

# 定义后台 task
应用程序必须定义后台 task，其格式如下：
```
void main(void)
{
	/* background task processing */
	...
	/* (optional) enter permanent idling state */
	return;
}
```
内核配置选项 CONFIG_MAIN_STACK_SIZE 指定了后台 task 在内存中所使用的栈空间的大小，以字节为单位。



