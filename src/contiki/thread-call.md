---
title: Zephys OS uIP 协议栈：Contiki - 线程的调度
date: 2016-10-07 15:53:21
categories: ["Zephyr OS"]
tags: [Zephyr]
---
上一节简单知道了 Contiki 中的线程长啥样，这一节我们来了解一下如何调用一个线程。


<!--more-->

# 基本概念
## 线程链表

Contiki 维护了一个全局的线程链表 process_list，所有被启动的线程都将加入到这个线程链表中。

## 线程的状态

Contiki 中的线程有三种状态：
- PROCESS_STATE_NONE：无效态。表示一个线程没有被启动，或者已经被退出。处于这种状态的线程不在线程链表中。
- PROCESS_STATE_CALLED：执行态。表示一个线程正在被调度，即正在执行线程的执行实体(入口函数)。处于这种状态的线程在线程链表中。
- PROCESS_STATE_RUNNING：可执行态(就绪态)。表示线程处于可执行态，即线程位于线程链表中，等待某一个时刻被调度、执行。

## 线程的优先级
在 Contiki 中，线程有两个优先级：
- 普通优先级。线程结构体 struct process 中的成员 neeedspoll 为 0 的线程。
- 高优先级。

# 线程的调度
## 启动一个线程
```
void
process_start(struct process *p, process_data_t data)
{
  struct process *q;

  // 如果线程已经在全局线程链表中(即已经被启动)，直接返回
  for(q = process_list; q != p && q != NULL; q = q->next)
    ;
  if(q == p) {
    return;
  }

  // 将该线程加入到线程链表的头部
  p->next = process_list;
  process_list = p;
  // 设置线程的状态为可执行态
  p->state = PROCESS_STATE_RUNNING;
  // 初始化线程的上下文。详细信息请参考《线程切换》一节。
  PT_INIT(&p->pt);

  // 向线程投递一个同步事件 PROCESS_EVENT_INIT
  // 关于投递事件，请参考《初识事件》一节。
  process_post_synch(p, PROCESS_EVENT_INIT, data);
}
```
总结一下，启动线程时将线程加入到线程链表的头部，然后设置一些状态等信息，向该线程投递一个同步事件 PROCESS_EVENT_INIT。下面我们看看 process_post_synch() 内部做了什么。

### process_post_synch
函数 process_post_synch 可以用于调用一个线程。
```
void process_post_synch(struct process *p, process_event_t ev, process_data_t data)
{
  struct process *caller = process_current;

  call_process(p, ev, data);
  process_current = caller;
}
```
process_current 是一个全局的指针变量，始终指向当前正在或即将被调度的线程(即正在或即将执行线程入口函数的线程)。由于 call_process() 的内部会改变 process_current 这个变量的值，所以在进入 call_process() 前先将其保存到一个临时变量 caller，从 call_process() 退出后再从这个临时变量恢复回来。

#### call_process
```
static void call_process(struct process *p, process_event_t ev, process_data_t data)
{
  int ret;

  // 如果线程是处于可执行态，且线程的入口函数不为 NULL，则执行该线程的执行实体(入口函数)。
  if((p->state & PROCESS_STATE_RUNNING) && p->thread != NULL) {
    // 将 process_current 指向即将被调度的线程
    process_current = p;
    // 设置线程的状态为“正在被执行态”
    p->state = PROCESS_STATE_CALLED;
    // 调用该线程的执行实体，即切换到该线程去执行
    ret = p->thread(&p->pt, ev, data, p->user_data);
    // 代码走到这里，说明已经执行完 p->thread 这个线程实体了。在 p->thread 这个线程实体内部，
    // 会返回一个返回代码，表示该线程执行实体是由于什么原因而返回。关于这个返回状态，更详细的信
    // 息请参考《线程切换》一节。
    if(ret == PT_EXITED || ret == PT_ENDED || ev == PROCESS_EVENT_EXIT) {
    	// 根据线程入口函数的返回值，判断是否要将该线程从线程链表中删除
      // exit_process() 会对线程做一些清理工作，然后将其从线程链表中删除
	    exit_process(p, p);
    } else {
    	// 将线程的状态由“正在被执行态”切换回“等待被执行态”
      p->state = PROCESS_STATE_RUNNING;
    }
  }
}
```
所以，函数 call_process() 才会真正去执行一个线程。此时我们再回头看一下，可以得出一个结论：**process_start() 在启动一个线程时，会立即执行该线程的线程实体**。

## 设置线程的优先级
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
## 线程的调度算法
Contiki 中，线程的调度策略体现在 process_run() 这个函数中：
```
int process_run()
{
  if(poll_requested) {
    // 如果有线程被置为高优先级，则先调度这些线程
    do_poll();
  }

  // 再调度一个普通线程
  do_event();

  // nevents 表示当前系统还有多少个事件需要处理，更多信息请参考
  // 《初始事件》一节。
  return nevents + poll_requested;
}
```
### 处理高优先级的线程
```
static void do_poll()
{
  struct process *p;

  poll_requested = 0;
  // 轮询线程链表中的所有线程，如果该线程为高优先级的线程，则执行该线程
  for(p = process_list; p != NULL; p = p->next) {
    if(p->needspoll) {
      p->state = PROCESS_STATE_RUNNING;
      p->needspoll = 0;
      // 执行该线程，执行线程的入口函数
      call_process(p, PROCESS_EVENT_POLL, NULL);
    }
  }
}
```
注意，do_poll() 这个函数将线程链表中所有需要高优先级的线程都执行了之后才返回的，这与后面我们要学习的 do_event() 有所不同。
### 处理低优先级的线程
当调度器处理完所有高优先级的线程后，会再使用函数 do_event() 调度低优先级的线程。这部分的内容涉及到事件驱动，我们后面单独拿一节来讲解。

# 总结

本节我们先学习了线程的一些基础知识，比如全局的线程链表、线程的状态、优先级，在理解了这些基础概念之后，我们再学习了线程的调度，比如启动一个线程，轮询线程链表中所有高优先级的线程，设置线程的优先级等。这些概念，第一次接触的时候可能有很多疑惑，此时不要停下脚步，待学习完后面的所有章节后，我们再回来回顾一下，那是就会明白很多。
