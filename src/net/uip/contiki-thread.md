---
title: Zephys OS uIP 协议栈：Contiki - 初识线程
date: 2016-10-07 14:47:34
categories: ["Zephyr OS"]
tags: [Zephyr]
---

Contiki 里的线程与传统线程的概念不一样，为了避免喧宾夺主，我们简单了解一下其基本概念即可。

- [线程的结构体](#线程的结构体)
- [线程的定义](#线程的定义)
- [线程的执行实体(入口函数)](#线程的执行实体(入口函数))
- [线程的使用方法举例](#线程的使用方法举例)

<!--more-->
# 线程的结构体
结构体 struct process 描述了线程相关的所有信息：
```
truct process {
  struct process *next;
#if PROCESS_CONF_NO_PROCESS_NAMES
#define PROCESS_NAME_STRING(process) ""
#else
  const char *name;
#define PROCESS_NAME_STRING(process) (process)->name
#endif
  PT_THREAD((* thread)(struct pt *, process_event_t, process_data_t,
                       struct net_buf *, void *user_data));
  struct pt pt;
  unsigned char state, needspoll;
  void *user_data;
};
```
主要成员：
- next：线程通常会被放到一个线程链表中，使用 next 指向线程链表中的下一个线程。
- name：该线程的名字。
- thread：该线程的执行实体，类似于 Zephyr OS 中的线程入口函数。
- pt：这个是用于进行线程切换的关键因素，可以不深究。
- state：线程的状态标志，下一节会介绍。
- needspoll：线程的优先级标志，下一节会介绍。Contiki 里的线程有两种优先级。当线程的 needspoll 被设为 1 时，表示该线程具有高优先级，会在线程调度时优先被执行。
- user_data：传递给线程的用户数据。

# 线程的定义
使用宏 PROCESS() 定义一个线程：
```
#define PROCESS(name, strname)				\
  PROCESS_THREAD(name, ev, data, buf, user_data);	\
  struct process name = { NULL, strname,		\
                          process_thread_##name }
```
这个宏定义了一个线程结构体类型的变量。其中，PROCESS_THREAD() 是用于定义线程的执行实体。

该宏有两个参数：
- name：线程的执行实体的“名字”，是函数的名字。
- strname：线程的名字

# 线程的执行实体(入口函数)
```
#define PROCESS_THREAD(name, ev, data, buf, user_data)		\
static PT_THREAD(process_thread_##name(struct pt *process_pt,	\
				       process_event_t ev,	\
				       process_data_t data,	\
				       struct net_buf *buf,	\
				       void *user_data))

#define PT_THREAD(name_args) char name_args
```
将上面的宏展开：
```
static char process_thread_name(struct pt * process_pt, \
				       process_event_t ev,	\
				       process_data_t data,	\
				       struct net_buf *buf,	\
				       void *user_data)
```

# 线程的使用方法举例

在 Contiki 中，定义一个新线程的步骤是这样的：
- 先使用宏 PROCESS() 定义一个线程
- 再使用宏 PROCESS_THREAD() 实现线程的执行实体

相关代码如下：
```
PROCESS(hello_world_process, "Hello world process");

PROCESS_THREAD(hello_world_process, ev, data)
{
	PROCESS_BEGIN();//这个是线程头部的固定格式

    // 中间是线程实际的执行代码
	printf("Hello, world\n");

    PROCESS_END(); //这个是线程尾部的固定格式
}
```

如果不考虑 PROCESS_BEGIN() 和 PROCESS_END() 两个宏，我们将上面的代码展开如下：
```
// 申明线程的入口函数
static char process_thread_hello_world_process(/* 这里是参数 */);
// 定义一个线程，并对其成员进行初始化
struct process hello_world_process = {NULL, "Hello world process", process_thread_hello_world_process}
// 实现函数的入口函数
static char process_thread_hello_world_process(/* 这里是参数 */)
{
	printf("Hello, world\n");
}
```
