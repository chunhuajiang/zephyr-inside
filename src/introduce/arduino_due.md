---
title: Zephyr OS 基础篇： 连接硬件 Arduino Due
date: 2016-07-24 22:00:03
categories: ["Zephyr OS"]
tags: [Zephyr]
---

本文主要介绍如何将 Zephyr 的程序烧写到硬件 Arduino Due 中。
<!--more-->
# 前言
本想着 Zephyr Project 提供了 QEMU 仿真器，因此不需要再买硬件，但后来发现自己错了，因为仿真器实现的功能很少，甚至连 GPIO 都没有。然后到[官网](https://www.zephyrproject.org/doc/1.4.0/board/board.html)查看 Zephyr 支持哪些板子，最终选定了 Arduino Due，原因只有一个，便宜。淘宝 50 大洋。

以 Ubuntu 为例。

# Arduino Due 硬件介绍
<center>![这里写图片描述](http://img.blog.csdn.net/20160730164313047)</center>

从淘宝买回来，一共保护两部分：

- 一块如上图所示的板子。
- 一根 USB 数据线。



简单介绍我们目前需要用到的三个地方：

- Programming Port（编程端口）： Arduino Due保护两个 USB 接口，一个是原生 USB 端口，一个是编程端口。编程端口可用于烧写 Zephyr 程序、给板子供电。
- Reset（复位按钮）：复位。
- Erase（擦除按钮）：擦除 flash 。

# 准备工作：安装 BOSSA

BOSSA 是用来烧写 Zephyr 程序的开源工具，托管在Github　上，支持　ＧＵＩ　和命令行。这里以命令行为例。如果你想使用　ＧＵＩ，请按照该仓库　ＲＥＡＤＭＥ　中的指示进行安装。

从仓库检出 bossa 的源码：
```
$ git clone https://github.com/shumatech/BOSSA.git
$ cd BOSSA
```
bossa的master分支不支持arduino，所以必须切换到arduino分支：
```
$ git checkout arduino
```
编译
```
$ make bin/bossac
```
　　生成的科执行文件位于`bin/bossac`，将其拷贝到系统PATH路径下：
```
$ sudo cp bin/bossac /usr/bin
```
# 烧写程序

先编译好 Zephyr 内核，生成的程序位于`outdir/zephy.bin`：
```
$ cd samples/hello_world/nanokernel
$ make BOARD=arduino_due
```
将 USB 数据线的一端插入笔记本的 USB 口，另一端插入板子的 USB 编程端口，此时两个 LED 灯亮。进入 Ubuntu 系统，执行命令`ls /dev/tty*`可以看到 dev 目录下有一个叫做 ttyACM0 的设备文件。

将 ttyACM0 的波特率改为 1200，否则在后面使用 bossa 烧程序时会报错`No device found on /dev/ttyACM0`。
```
stty -F /dev/ttyACM0 speed 1200 cs8 -cstopb -parenb
```

按下 Erase 按钮，220 ms 后松开。220 ms 很难把握，因此可以按久一点。

按 Reset 按钮，此时板子会复位并进入 SAM-BA bootloader。

使用 bossa 烧写程序：
```
sudo bossac -p ttyACM0 -e -w -v -b outdir/zephyr.bin
```
烧写结果如下图所示：

<center>![这里写图片描述](http://img.blog.csdn.net/20160730164358299)</center>

打开你的串口，选择端口为 /dev/ttyACM0。按 Reset 按钮进行复位，可以看到串口输出的 hello-world。（注意，你需要在串口中将波特率设为 115200，而不是前面烧程序所设的 1200）
<center>![这里写图片描述](http://img.blog.csdn.net/20160730164431299)</center>

> 注意事项：由于串口是独占设备，所以烧写程序的时候需要先关闭串口软件再烧程序。


# 参考资料
- 论坛
http://digistump.com/board/index.php/topic,1297.0/

-  Zephyr OS 官方文档
https://www.zephyrproject.org/doc/1.4.0/board/arduino_due.html

- Arduino Due 官网
https://www.arduino.cc/en/Main/ArduinoBoardDue
