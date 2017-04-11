# 实验 - 利用 Zephyr 运行 JavaScript

Zephyr 为何要引入 JavaScript？请参考 [如何加速物联网操作系统开发？Zephyr 项目引入 JavaScript 这样做到的](http://geek.csdn.net/news/detail/133848)。

这里要涉及到另一个开源项目 —— Zephyr.js，地址是：[https://github.com/01org/zephyr.js](https://github.com/01org/zephyr.js)。我们这里只是演示一下如何运行 JavaScript 版的 Hello World。

## 获取源码

Zephyr.js 除了该代码仓库之外，还依赖于其它几个代码仓库，包括 jerryscript、zephyr、ihex、iotivity-constrained，他们都是通过通过 git submodule 进行维护的，所以我们在下载 Zephyr.js 源码的时候也需要是使用 git 下载：

```
$ git clone https://github.com/01org/zephyr.js
```

### 更新依赖仓库

进入刚刚克隆的 zephyr.js 的目录，执行如下命令更新它所依赖的代码仓库：
```
$ cd zephyr.js 
$ source zjs-env.sh
$ make update
```
然后我们会看到在 zephyr.js/deps 目录下增加了几个文件夹，这就是我们获取到的依赖仓库。

## 编译 HelloWorld.js 

Zephyr.js 的例程位于 samples 目录下，我们可以看到该目录下面提供了很多 .js 例程脚本。

我们可以打开 HelloWorld.js，看看该脚本里面有啥内容。里面其实就一句 Javascript 语言：
```
$ cat samples/HelloWorld.js 
console.log('Hello, ZJS world!')
```

它的作用就是向控制台(即我们的串口)输出一条日志信息 'Hello, ZJS world!' 。

在开始编前，还需要执行如下两个命令，以设置编译时需要的环境变量：
```
$ source zjs-env.sh 
$ source deps/zephyr/zephyr-env.sh 
```

然后我们开始编译了。在 zephyr.js 的根目录执行：
```
$ make BOARD=frdm_k64f JS=samples/HelloWorld.js
```

其中，JS=samples/xxxx.js 是用于指定将那个 JS 脚本编写到进行中。

编译完成后，会在相对于 zephyr.js 根目录下的 outdir/frdm_k64f 下生成二进制镜像文件 zephyr.bin。

## 实验现象

将 Zephyr.js 烧写到开发板后，对开发板复位，我们可以在串口上看到如下输出：
```
Hello, ZJS world!
```

## 总结

与普通的 JavaScript 脚本不同的是，Zephyr.js 中的 JS 脚本不是在运行时解释的，而是在编译时解释的，它在编译的时候先将 JS 脚本编译成二进制镜像文件。