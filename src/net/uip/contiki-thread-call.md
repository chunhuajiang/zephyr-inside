---
title: Zephys OS uIP 协议栈：Contiki - 线程的调用
date: 2016-10-07 15:53:21
categories: ["Zephyr OS"]
tags: [Zephyr]
---
上一节简单知道了 Contiki 中的线程长啥样，这一节我们来了解一下如何调用一个线程。

- [线程链表](#线程链表)
- [线程的状态](#线程的状态)
- [启动一个线程](#启动一个线程)
- [调用一个线程](#调用一个线程)
- [设置线程的优先级](#设置线程的优先级)
- [线程的调度算法](#线程的调度算法)
- [处理高优先级的线程](#处理高优先级的线程)
- [处理低优先级的线程](#处理低优先级的线程)
<!--more-->
# 线程链表

Contiki 维护了一个全局的线程链表 process_list，所有被启动的线程都将加入到这个线程链表中。

# 线程的状态
Contiki 中的线程有三种状态：
- PROCESS_STATE_NONE：表示一个线程没有被启动，或者已经被退出。处于这种状态的线程不在线程链表中。
- PROCESS_STATE_CALLED：表示一个线程正在被调度，即正在执行线程的执行实体(入口函数)。处于这种状态的线程在线程链表中。
- PROCESS_STATE_RUNNING：表示线程处于可执行态，即线程位于线程链表中，等待某一个时刻被调度、执行。

# 启动一个线程
```
void process_start(struct process *p, process_data_t data, void *user_data)
{
  struct process *q;

  // 如果线程已经在全局线程链表中(即已经被启动)，直接返回
  for(q = process_list; q != p && q != NULL; q = q->next);
  if(q == p) {
    return;
  }

  // 将该线程加入到线程链表的头部
  p->next = process_list;
  process_list = p;
  // 设置线程的状态
  p->state = PROCESS_STATE_RUNNING;
  // 设置线程的用户数据
  p->user_data = user_data;
  // 初始化线程上下文相关的内容
  PT_INIT(&p->pt);

  // 调用线程的执行实体(入口函数)
  process_post_synch(p, PROCESS_EVENT_INIT, data, NULL);
}
```
总结一下，启动线程时将线程加入到线程链表的头部，然后设置一些状态等信息，然后调用该线程的执行实体(入口函数)。

# 调用一个线程
函数 process_post_synch 可以用于调用一个线程。

> 更专业的说法叫做给线程 p 投递一个同步事件，请参考后面《初识事件驱动》一节。
```
void process_post_synch(struct process *p, process_event_t ev, process_data_t data,
		   struct net_buf *buf)
{
  struct process *caller = process_current;

  call_process(p, ev, data, buf);
  process_current = caller;
}
```
它的内部实际调用的是 call_process() 函数。

process_current 是一个全局的指针变量，始终指向当前正在被调度的线程(即正在执行线程入口函数的线程)。由于 call_process() 的内部会改变 process_current 这个变量的值，所以在进入 call_process() 前先将其保存到一个临时变量，从 call_process() 退出后再从这个临时变量恢复回来。

```
static void call_process(struct process *p, process_event_t ev, process_data_t data,
		struct net_buf *buf)
{
  int ret;

  // 如果线程是处于可执行态，且线程的入口函数不为 NULL，则执行该线程的执行实体(入口函数)。
  if((p->state & PROCESS_STATE_RUNNING) && p->thread != NULL) {
    // 将 process_current 指向即将被调度的线程
    process_current = p;
    // 设置线程的状态为“被调度状态”
    p->state = PROCESS_STATE_CALLED;
    // 调用该线程的执行实体，即切换到该线程取执行
    ret = p->thread(&p->pt, ev, data, buf, p->user_data);
    if(ret == PT_EXITED || ret == PT_ENDED || ev == PROCESS_EVENT_EXIT) {
    	// 根据线程入口函数的返回值，判断是否要将该线程从线程链表中删除
      // exit_process() 会对线程做一些清理工作，然后将其从线程链表中删除
	    exit_process(p, p, buf);
    } else {
    	// 将线程的状态切换回可执行态
      p->state = PROCESS_STATE_RUNNING;
    }
  }
}
```

# 设置线程的优先级
通过 process_poll 函数可以将一个线程设置为高优先级的线程。
```
void
process_poll(struct process *p)
{
  if(p != NULL) {
    if(p->state == PROCESS_STATE_RUNNING ||
       p->state == PROCESS_STATE_CALLED) {
      // 现将线程的 needspoll 成员置为 1
      p->needspoll = 1;
      // 再将全局变量 poll_requested 置为 1，以告诉线程的调度器
      // 现在有线程处于高优先级状态。然后调度器在下次调度线程时，会
      // 优先调度高优先级的线程
      poll_requested = 1;
    }
  }
}
```
# 线程的调度算法
Contiki 中，线程的调度策略体现在 process_run() 这个函数中：
```
int process_run(struct net_buf *buf)
{
  if(poll_requested) {
    // 如果有线程被置为高优先级，则先调度这些线程
    do_poll(buf);
  }

  // 再调度一个普通线程
  do_event(buf);

  return nevents + poll_requested;
}
```

# 处理高优先级的线程
```
static void
do_poll(struct net_buf *buf)
{
  struct process *p;

  poll_requested = 0;
  // 轮询线程链表中的所有线程，如果该线程为高优先级的线程，则执行该线程
  for(p = process_list; p != NULL; p = p->next) {
    if(p->needspoll) {
      p->state = PROCESS_STATE_RUNNING;
      p->needspoll = 0;
      // 执行该线程，执行线程的入口函数
      call_process(p, PROCESS_EVENT_POLL, NULL, buf);
    }
  }
}
```
# 处理低优先级的线程
当调度器处理完所有高优先级的线程后，会再使用函数 do_event() 调度低优先级的线程。这部分的内容涉及到事件驱动，我们后面单独拿一节来讲解。
