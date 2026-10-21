# TB128FU 蓝牙修复：接收脚复用、原厂地址与开机恢复

2026-10-21，本机已完成芯片版本读取、固件加载、扫描、用户实际配对/连接，以及正常重启后再次连接。开机约17.38秒蓝牙修复服务完成，配对/信任记录保留。**这不代表自动重连、实际音频播放、所有BLE外设或深度休眠唤醒均已通过。** 相机仍不可用，保持暂停。

适用的是[状态表](status.md)中的 TB128FU/P89990JA1、SM6225、`lenovo,tb128` 和 `6.14.0-rc5-next-20250306-tb128fu+`。不覆盖其他型号或任意更新的内核。

## 1. 真正阻塞通信的是 RX 被唤醒中断改回 GPIO

最初 `qcom_geni_serial` 报 `Invalid line -19`，因为设备树缺少所需串口别名。单设备外部驱动绕过编号，补齐 GPIO8～11 的 qup3 配置、L17/L23 供电后能建立 hci0，却反复在 `0xfc00` 查询超时。内部回环通过，也不能证明外部管脚正常。

只读寄存器快照找到差异：GPIO8/9/10 的 mux=1，GPIO11 却是 mux=0。live DT 的第二个中断正是 TLMM GPIO11 falling edge；它同时是 UART RX。

匹配源码的调用顺序解释了现象：

1. UART 选择 default pinctrl，将 GPIO11 设为 qup3。
2. `dev_pm_set_dedicated_wake_irq()` 申请第二中断。
3. `msm_gpio_irq_reqres()` → `msm_pinmux_request_gpio()` → `msm_pinmux_set_mux()`，把同一脚改回 GPIO 输入。

因此物理 RX 已空闲为高，GENI `SE_GENI_IOS` 的 RX 位仍读为0，出现 break/零字节。临时驱动只跳过此 UART 的专用 GPIO 唤醒中断，保留正常自动 RFR，就获得有效版本响应。GPIO11 CTL 从0变为 `0x4`、mux=1，GENI RX 位变为1。

[单因素对照补丁](../patches/tb128-bt-no-gpio-wake-comparison.patch)针对本实验的外部驱动，不能直接当成适用于所有设备的主线补丁。完整驱动还包含编号、供电、pinctrl和FIFO处理。本机已禁用整机深度休眠；本修复没有实现从深度休眠由蓝牙唤醒。

## 2. 固件成功后仍有 DOWN RAW：缺少本机地址

芯片返回 Product `0x0a`、SoC `0x40020150`、ROM `0x0201`，随后成功加载 `qca/crbtfw21.tlv` 与 `qca/crnv21.bin`。但通用NVM含占位地址，QCA检查后要求提供 public-address。`hciconfig` 显示 DOWN RAW、普通management index列表为空，此时不是再次发生固件传输故障。

`btmgmt --index 0 config` 显示 `missing options: public-address` 后，才使用本机原厂地址配置。原地址来自**自己的 persist 分区**内 `bt_macaddress` 文本；挂载参数为 `ro,noload`，不进行日志回放、不修改该分区、不替换通用NVM。不复制其他设备的地址。

[私有地址读取工具](../tools/read-bluetooth-factory-address.py)只把地址存到目标设备的 `/root/tb128-bluetooth-private/factory-address`（0600），不输出地址。该文件和原persist不得上传GitHub。`btmgmt public-addr`用于当前控制器的初始化配置，不是烧录设备熔丝。

该读取工具是依据本机已通过流程整理的公开版本，只做了离线语法检查；若型号、文件布局或地址格式不同会退出，不会生成“备用”地址。先审阅自己的分区和备份。

## 3. 源码、固件与公布版本的边界

