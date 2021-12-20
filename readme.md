# Phoenix Transfer (PT中转站): 使用Python透过FB与MC交互

## 概述

Phoenix Transfer, 通过修改 FastBuilder (PhonixBuilder) 的主程序，完成对FB的开孔，让FB通过 socket 中转数据包，使 Python程序可以与服务器通信。

例如： 让 Python 程序接受服务器内聊天信息，和命令执行结果 让 Python 程序直接向服务器发送mc指令，例如setblock

## 当前阶段

可能性验证成功，从python发送m指令，fb机器人执行并将mc指令执行结果返回到python

## 其他说明

刚学 go 语言，写的比较糊

## 使用方式

1. 按照 fb 文件夹下两份go文件的说明修改 fb的源代码并编译
**注意：本项目仅仅实现对fb的开孔，不属于本项目范畴的任务，例如：**   
**解决编译完成后的 版本无效 问题，本项目不会给出任何说明，请自行解决**

2. 你已经就绪了，参考示例代码了解如何 使用Python透过FB与MC交互 吧!