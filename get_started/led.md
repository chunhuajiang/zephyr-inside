# 实验 - LED


## 编译&烧写

`samples/basic/`目录下的例程是与 LED、按键等相关的 GPIO 实验，我们只看下最简单的 LED 闪烁实验。进入 blinky 所在目录：
```
$ cd samples/basic/blinky 
$ make BOARD=frdm-k64f
```
编译完成后，生成的镜像文件位于`samples/basic/blinky/outdir/frdk-k64f/zephyr.bin`，将其烧写到开发板上面。

## 现象

将`zephyr.bin`烧写到板子上后，复位，可以看到 LED 灯每秒闪烁一次。

## 总结

LED 实验虽然非常简单，但是我们初次去看代码的话可能会被绕晕，这涉及到 Zephyr 的设备驱动模型。我们在后面驱动篇再详细分析代码，这里仅仅是做下实验，看下现象。

另外，LED 是每个一秒闪烁一次的，它还涉及到内核时钟和定时器，我们在内核篇再详细分析相关代码。