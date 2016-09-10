---
title: Zephyr OS 基础篇： 搭建开发环境 hello-world
date: 2016-07-22 22:20:05
categories: ["Zephyr OS"]
tags: [Zephyr]
---

本文主要讲解如何在 Linux、MacOS、Windows 上搭建 Zephyr OS 的开发环境，以及如何使用QEMU仿真器，如何编译、运行`hello world`程序。

- [搭建开发环境](#)
    - [Linux](#linux)
        - [安装依赖的包](#)
        - [安装 SDK](#-sdk)
    - [Mac OS](#mac-os)
    - [Windows](#windows)
- [下载源码](#)
- [编译 hello-world](#-hello-world)
- [使用 QEMU 仿真](#-qemu-)

<!--more-->

# 搭建开发环境

Zephyr OS 支持如下操作系统：

- Linux
- Mac OS
- Windows 8.1

## Linux
### 安装依赖的包
先将系统更新到最新状态：
```
$ sudo apt-get update
```
再安装依赖的包：
```
$ sudo apt-get install git make gcc gcc-multilib g++ libc6-dev-i386 \
  g++-multilib python3-ply
```
> 如果你的系统是 32 位的，不需要安装 libc6-dev-i386 这个包。


### 安装 SDK
访问 [Zephyr SDK archive](https://nexus.zephyrproject.org/content/repositories/releases/org/zephyrproject/zephyr-sdk/) 下载最新版 SDK 。
> 国外的服务器，有时候慢到吐血，我已经将目前最新版0.8.1上传到百度云了：[https://pan.baidu.com/s/1jHQnOxC](https://pan.baidu.com/s/1jHQnOxC) (提取码as9i)

下载完成后，运行该文件：
```
$ chmod +x zephyr-sdk-0.8.1-i686-setup.run
$ sudo ./zephyr-sdk-0.8.1-i686-setup.run
```
默认会将 SDK 安装到`/opt/zephyr-sdk/`目录下。个人推荐使用默认设置。

导出环境变量到`~/.zephyr`文件：
```
$ cat <<EOF > ~/.zephyr
export ZEPHYR_GCC_VARIANT=zephyr
export ZEPHYR_SDK_INSTALL_DIR=/opt/zephyr-sdk
EOF
```

## Mac OS
## Windows

# 下载源码
Zephyr 的代码托管在 Linux 基金会的 Girret 服务器上，只支持以 git clone 的方式下载源码：

```
$ git clone https://gerrit.zephyrproject.org/r/zephyr zephyr-project
```
# 编译 hello-world
进入 Zephyr 项目目录，先配置环境变量：

```
$ cd zephyr-project
$ source zephyr-env.sh
```
进入 hello-world 目录，编译：
```
$ cd samples/hello_world/microkernel
$ make
```
上面的 make 命令会使用应用程序的 Makefile 文件中定义的默认设置编译 hello_wolrd 例程。你可以 定义环境变量 BOARD 为所支持的其它板子编译应用，例如：`make BOARD=arduino_101`。关于make命令的具体使用方法可以执行`make help`。

# 使用 QEMU 仿真
Zephyr 支持在 x86 和 ARM Cortex-M3 两种架构下使用 qemu 进行仿真。
 
仿真 x86：
```
$ make BOARD=qemu_x86 qemu
```
仿真 ARM Cortex-M3：
```
$ make BOARD=qemu_cortex_m3 ARCH=arm qemu
```

仿真结果：
![这里写图片描述](http://img.blog.csdn.net/20160728222104633)
> 退出仿真界面的方法：先按 CTRL+a，再按 x。




