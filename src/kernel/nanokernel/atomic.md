---
title: Zephys OS nano内核篇：原子操作
date: 2016-09-01 17:10:12
categories: ["Zephyr OS"]
tags: [Zephyr]
---

Zephyr OS 在软件层面提供了一套原子操作相关接口。其实现函数很简单，在操作原子变量前先屏蔽中断，操作完原子变量后再是使能中断。

- [类型定义](#类型定义)
- [atomic_cas](#atomic_cas)
- [atomic_add](#atomic_add)
- [atomic_sub](#atomic_sub)
- [atomic_inc](#atomic_inc)
- [atomic_dec](#atomic_dec)
- [atomic_get](#atomic_get)
- [atomic_set](#atomic_set)
- [atomic_clear](#atomic_clear)
- [atomic_or](#atomic_or)
- [atomic_xor](#atomic_xor)
- [atomic_and](#atomic_and)
- [atomic_nand](#atomic_nand)

<!--more-->
# 类型定义
定义了两种类型，分表表示原子操作的变量和该变量的值：
```
typedef int atomic_t;
typedef atomic_t atomic_val_t;
```
# atomic_cas
```
FUNC_NO_FP int atomic_cas(atomic_t *target, atomic_val_t old_value,
			  atomic_val_t new_value)
{
	unsigned int key;
	int ret = 0;

	key = irq_lock();

	if (*target == old_value) {
		*target = new_value;
		ret = 1;
	}

	irq_unlock(key);

	return ret;
}
```
比较并设置compare-and-set：测试原子变量 target 的值是否等于 old_value，如果相等，则将其值修改为新值 new_value，并返回 1;如果不相等，则直接返回 0。
# atomic_add
```
FUNC_NO_FP atomic_val_t atomic_add(atomic_t *target, atomic_val_t value)
{
	unsigned int key;
	atomic_val_t ret;

	key = irq_lock();

	ret = *target;
	*target += value;

	irq_unlock(key);

	return ret;
}
```
将原子变量 target 的值增加 value，并返回 target 的原始值。
# atomic_sub
```
FUNC_NO_FP atomic_val_t atomic_sub(atomic_t *target, atomic_val_t value)
{
	unsigned int key;
	atomic_val_t ret;

	key = irq_lock();

	ret = *target;
	*target -= value;

	irq_unlock(key);

	return ret;
}
```
将原子变量 target 的值减小 value，并返回 target 的原始值。
# atomic_inc
```
FUNC_NO_FP atomic_val_t atomic_inc(atomic_t *target)
{
	unsigned int key;
	atomic_val_t ret;

	key = irq_lock();

	ret = *target;
	(*target)++;

	irq_unlock(key);

	return ret;
}
```
将原子变量 target 的值自增 1，并返回 target 的原始值。
# atomic_dec
```
FUNC_NO_FP atomic_val_t atomic_dec(atomic_t *target)
{
	unsigned int key;
	atomic_val_t ret;

	key = irq_lock();

	ret = *target;
	(*target)--;

	irq_unlock(key);

	return ret;
}
```
将原子变量 targe 的值自减 1，并返回 target 的原始值。
# atomic_get
```
FUNC_NO_FP atomic_val_t atomic_get(const atomic_t *target)
{
	return *target;
}
```
获取原子变量 target 的值。

# atomic_set
```
FUNC_NO_FP atomic_val_t atomic_set(atomic_t *target, atomic_val_t value)
{
	unsigned int key;
	atomic_val_t ret;

	key = irq_lock();

	ret = *target;
	*target = value;

	irq_unlock(key);

	return ret;
}

```
设置原子变量 target 的值为新值 value，并返回 target 的原始值。

# atomic_clear
```
FUNC_NO_FP atomic_val_t atomic_clear(atomic_t *target)
{
	unsigned int key;
	atomic_val_t ret;

	key = irq_lock();

	ret = *target;
	*target = 0;

	irq_unlock(key);

	return ret;
}
```
将原子变量 target 的值清零，并返回 target 的原始值。
# atomic_or
```
FUNC_NO_FP atomic_val_t atomic_or(atomic_t *target, atomic_val_t value)
{
	unsigned int key;
	atomic_val_t ret;

	key = irq_lock();

	ret = *target;
	*target |= value;

	irq_unlock(key);

	return ret;
}
```
将原子变量 target 与值 value 进行按位或操作，并返回 target 的原始值。
# atomic_xor
```
FUNC_NO_FP atomic_val_t atomic_xor(atomic_t *target, atomic_val_t value)
{
	unsigned int key;
	atomic_val_t ret;

	key = irq_lock();

	ret = *target;
	*target ^= value;

	irq_unlock(key);

	return ret;
}
```
将原子变量 target 与值 value 进行按位异或操作，并返回 target 的原始值。
# atomic_and
```
FUNC_NO_FP atomic_val_t atomic_and(atomic_t *target, atomic_val_t value)
{
	unsigned int key;
	atomic_val_t ret;

	key = irq_lock();

	ret = *target;
	*target &= value;

	irq_unlock(key);

	return ret;
}
```
将原子变量 target 与值 value 进行按位与操作，并返回 target 的原始值。
# atomic_nand
```
FUNC_NO_FP atomic_val_t atomic_nand(atomic_t *target, atomic_val_t value)
{
	unsigned int key;
	atomic_val_t ret;

	key = irq_lock();

	ret = *target;
	*target = ~(*target & value);

	irq_unlock(key);

	return ret;
}

```
将原子变量 target 与值进行按照与操作，再按位取反操作，并返回 target 的原始值。



