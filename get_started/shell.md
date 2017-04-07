# 实验 - Shell


为了达到人机交互的目的，Zephyr 提供了一个 Shell 例程，位于 `samples/shell` 下面。这个 shell 只提供了最基本的功能，额外的功能需要用户根据自己产品的需求进行添加。添加额外功能的方法非常简单，可以参考 Zephyr 的文档 [Zephyr OS Shell](http://iot-fans.xyz/zephyr/doc/v1.6.0/subsystems/shell.html) 或者直接参考源码中的 shell 例程。

## Shell 的架构

Shell 的架构如下图所示：

```
                 shell
             /           \ 
       module1           moudle2    ... 
       /    \           /   |   \
    cmd1    cmd2      cmd1 cmd2 cmd3   ...
```

整个 shell 子系统由若干个模块(module)组成，而每个模块又由若干过命令组成。用户可以根据自己的需要向 shell 子系统中注册新的模块，并实现这个模块需要完成的命令(具体需要完成哪些命令也由用户决定)。

## 编译&烧写

进入 shell 所在目录：
```
$ cd samples/hello-world 
$ make BOARD=frdm-k64f
```
编译完成后，生成的镜像文件位于`samples/shell/outdir/frdk-k64f/zephyr.bin`，将其烧写到开发板上面。

## 实验现象

烧写完成后，对板子复位。通过串口，我们可以通过 help 命令查看 shell 中支持哪些模块：
```
  shell> help
```
<center><img src="./shell-1.png" /></center>
  
我们可以通过命令 `set_module xxx` 进入 xxx 模块： 
```
  shell> set_module kernel
```
进入 kernel 模块后，命令提示符由 `shell>` 变为了 `kernel>`。此时我们可以再使用 help 命令，查看该模块提供了哪些命令： 
```
  kernel> help 
```
<center><img src="./shell-2.png" /></center>

我们可以使用 `version` 命令查看 Zephyr 的版本，使用 `uptime` 命令查看系统上电后运行了多久(单位是毫秒)等等。
```
  kernel> version
  kernel> uptime
```
<center><img src="./shell-3.png" /></center>
  
## 总结

Zephyr 中的 shell 可以用短小精悍来形容，虽然它提供的模块非常少，但是模块的开发非常方便，而且然还支持 tab 键补全等一些暖心功能。