- [完整外部UART源码](../bluetooth/tb128_bt_uart.c)保留 Linux Foundation 版权和 GPL-2.0，基于[固定UART上游文件](https://github.com/dys0re/linux-next/blob/bd4ad8882d7c500cba79db8b35501960febf0f11/drivers/tty/serial/qcom_geni_serial.c)。只允许本板和 `4a8c000`，不注册/接管调试控制台。
- [Kbuild](../bluetooth/Makefile)、[构建工具](../tools/build-bluetooth-module.sh)、[来源/校验记录](../bluetooth/validation.json)。
- 固件来自 Debian [`firmware-atheros 20250410-2`](https://packages.debian.org/trixie/firmware-atheros)，需启用 `non-free-firmware`。[包下载](https://deb.debian.org/debian/pool/non-free-firmware/f/firmware-nonfree/firmware-atheros_20250410-2_all.deb)。本仓库不再分发固件。

| 文件 | 实机 SHA256 |
| --- | --- |
| `qca/crbtfw21.tlv` | `62ce092b55e5d4bd511a637b3d8b5d56bc9fb39b5fa9639ea0a54f161daff144` |
| `qca/crnv21.bin` | `274ac49ab207200629a4324cd9665184fc9339618c0ee78fa978f86bab20cfcd` |
| 已验证原型 `.ko`（不分发） | `90cdd40f1e93dc823ce5039696c7d1cd9ccbe8af7a5cd19021c3d256c620c781` |

**公开源码增加了一项入口保护**：在任何管脚、供电或动态DT操作之前，拒绝 `force_rfr_ready=1` 和 `loopback_test=1` 这两个已退役诊断模式，见[差异](../patches/tb128-bt-publication-guard.patch)。正常 false/false 路径保留。该公开整理版在电脑编译检查，**没有重新安装到平板**；实机验证对象是上述原型，不能把新编译产物伪称为逐字节同一个已验证二进制。

## 4. 构建与人工安装顺序

先备份当前配置，保留已验证USB控制台。构建使用固定 `bd4ad888…` 源码及[记录内核配置](../touch/kernel-release.config)：

```sh
bash tools/build-bluetooth-module.sh /path/to/pinned-kernel /path/to/new-build /path/to/matching/Module.symvers
```

本机历史构建缺完整 `Module.symvers`，在 `MODVERSIONS` 和模块签名均关闭的特定内核上，曾允许 `KBUILD_MODPOST_WARN=1` 并逐项核对目标导出；原型104个外部导出匹配。这只是有限验证，不是稳定ABI承诺。构建工具只在显式 `ALLOW_UNVERIFIED_EXPORT_BUILD=1` 时开放这条路径；不得强制加载不兼容模块。

构建只产生文件，不会连接设备或安装。准备在目标平板验证时，先用[导出检查工具](../tools/check-touch-abi.sh)检查新模块；工具名保留触控历史，但检查内容同样适用于此模块。另需人工核对源码、配置、结构体/API及签名规则。

以下为配置布局，逐项安装并检查，不要把整个 `files/` 递归覆盖到系统：

| 目标 | 来源 |
| --- | --- |
| `/usr/local/lib/tb128-bluetooth/{tb128_bt_uart.ko,undefined-symbols.txt,module.sha256}` | 同一次新构建 `module/` 中的三个文件；不得使用原型哈希代替新产物哈希 |
| `/usr/local/sbin/tb128-bluetooth-start`、`tb128-bluetooth-stop` | [启动](../files/usr/local/sbin/tb128-bluetooth-start)、[停止](../files/usr/local/sbin/tb128-bluetooth-stop)助手，0755 |
| `/etc/systemd/system/tb128-bluetooth.service` | [服务](../files/etc/systemd/system/tb128-bluetooth.service)，0644 |
| `/etc/systemd/system/bluetooth.service.d/20-tb128-transport.conf` | [排序配置](../files/etc/systemd/system/bluetooth.service.d/20-tb128-transport.conf)，0644 |
| `/root/tb128-bluetooth-private/factory-address` | 本机私有地址读取工具生成，0600；不是仓库文件 |

所有助手和模块配置由root拥有，不允许普通用户修改。还需系统的 `bluez`、`kmod`、`python3`、`binutils` 与匹配固件；后台连接检查另用 `python3-dbus`。先人工做一次 `systemctl start tb128-bluetooth.service` 和扫描/配对，再 `systemctl enable tb128-bluetooth.service bluetooth.service`；重启复核后才认为持久化通过。

启动助手每次检查内核release、模块哈希和导出，并确认 hci0 实际属于本UART；仅在需要配置地址时恢复自己的原厂身份。公开助手把原型的固定二进制哈希改为新构建的 `module.sha256`，这是另一项发布整理差异。开机服务使用 Wants/After排序，不把所有桌面服务强制依赖于蓝牙成功。

回退时先停用该服务，再移除本次新增的BlueZ排序drop-in并恢复自己的备份，最后 daemon-reload；已有蓝牙连接会断开。不要删除整个 `/etc/systemd/system/bluetooth.service.d/`，也不要重新锁bootloader。这里无需写boot/dtbo或分区表。

## 5. 失败教训与避免误判

- **FIFO接收被误编译为空函数**：取消控制台Kconfig也取消了 `handle_rx_console`；此前FIFO阴性测试作废。外部驱动保留完整接收函数，同时禁止注册控制台。
- **手动RFR试验导致CrashDump**：修正FIFO后的 `force_rfr_ready=1` 试验紧接着发生900E；没有完整panic栈，确切故障点未证明。入口已停用，公开版也在硬件操作前拒绝此模式。Sahara RESET返回Linux，没有为该次恢复刷分区。
- **EGPIO猜测未成立**：原厂代码会处理所有权位，但本机GPIO8～11的present位都为0；只读核对后排除，没有盲写bit12。
- **暖重启/共享电源不等于完全断电**：解绑Wi-Fi时L9仍有其他消费者；不能称无线芯片全部电源都关闭。完整拔线关机也没修复GPIO11复用问题。
- **有hci0不等于BlueZ可用**：固件成功之后，仍需区分RAW/unconfigured与正常management index，并检查自己的地址。
- **不能只凭 `CONFIG_BT_LE` 名字下结论**：该匹配6.14源码始终编译SMP；此选项主要控制ISO实现及相关接口。之前“未启用就完全没有BLE”的说法过宽，现已纠正。具体BLE外设、LE Audio/ISO仍需独立验证。

## 6. 重启与USB恢复的验收

冷启动曾在约186秒发生模块加载、journald和ttyGS0依赖超时，桌面后来仍正常出现；不能仅凭解锁警告把它当成坏槽。恢复getty后完成了蓝牙修复。

为既有USB gadget服务增加[启动后助手](../files/usr/local/sbin/tb128-usb-console-ready)及[drop-in](../files/etc/systemd/system/tb128-usb-serial.service.d/20-console-ready.conf)：仅在getty未运行时重新通告已有tty给udev，再非阻塞启动getty。不重建gadget、不关闭登录认证。它依赖现有 `tb128-usb-serial.service`，不是独立USB安装包。

随后正常重启中：USB服务约7.34秒完成、getty约14.45秒启动、蓝牙约17.38秒就绪；桌面/触控服务active、Wi-Fi connected、failed units=0，原触控模块哈希一致。A槽active/successful/bootable均为1。一次暖重启通过，不能证明所有冷启动延迟根因已解决。

最后复核原配对/信任记录仍在，向唯一已配对设备重新发起连接后，Connected和ServicesResolved均为true。实际播放音频、录音、耗电、深度休眠唤醒、自动重连和不同硬件批次仍不宣称通过。
