# 实验 - Hello World

经典的 hello world 来了！ :smile:

> 某程序员退休后决定练习书法，于是重金购买文房四宝。一日，饭后突生雅兴，一番研墨拟纸，并点上上好檀香。定神片刻，泼墨挥毫，郑重地写下一行字：hello world！

在 [搭建开发环境](env.md) 的过程中我们已经编译过 Hello World 了，现在我们正式将它烧写到开发板上。

## 编译&烧写

先执行 source 操作，然后进入 Hello World 代码所在目录进行编译：
```
$ cd samples/hello-world 
$ make BOARD=frdm-k64f 
```
编译完成后，生成的镜像文件位于`samples/hello_world/outdir/frdk-k64f/zephyr.bin`，将其烧写到开发板上面。

## 实验现象

烧写完成后，对板子复位，串口会打印`Hello World! ARM`。

:smile::smile::smile:

## 总结

整个 main 行数里面只有一行打印语句`printk`，我们在后面会单独分析它的源码实现，参考 [驱动篇之 printk]()。





    
