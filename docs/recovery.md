# 恢复、A/B与非官方解锁记录

恢复方法取决于 **userdata 是否还属于 Android**。安装Debian前，Android A/B各自实际启动过；最终userdata已改为ext4 Debian，不能再说“切B就能保留Android双系统”。

## Linux仍可访问：先退用户态改动

通过已验证USB串口登录，先保存有关服务日志：

- GPU异常：`sudo /usr/local/sbin/tb128-gpu-fallback` 恢复软件桌面并重建会话。
- 新轮询输入异常：先停greetd，再停`tb128-touch-poll.service`，确认模块已卸载、原IRQ恢复，按需启旧compat并重建会话。不要同时让两个进程抓取同一物理输入。
- GTK私有库异常：恢复发行版Phosh的desktop入口，重建会话。系统库从未被覆盖。
- 仅出现login：查看greetd退出原因；它的自动登录标记见 [fixes.md](fixes.md)，无需重刷userdata。

正常串口访问必须是可登录服务，不把早期ramdisk的免密紧急shell用于日常系统。修改输入/图形前保持另一条控制通道。

## Android userdata 尚在：B槽恢复曾如何成功

早期Linux/Android内存启动测试后，旧A和被标不可用的B造成循环。A的`vbmeta_system`回滚版本1698796800，低于已工作的B版本1711929600。它们对应不同年代的固件；不能靠盲目降级bootloader解决。B的有效payload仍在。

本机在CrashDump诊断接口触发重启、配合按键进入更底层救援，再经匹配的签名Firehose检查/恢复自己的启动元数据，最后**显式选择B槽**，Android才恢复。只恢复元数据后不选择正确槽，不能认为已经完成。

这不是“出现CrashDump就应该改GPT”的教程。先区分：

| 状态 | 说明 |
| --- | --- |
| 解锁警告 / Lenovo Logo | 不是Fastboot握手成功 |
| Fastboot实际枚举 | 可以读取槽状态、明确选择已知可启动槽；操作前确认userdata阶段 |
| Qualcomm CrashDump / 900E诊断 | 与9008不同；当时通过诊断重启才转到救援路径 |
| EDL / Qualcomm 9008 | Sahara/Firehose，须匹配签名programmer，绝非随便找一个即可 |
| 0000:0002 / 描述符失败 | Windows未取得USB描述符，先恢复物理/引导接口，不能对失踪设备继续刷 |

按键组合在本机不同状态下结果不一；请参考 [联想说明](https://iknow.lenovo.com.cn/app/detail/196528) 并以真实协议为准。未连接时不要不断发送依赖旧COM端口的命令。

## A槽曾经可以修复，但不是只复制boot

Android时期先备份55项分区（含约8GiB的super），再把A的19项静态分区更新到匹配版本，并修复A的逻辑分区启动元数据；当时只改两个元数据块，共8192字节，没有覆盖共享super payload。A、B都经过真实Android启动验证后才继续Linux安装。

本机使用virtual A/B，共享逻辑分区数据与快照关系会影响修复。**本仓库没有提供通用GPT/元数据patch或固定LBA**：将别人的GPT/OEM写进另一台设备会引入容量、身份和校准问题。先取得自己的完整可信备份并核对逻辑映射、回滚索引，再决定该恢复哪些对象。不要只因分区名带`_a`就假定其全部数据独立于B。

`qbootctl`无参数用于读取，`-s`会切换槽，`-m`更新成功标记。这些都可能写启动元数据；只能在实际成功从目标槽稳定启动后更新。不要把“mark successful”当作修好系统。

## userdata 已替换Debian：恢复Android

需要自己的匹配完整Android固件及正确userdata初始化流程，或安装前保留的完整可恢复备份。B槽仍留着固件只是减少部分恢复材料，不包含被删除的Android数据/加密结构。恢复会替换Linux根分区，先另行保存Debian里的个人文件。

不要在自制boot/dtbo/vbmeta组合上重新锁BL。仅在恢复了完整、匹配且实际启动验证的原厂链后，才另外研究厂商要求；本次实验没有执行重新锁定。

## 最初解锁和Root的经验

本机厂商未提供可用官方解锁渠道。历史流程参考公共签名`sn.img`及同型号社区讨论，临时修改与解锁文件匹配的身份字段后解锁，再从**自己的原始OEM备份**恢复原序列号，并验证恢复结果。

这类方法强依赖型号、签名、固件和分区布局。公开下载地址及SHA见 [SOURCES.md](../SOURCES.md)，但地址能下载不等于可信：本机还做过离线签名检查。不发布个人OEM镜像、设备身份或适用于某个LBA的写入脚本；公共签名镜像也不重新托管。

Android Root使用原机boot匹配Magisk v30.7修补，之后在Android中实际验证su，并验证重启。`su`当时在`/debug_ramdisk/su`，不在默认PATH不等于没有Root。曾准备禁用验证的vbmeta镜像，但没有刷入；不要将未执行的尝试写进必需步骤。原生Debian的root账户权限和Android Magisk是两件事。

## EDL读取的特别教训

- `SkipWrite=1`当时会走NULL storage，不可用于真实分区备份。读取环境改为实际存储通路，并在适配器拒绝program/erase/patch，才进行备份。
- 有工具显示GPT成功却没保存文件。必须检查文件存在、实际长度、内容和读回校验，不能以退出码代替备份。
- pySerial打开串口的清理动作曾丢掉Sahara HELLO，握手需要处理分包及合理超时；底层复位后端口消失可以是正常的重枚举。
- 不提供跨机器套用的EDL自动刷写器。救砖需要本机匹配材料，错误底层写入的后果远大于重建一个桌面会话。
