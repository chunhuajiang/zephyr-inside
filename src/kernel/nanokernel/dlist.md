---
title: Zephyr OS 内核篇： 内核链表
date: 2016-08-10 19:34:38
categories: ["Zephyr OS"]
tags: [Zephyr]
---
本文先简单地介绍了一些内联函数的知识，然后再详细分析 Zephyr OS 内核中的链表的源码。

- [内联(inline)函数](#内联inline函数)
- [链表的定义](#链表的定义)
- [链表的初始化](#链表的初始化)
- [判断某节点是否是链表的头节点](#判断某节点是否是链表的头节点)
- [判断某节点是否是链表的尾节点](#判断某节点是否是链表的尾节点)
- [判断链表是否为空](#判断链表是否为空)
- [获取链表头节点](#获取链表头节点)
- [获取节点的下一个节点](#获取节点的下一个节点)
- [在链表尾部插入节点](#在链表尾部插入节点)
- [在链表头部插入节点](#在链表头部插入节点)
- [在某节点后插入节点](#在某节点后插入节点)
- [在某节点前插入节点](#在某节点前插入节点)
- [删除某节点](#删除某节点)
- [取出第一个节点](#取出第一个节点)

<!--more-->

# 内联(inline)函数

在 Zephyr OS 中，实现了一个双链表，其代码位于头文件 inclue/misc/dlist.h 中。

居然将函数实现在头文件中！！再仔细一看，这些函数不是普通的函数，而是内联函数！

为什么？这样有什么好处？在网上搜了一通，总结如下：

- 什么是内联函数：
  - 简单地讲，内联函数就是用关键字 inline 修饰的函数。编译器在编译含有内联函数的文件时，会在调用内联函数的地方将该函数展开，这一点与处理宏的过程类似。但是，在将内联函数展开的时候，编译器会对该内联函数的类型进行检查，比如检查参数、返回值类型等。
- 什么时候使用内联函数：
  - 如果一段代码需要重用，且重用的频率很高，且代码很短，那么推荐使用内联函数。
- 内联函数 vs 宏：
  - 编译器会对内联函数进行类型检查，而对宏只是进行简单的替换。
  - 内联函数在编译时被展开，宏在预编译时被展开
- 内联函数 vs 普通函数：
  - 前面已经说了，内联函数的调用频率高，代码短小，在这种情况下，如果不使用内联函数而使用普通函数，会降低运行效率，因为函数调用有开销，比如参数、返回值、返回地址等的压栈、出栈操作。
- 内联函数的缺点：
  - 增加了编译后的代码的大小。

> 在 Zephyr OS 的源码中，还会看到另外一套链表，位于 net/ip/contiki/os/list.[ch]。这套链表是移植于Contiki，只在ip协议栈中有使用。

# 链表的定义

```
struct _dnode {
	union {
		struct _dnode *head; 
		struct _dnode *next; 
	};
	union {
		struct _dnode *tail; 
		struct _dnode *prev;
	};
};
```

第一眼就蒙了，为什么节点的定义里面居然有两个联合体。直到看到后来，恍惚间想明白了。Zephyr OS 中对该结构体使用 tpyedef 定义了两种类型：

```
typedef struct _dnode sys_dlist_t;
typedef struct _dnode sys_dnode_t;
```

sys_dlist_t 定义了一个双链表，sys_dnode_t 定义了一个节点。在使用 sys_dlist_t 时，使用的是结构体中的 head, tail 两个成员；在使用 sys_dnode_t 时，使用的是结构体中的 next, prev 两个成语。

其实我们可以对上面的代码展开成两个结构体：

``` c
typedef struct _dnode {	// 定义节点
  struct _dnode *next;	// 后继节点
  struct _donde *prev;	// 前驱节点
} sys_dnode_t;

typedef struct _dlist {	//	定义链表
  struct _dlist *head;	//	链表头
  struct _dlist *tail;	//	链表尾
} sys_dlist_t;
```

> 有人可能会被链表和节点两个概念搞晕了，比如曾经的我。我们只需要记住一点，在使用链表的时候，我们都是先定义一个链表，然后往链表里进行添加节点、删除节点、查找节点等操作。比如：
>
> ```
> sys_dlist_t mylist;				// 定义链表
> sys_dlist_init(&mylist);		// 链表初始化
>
> sys_dnode_t mynode1, mynode2;	// 定义节点
> ...	// 对节点初始化
> sys_dlist_append(&mylist, &mynode1);	// 插入节点1
> sys_dlist_append(&mylist, &mynode2);	// 插入节点2
> ```
>
> 

# 链表的初始化

```
static inline void sys_dlist_init(sys_dlist_t *list)
{
	list->head = (sys_dnode_t *)list;
	list->tail = (sys_dnode_t *)list;
}
```

理解了前面所说的东西，再看具体的代码实现，so easy.

进行链表的初始化，此时链表是空的，没有任何节点，所以将 head, tail 两个指针都指向 list 自身。

# 判断某节点是否是链表的头节点

```
static inline int sys_dlist_is_head(sys_dlist_t *list, sys_dnode_t *node)
{
	return list->head == node;
}
```

# 判断某节点是否是链表的尾节点

```
static inline int sys_dlist_is_tail(sys_dlist_t *list, sys_dnode_t *node)
{
	return list->tail == node;
}
```

# 判断链表是否为空

```
static inline int sys_dlist_is_empty(sys_dlist_t *list)
{
	return list->head == list;
}
```

# 获取链表头节点

```
static inline sys_dnode_t *sys_dlist_peek_head(sys_dlist_t *list)
{
	return sys_dlist_is_empty(list) ? NULL : list->head;
}
```

先判断链表是否为空，如果为空，则返回 NULL，否则返回头结点。所以在使用才函数时，需要判断返回值是否为 NULL，再做处理。

# 获取节点的下一个节点

```
static inline sys_dnode_t *sys_dlist_peek_next(sys_dlist_t *list,
					       sys_dnode_t *node)
{
	return node == list->tail ? NULL : node->next;
}
```

先判断传入的节点是不是链表的尾节点，如果是，则返回 NULL，否则返回下一个节点。所以在使用才函数时，需要判断返回值是否为 NULL，再做处理。

# 在链表尾部插入节点

```
static inline void sys_dlist_append(sys_dlist_t *list, sys_dnode_t *node)
{
	node->next = list;
	node->prev = list->tail;

	list->tail->next = node;
	list->tail = node;
}
```

# 在链表头部插入节点

```
static inline void sys_dlist_prepend(sys_dlist_t *list, sys_dnode_t *node)
{
	node->next = list->head;
	node->prev = list;

	list->head->prev = node;
	list->head = node;
}
```

# 在某节点后插入节点

```
static inline void sys_dlist_insert_after(sys_dlist_t *list,
	sys_dnode_t *insert_point, sys_dnode_t *node)
{
	if (!insert_point) {
		sys_dlist_prepend(list, node);
	} else {
		node->next = insert_point->next;
		node->prev = insert_point;
		insert_point->next->prev = node;
		insert_point->next = node;
	}
}
```

# 在某节点前插入节点

```
static inline void sys_dlist_insert_before(sys_dlist_t *list,
	sys_dnode_t *insert_point, sys_dnode_t *node)
{
	if (!insert_point) {
		sys_dlist_append(list, node);
	} else {
		node->prev = insert_point->prev;
		node->next = insert_point;
		insert_point->prev->next = node;
		insert_point->prev = node;
	}
}
```

# 删除某节点

```
static inline void sys_dlist_remove(sys_dnode_t *node)
{
	node->prev->next = node->next;
	node->next->prev = node->prev;
}
```

# 取出第一个节点

```
static inline sys_dnode_t *sys_dlist_get(sys_dlist_t *list)
{
	sys_dnode_t *node;

	if (sys_dlist_is_empty(list)) {
		return NULL;
	}

	node = list->head;
	sys_dlist_remove(node);
	return node;
}
```

取出头节点后将其重链表中删除。


