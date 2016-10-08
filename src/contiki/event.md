---
title: Zephys OS uIP 协议栈：Contiki - 初始事件
date: 2016-10-07 18:36:26
categories: ["Zephyr OS"]
tags: [Zephyr]
---
如果用一句话概况 Contiki 内核的特点，就是：Contiki 是一个由事件来驱动线程运行的操作系统。本节先初步了解 Contiki 的事件驱动的原理。

- [事件](#事件)
- [事件的控制结构](#事件的控制结构)
- [事件的内存缓冲模型](#事件的内存缓冲模型)
- [将事件投递给线程](#将事件投递给线程)
    - [同步投递](#同步投递)
    - [异步投递](#异步投递)
- [处理缓冲队列中的事件](#处理缓冲队列中的事件)

<!--more-->
# 事件
```
typedef unsigned char process_event_t;
```
事件的本质是一个无符号字符类型的整数，为了便于理解，我们可以将其理解为一个编号。线程的执行实体接收到事件(即一个事件编号)后，会根据这个编号来做相应的处理。

# 事件的控制结构
结构体 struct event_data 用于描述一个事件的相关信息：
```
struct event_data {
  process_event_t ev;
  process_data_t data;
  struct process *p;
};```
其成员变量：
- ev：事件，即一个编号。
- data：指向需要传递给线程实体(入口函数)的数据。
- p：该事件所绑定的线程。

# 事件的内存缓冲模型
Contiki 的内核维护了一个环形缓冲队列，这个队列里的每个元素都是一个事件的控制结构。这个环形缓冲队列是由一个数组构成的：
```
static struct event_data events[PROCESS_CONF_NUMEVENTS];
```
这个环形缓冲最多能容纳 PROCESS_CONF_NUMEVENTS 个事件的控制结构。

此外，内核还定义了两个变量：
```
static process_num_events_t nevents, fevent;
```
其中：
- nevents：表示该缓冲队列中已经存放的事件控制结构的个数。
- fevent：是一个下标索引，“指向”缓冲中存放的第一个事件控制结构。

# 将事件投递给线程
一个线程的执行实体要被调用，必须将一个事件投递给该线程。事件的投递分为两类：
- 同步投递：指的是将事件投递给一个线程后，该线程会立即执行。
- 异步投递：指的是将事件投递给一个线程后，该线程不会理解执行。具体的做法是，先将事件的相关控制信息保存到事件的缓冲队列中，随后调度器会从这个缓冲队列中取出事件的控制信息，然后调用线程的执行实体。

## 同步投递
其实同步投递已经在上一节中介绍过了，即 process_post_synch() 这个函数:
```
void process_post_synch(struct process *p, process_event_t ev, process_data_t data)
{
  struct process *caller = process_current;

  call_process(p, ev, data);
  process_current = caller;
}
```
这次我们主要关注该函数的三个参数：
- p：要接收事件的线程
- ev：要投递给线程的事件
- data：指向要传递给线程的执行实体的数据

咦，这不就是事件的控制结构体的各个成员嘛！为什么会这样，且看本节后面的内容。

## 异步投递
函数 process_post 用于像事件投递一个异步事件：
```
int process_post(struct process *p, process_event_t ev, process_data_t data)
{
  static process_num_events_t snum;

  if(nevents == PROCESS_CONF_NUMEVENTS) {
    // 事件的缓冲队列满了，返回一个错误码给调用线程
    return PROCESS_ERR_FULL;
  }

  // fevent 是事件缓冲队列中缓存的第一个元素的索引
  // nevents 是事件缓存队列中已缓存的元素的个数
  // fevent + nevents 就表示缓存队列中已缓存数据(最后一个元素)的下一个索引，
  // 也就是用来存储此次事件控制结构的索引
  // 对 PROCESS_CONF_NUMEVENTS 进行求模运算是因为缓冲队列是环形的
  snum = (process_num_events_t)(fevent + nevents) % PROCESS_CONF_NUMEVENTS;
  // 将事件的控制结构信息保存到该索引所对应的内存空间里面。
  events[snum].ev = ev;
  events[snum].data = data;
  events[snum].p = p;
  // 缓冲队列中元素已缓冲元素个数递增 1
  ++nevents;

  return PROCESS_ERR_OK;
}
```
该函数的三个参数与同步投递的参数是一样的：
- p：要接收事件的线程
- ev：要投递给线程的事件
- data：指向要传递给线程的执行实体的数据

所谓的异步投递，指的是将事件的控制结构信息保存到事件的缓冲队列里面，等待调度机处理。
# 处理缓冲队列中的事件
Contiki 中的调度器使用 do_event() 函数处理缓冲在事件缓冲队列中的事件：
```
static void do_event(void)
{
  static process_event_t ev;
  static process_data_t data;
  static struct process *receiver;
  static struct process *p;

  // 如果缓冲队列中缓冲了数据，处理之
  if(nevents > 0) {

      // 取出缓冲队列中的第一个数据，即索引 fevent 处存放的数据
      ev = events[fevent].ev;
      data = events[fevent].data;
      receiver = events[fevent].p;

      // 取出数据后，fevent + 1
      // 对 PROCESS_CONF_NUMEVENTS 进行求模运算是因为缓冲队列是环形的
      fevent = (fevent + 1) % PROCESS_CONF_NUMEVENTS;
      // 取出数据后，缓冲队列缓冲的总元素个数递减 1
      --nevents;

      // Contiki 中定义了一个特殊的线程，叫做广播线程，即 PROCESS_BROADCAST
      // 当向该线程投递事件时，实际上相当于给所有的线程都投递了一个事件
      if(receiver == PROCESS_BROADCAST) {
           // 如果接收线程是广播线程，遍历线程链表，依次调用所有线程
           for(p = process_list; p != NULL; p = p->next) {
	            if(poll_requested) {
                 // 如果有高优先级的线程，则先调度高优先级的线程
	               do_poll();
	            }
              // 调用线程
	            call_process(p, ev, data);
           }
       } else {
         if(ev == PROCESS_EVENT_INIT) {
         // 如果该事件是一个初始化事件，先修改该线程的状态为可执行态
	       receiver->state = PROCESS_STATE_RUNNING;
        }
        // 调用线程
        call_process(receiver, ev, data);
      }
   }
}
```
