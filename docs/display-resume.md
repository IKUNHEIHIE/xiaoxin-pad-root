# 普通熄屏后的锁屏触控恢复

2026-10-21追加。单指滑动流畅不代表熄屏/亮屏路径已经正确。此前禁用了深度挂起，但普通DRM面板断电仍可让HX83102 TDDI进入另一状态。

## 发现与失败方案

系统仍running、串口可登录、GPU没有新fault，但持续滑动没有输入事件，轮询每秒约50次读取全部校验失败。背光`bl_power=4`，Phoc记录DSI Turning off；亮屏后`bl_power=0`，错误仍持续。

面板unprepare会拉低enable并关闭供电，Himax的fb通知处理却为no-op。轮询关闭了原生IRQ，也绕开原生ESD恢复。最初停轮询、执行`senseonoff,1s`、重载模块，曾恢复触摸；但自动复现时仍失败。这个方案依赖IRQ触发ESD的时序，并且删除/重建input设备可能留下锁屏手势状态，不作为最终恢复方案。

另一个试验将全零帧也计入故障，导致空闲时反复恢复。全零FIFO读取本身不等于硬件故障，自动测试要求“95%有效坐标帧”同样不成立：没有手指时完全可以没有坐标帧。

## 当前方案

- [模块](../touch/tb128_touch_poll.c) 增加root可写`pause`和只读`paused`握手。暂停前报告全部松手，暂停时不读SPI，但不注销`TB128 Continuous Touch`。
- [服务程序](../files/usr/local/sbin/tb128-touch-resume) 检测`bl_power`从关到开，每次亮屏执行一次恢复。显示保持亮着时，正常全零空闲数据不触发恢复；持续坏校验/总线错误才走有限重试。
- 暂时grab原生Himax evdev节点，阻止恢复过程中的原生瞬态事件传给桌面；不记录触摸坐标或按键。
- 请求模块暂停，等`paused=Y`后，通过现有驱动的`HX_ZERO_FLASH`调试接口执行`t,Himax_firmware.bin`，同步把本机已验证的镜像重载到控制器SRAM。
- 源程序严格检查固件SHA256，当前只接受本机测试版本。它不改固件文件，不写控制器非易失flash，不写boot或userdata。
- 结束暂停时，内核先用独立IRQ-disable引用等待在途处理完成，再把原生IRQ状态交还轮询。虚拟设备身份始终不变。

这仍是围绕当前内核的恢复方案，不是已经把上游面板/触控电源联动从根本修好。

## 安装与回退

先按照[构建说明](fixes.md)重编当前模块、核对vermagic和所有导出符号。增加的`disable_irq/enable_irq`在本机发布内核上已逐个核对；完整imports记录见[列表](../touch/undefined-symbols-tested.json)。不要把新服务配到没有`pause/paused`接口的旧模块。

第一次替换模块应停桌面会话并保留USB串口。安装模块到原来的`/usr/local/lib/tb128-input/tb128_touch_poll.ko`，安装服务程序为0755，安装[unit](../files/etc/systemd/system/tb128-touch-resume.service)为0644，重新建立桌面会话，再启用`tb128-touch-resume.service`。平时亮屏不再重启桌面或重载模块。

这是特定backlight名称、Himax节点、固件SHA与内核的组合；换硬件/固件必须重新核查，不能为了通过检查直接删掉哈希约束。服务保留原有密码锁屏，不修改认证设置。

停用恢复服务可执行`systemctl disable --now tb128-touch-resume.service`；模块仍按原方式提供连续输入。若要恢复旧模块，停桌面及恢复服务，停止poll服务，再恢复自己的旧模块和配置，最后重建桌面会话。

## 验证范围

新模块成功载入并核对全部30项imports，三轮软件熄屏/亮屏中输入设备路径始终相同、每轮恰好一次SRAM恢复、稳定采样期坏校验与总线错误均为0。测试时空闲FIFO可以全零，不把它误称为“有效触点”。

随后使用者复核滑动正常；启动服务已启用，试验回退计时器已关闭。此次没有刷写启动分区，也没有为新模块再次进行整机重启。长期挂起、电池续航、多点手势仍未获得新结论。
