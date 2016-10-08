---
title: Zephys OS uIP 协议栈：Contiki - 事件定时器 etimer
date: 2016-10-07 23:10:32
categories: ["Zephyr OS"]
tags: [Zephyr]
---

本节我们讨论 Contiki 里面的一个定时器 —— 事件定时器。

- [定时器](#定时器)
- [事件定时器](#事件定时器)
- [事件定时器链表](#事件定时器链表)
- [更新 next_expiration](#更新-next_expiration)
- [向定时器链表添加定时器](#向定时器链表添加定时器)
- [事件定时器线程](#事件定时器线程)
- [事件定时器的 API](#事件定时器的-api)
    - [启动定时器](#启动定时器)
    - [重置定时器](#重置定时器)
    - [重启定时器](#重启定时器)
    - [判断定时器是否到期](#判断定时器是否到期)
    - [判断定时器还有多久到期](#判断定时器还有多久到期)

<!--more-->

# 定时器
所谓的定时器，指的是我们想要做一件事儿，但是这个事儿不是马上去做，而是在经过一段指定的时间后再做。
Contiki 使用结构体 struct timer 来描述定时器相关的信息：
```
struct timer {
  clock_time_t start;
  clock_time_t interval;
};

typedef unsigned long clock_time_t;
```
其中：
- start：记录定时器启动时的系统时间。
- interval：记录该定时器需要等待的时间。

定时器的这个结构体不会单独使用，而是内嵌在事件定时器里面的。


# 事件定时器
所谓的事件定时器，指的是经过一段指定的时间后，向一个线程投递一个定时器事件(PROCESS_EVENT_TIMER)。

结构体 struct etimer 用于描述事件定时器相关的所有信息：
```
struct etimer {
  struct timer timer;
  struct etimer *next;
  struct process *p;
};
```
其中：
- timer：用来记录定时器相关信息的变量
- next：所有的事件定时器会被维护在一个事件定时器链表里，next 成员就指向链表中的下一个事件定时器。
- p：该事件定时器绑定的线程。当定时器到期后，会向这个线程投递一个定时器事件(PROCESS_EVENT_TIMER)。此外，还可以用这个值是否为 NULL，来判断这个事件定时器是否在事件定时器链表中。

# 事件定时器链表
Contiki 维护了一个事件定时器链表 timerlist，这个链表里包含了系统当前所有的事件定时器：
```
static struct etimer *timerlist;
```
此外，内核还维护了另一个全局变量 next_expiration，用于记录该链表中即将到期的定时器还有多久到期：
```
static clock_time_t next_expiration;
```
# 更新 next_expiration
```
static void update_time(void)
{
  clock_time_t tdist;
  clock_time_t now;
  struct etimer *t;

  if (timerlist == NULL) {
    // 如果事件定时器链表为 NULL，返回 0 ，表示没有定时器将到期
    next_expiration = 0;
  } else {
    // 否则，查找事件定时器链表，找到将要到期的定时器，并更新 next_expiration 的值。
    now = clock_time();
    t = timerlist;
    tdist = t->timer.start + t->timer.interval - now;
    for(t = t->next; t != NULL; t = t->next) {
      if(t->timer.start + t->timer.interval - now < tdist) {
	    tdist = t->timer.start + t->timer.interval - now;
      }
    }
    next_expiration = now + tdist;
  }
}
```

# 向定时器链表添加定时器
函数 add_timer() 用于将一个事件定时器添加到事件定时器链表中。
```
static void add_timer(struct etimer *timer)
{
  struct etimer *t;

  etimer_request_poll();

  if(timer->p != PROCESS_NONE) {
    // 如果定时器已经在链表中，查找到该定时器，然后重新绑定线程
    for(t = timerlist; t != NULL; t = t->next) {
      if(t == timer) {
	      /* Timer already on list, bail out. */
        timer->p = PROCESS_CURRENT();
	      update_time();
	      return;
      }
    }
  }

  // 代码走到这里，说明定时器不在链表中，
  // 为定时器绑定当前线程
  timer->p = PROCESS_CURRENT();
  // 将定时器加入到链表的表头
  timer->next = timerlist;
  timerlist = timer;
  update_time();
}
```
在这个函数里面，通过判断定时器所否绑定了线程，来判断定时器是否已经在链表中。

# 事件定时器线程
```
PROCESS_THREAD(etimer_process, ev, data)
{
  struct etimer *t, *u;

  PROCESS_BEGIN();

  timerlist = NULL;

  while(1) {
    PROCESS_YIELD();

    if(ev == PROCESS_EVENT_EXITED) {
        // 有线程将要退出了，它向内核中的所有线程都投递了一个 PROCESS_EVENT_EXITED 事件
        // 以通知所有的线程(如果需要)做清理工作。
        // 当线程退出时，当它向所有线程投递 PROCESS_EVENT_EXITED 事件时，所绑定的 data
        // 指向的该线程自己。
        // 关于线程退出，请参考后续的《线程退出》一节。
        struct process *p = data; // 指向将要退出的线程。

        while(timerlist != NULL && timerlist->p == p) {
          // 先将定时器链表的前面连续的若干个绑定了需要退出线程的定时器从链表中删除
	        timerlist = timerlist->next;
        }

        // 再遍历整个链表，当查找到有定时器所绑定的线程就是需要退出的那个线程时，
        // 将该定时器从链表中删除
        if(timerlist != NULL) {
	         t = timerlist;
	         while(t->next != NULL) {
	            if(t->next->p == p) {
	               t->next = t->next->next;
	            } else
	            t = t->next;
	        }
        }
        continue;
    } else if(ev != PROCESS_EVENT_POLL) {
        continue;
    }

    // 代码走到这里，说明本线程接收到的事件为 PROCESS_EVENT_POLL。
  again:

    u = NULL;

    // 遍历这个链表，查看是否有定时器到期了
    for(t = timerlist; t != NULL; t = t->next) {
      if(timer_expired(&t->timer)) {
         // 如果有定时器到期了，则向该定时器绑定的线程投递一个定时器事件 PROCESS_EVENT_TIMER。
	       if(process_post(t->p, PROCESS_EVENT_TIMER, t) == PROCESS_ERR_OK) {
            // 如果定时器事件投递成功
            // 先解除定时器绑定的线程
	          t->p = PROCESS_NONE;
            // 再将该定时器从链表中删除
	          if(u != NULL) {
	             u->next = t->next;
	          } else {
	             timerlist = t->next;
	          }
	          t->next = NULL;
	          update_time();
	          goto again;
	       } else {
           // 如果定时器事件投递不成功，将本线程(事件定时器线程)设置为高优先级
           // 调度器会优先再次调用本线程遍历链表。
	           etimer_request_poll();
	      }
      }
      // u 表示在链表中到期定时器的前一个定时器
      u = t;
    }

  }

  PROCESS_END();
}
```
可以看出来，事件定时器线程只处理两类事件：PROCESS_EVENT_EXITED 和 PROCESS_EVENT_POLL。如果接收到投递过来的其它事件，直接返回(PROCESS_YIELD() 会保存当前线程的上下文，然后退出当前线程)。

# 事件定时器的 API
## 启动定时器
```
void etimer_set(struct etimer *et, clock_time_t interval)
{
  // 设置定时器的起始时间和等待间隔
  timer_set(&et->timer, interval);
  // 将定时器添加到定时器链表中
  add_timer(et);
}

void timer_set(struct timer *t, clock_time_t interval)
{ // 设置定时器的等待时间
  t->interval = interval;
  // 设置定时器的起始时间
  t->start = clock_time();
}
```
## 重置定时器
当定时器到期一次后，如果希望定时器再次工作，者需要调用 timer_reset() 函数重置寄存器。
```
void timer_reset(struct timer *t)
{
  // 将定时器的起始时间设置为定时器上次到期时的时间
  t->start += t->interval;
}
```
## 重启定时器
timer_restart() 是重新启动一个定时器。请注意它与 timer_reset() 的区别。
```
void timer_restart(struct timer *t)
{
  // 将定时器的起始时间设置为系统当前的时间，定时器的间隔保持不变
  t->start = clock_time();
}
```
## 判断定时器是否到期
```
int timer_expired(struct timer *t)
{
  clock_time_t diff = (clock_time() - t->start) + 1;
  return t->interval < diff;
}
```
## 判断定时器还有多久到期
```
clock_time_t timer_remaining(struct timer *t)
{
  return t->start + t->interval - clock_time();
}
```



