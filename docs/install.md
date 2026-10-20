# 安装与重建

这是一次成功安装的可审查重建路线，面向能检查 Android 分区、Linux boot/initramfs 和串口的人。仓库不是一键刷机工具。`tools/` 是根据实测命令整理的便携版本，做过静态检查；boot重打包工具另在电脑上完成生成与反解payload比较。没有用整理后的脚本再次重刷整机。实际使用的服务、模块源码和 `/init` 单独保留。

## 0. 先确定自己能恢复

核对 [硬件/版本](status.md)，保存本机 GPT、A/B 状态、原 boot/dtbo/vbmeta、原厂固件、固件 programmer 和需要保留的数据。备份应能读回、核对大小和哈希，不能只看到工具打印 `OK`。保持一个已实际启动过的 Android 槽可用于前期恢复。

本机 bootloader 已解锁。解锁、Root 是独立阶段；原生 Linux 不要求先给 Android 安装 Magisk。非官方解锁与 A/B 救援的历史见 [recovery.md](recovery.md)。不要重新锁定运行自制镜像的设备。

本机验证中 **`fastboot boot` 没有提供可靠的“临时、不改变状态”的测试**，曾进入循环并改变可用槽状态。不要用它作为此型号的默认试跑方法。前期在明确备份后使用专用测试槽，保留可恢复槽，分开验证内核/USB和根系统；实际设备的风险仍需自己承担。

## 1. 固定输入版本

下载链接、提交与哈希见 [SOURCES.md](../SOURCES.md)、[downloads.json](../sources/downloads.json)。

- 测试内核来自上游 `tb128fu-hx83102-20260908` 发布镜像。用它解出的 kernel、dtb、对应模块作为一组。
- 该镜像自带 Ubuntu dracut ramdisk，不能直接当 Debian 安装器。最终改成 [boot/init](../boot/init) 的小型 ramdisk。
- 后来的源码包含 GPU PLL/Himax 两个改变，本机没有刷入验证；重编完整内核应建立自己的新测试基线，不能直接沿用这里的成功结论。
- 轮询模块曾用后续固定源树编译，再逐个核对发布内核导出符号。详情见 [fixes.md](fixes.md)。

在 Linux / WSL 构建环境准备 Python3、git、cpio、gzip、device-tree-compiler、AOSP mkbootimg 完整源码、交叉编译器及 ext4/Android sparse 工具。涉及设备写入的 Fastboot 在能稳定枚举设备的宿主环境操作。

## 2. 建立 ARM64 Debian rootfs

在独立 Linux 构建目录使用 `debootstrap` 建立 `trixie arm64`，使用 Debian archive keyring 验证软件包。跨架构需要 QEMU user/binfmt 与第二阶段引导；也可在原生 ARM64 Linux 构建。不要对宿主系统目录执行 chroot 配置命令。

示意（在已配置 ARM64 binfmt 的构建机上）：

```sh
sudo debootstrap --arch=arm64 trixie rootfs https://deb.debian.org/debian
```

在 rootfs 中配置 `main contrib non-free-firmware` 软件源，安装 Phosh、Phoc、greetd、Squeekboard、NetworkManager、wpasupplicant、dbus-user-session、kmod、sudo、locales、fonts-noto-cjk，以及自己的必要应用。QRTR 无线固件服务用到 `qrtr-tools`、`rmtfs`、`tqftpserv`；软件包命名和可用性以当前 Debian 为准。旧鼠标回退另需 `python3-pywayland`。

创建自己的 `tablet` 账户和密码；若换用户名，修改 greetd 的 `initial_session.user`。加入 input/video/render 等实际需要的设备访问组，使用正常 PAM/logind 会话。仓库没有固定登录密码。回退服务暂按 UID1000 的 `/run/user/1000` 配置，UID 不同需要同步修改。不要发布 `/etc/shadow`、SSH 主机私钥或 NetworkManager 的连接文件。

## 3. 固件、内核模块与无线

使用自己匹配版本的原厂 `NON-HLOS.bin`、vendor 固件和上游固定版本的固件准备说明。参考 [上游 TB128FU.md](https://github.com/dys0re/linux-next/blob/bd4ad8882d7c500cba79db8b35501960febf0f11/TB128FU.md) 及同提交的固件工具：

- modem/adsp/cdsp 等 Qualcomm 分段固件与匹配的 MDT 必须配套；不能拼接其他机型。
- 需要 Himax zero-flash 的 `Himax_firmware.bin`，以及本机 GPU 所需 `a630_sqe.fw`、`a610_zap.*` 等。文件名与实际驱动请求一致，不按 GPU 商品名猜文件名。
- WCN3990 的 Wi-Fi 固件和 board data 需要正确路径；Debian 的 `firmware-atheros` 可提供通用部分，但不能替代全部设备专属内容。
- 本机原厂 FAT 镜像曾存在截断/声明长度不一致；只对副本补齐解析，不修改原始备份。
- 本机 rmtfs 使用只读分区模式 `-r -P -s`；不要让重建无线服务写错设备的持久分区。

上游安装脚本将固件复制到离线rootfs、安装rmtfs/tqftpserv服务覆盖并启用二者。保留其`services/`目录，先检查目标rootfs，再运行；[工具链接](../SOURCES.md)固定到相同提交。不要只复制固件而漏掉服务配置。

把同一个内核的模块放入 rootfs 的 `/lib/modules/6.14.0-rc5-next-20250306-tb128fu+` 并生成依赖。`boot/init` 还需要对应的 `qcom-pon.ko`、`spi-geni-qcom.ko` 在 ramdisk。模块混用可能让显示正常但触摸、电源或 USB 不工作。

## 4. 配置根系统，再做小型启动 ramdisk

先阅读 [fixes.md](fixes.md)，选择纯软件桌面起步，确认 USB 与输入后再启用保守 GPU 合成。`files/` 按根路径组织，但不是可直接整目录覆盖的发行包；逐项合并已有系统配置，特别是 `environment`、`fstab` 和 greetd。脚本装为0755，配置为0644。建立root所有的 `/var/lib/tb128`、`/usr/local/lib/tb128-input`，供时钟保存、GPU回退标记和触摸模块使用。首次没有保存时间时依靠RTC/网络对时。

ramdisk 最少包含：

```text
/init                         本仓库 boot/init，可执行
/bin/busybox                  静态 ARM64，支持 mount/blkid/switch_root/insmod
/sbin/reboot-bootloader        boot/reboot-bootloader.c 静态 ARM64 编译产物
/lib/modules/qcom-pon.ko       匹配发布内核
/lib/modules/spi-geni-qcom.ko  匹配发布内核
/lib/firmware/...             启动早期驱动请求的本机固件
/dev /proc /sys /run /newroot /bin /sbin
```

最终 `/init` 仅接受本机 `/dev/sda18`、ext4 label `debian13-pad` 和 Debian13；其他布局先修改并审查代码。它创建 USB ACM，失败时提供紧急 root 控制台，并在约180秒后返回 bootloader。**这条紧急 USB 控制台没有认证，只用于受自己控制的诊断连接。** 正常 switch_root 后使用正常登录的串口 getty，不保留免密 shell。

离线rootfs至少启用 `NetworkManager.service`、`tb128-usb-serial.service`、`serial-getty@ttyGS0.service`、`tb128-clock.service` 和 `greetd.service`，并选 `graphical.target`。使用greetd作为唯一display-manager，停用GDM等竞争的登录器；这类操作应在自己的rootfs内执行，不能误作用于构建机。在已有可用软件桌面上，准备触控模块和回退依赖后启用poll、停用compat自动启动；最后才启用safe-clock/guard并选择GPU session，具体见修复文档。默认仓库session是最终GPU版本，初期需明确换成`.software`。

重打包工具保留本机原 Android boot 的头参数，用发布镜像中的 kernel/dtb 替换 payload，再使用自建 ramdisk，移除 dtb 中旧根系统启动参数：

```sh
python3 tools/repack-boot.py \
  --reference-android /path/to/own-original-boot.img \
  --upstream-boot /path/to/verified-upstream-boot.img \
  --ramdisk-directory /path/to/minimal-ramdisk \
  --aosp-tools /path/to/aosp-mkbootimg \
  --output /path/to/boot-debian13.img
```

该工具仅生成并反解验证文件，不连接设备、不刷写。它已在电脑上用本机材料运行并核对kernel、dtb、ramdisk三个payload；没有为此再次刷设备。原厂 Android DTBO 不适合叠加到这一套 mainline DTB：曾报 `FDT_ERR_NOTFOUND`。本机最终对应的 A 槽 dtbo 清空；这不是适用于所有设备的通用操作。

## 5. 制作 ext4 镜像与写入边界

在构建机创建容量小于 userdata 的 ext4 镜像，4KiB block、label `debian13-pad`，留够系统/应用空间。本机初始镜像12GiB，安装后扩展到实际分区约103GiB。示意：

```sh
truncate -s 12G debian-rootfs.ext4
sudo mkfs.ext4 -F -b 4096 -m 0 -L debian13-pad \
  -E lazy_itable_init=0,lazy_journal_init=0 -d rootfs debian-rootfs.ext4
e2fsck -fn debian-rootfs.ext4
img2simg debian-rootfs.ext4 debian-rootfs.sparse.img
simg2img debian-rootfs.sparse.img roundtrip.ext4
cmp debian-rootfs.ext4 roundtrip.ext4
```

这些命令针对构建文件；不要把输出路径写成电脑或平板的块设备。

**写 userdata 会删除 Android 数据和原有加密文件系统；B 槽固件仍在也无法构成可用 Android 双系统。** 只有完成备份、确认设备型号/分区大小/镜像校验，并决定接受替换 Android 后，才进入设备写入阶段。

本机最终写入对象为 `userdata`、`boot_a`、`dtbo_a`，并显式选择 A 槽。不要复制别人的序列号或 GPT 扇区地址。为避免跳过检查，这里不提供连在一起的自动刷写命令。应逐项观察真实 Fastboot 枚举与每个结果；大 sparse 传输后 USB 描述符曾失效，通过菜单 Restart bootloader 恢复后才完成剩余启动镜像操作。**不要因 USB 临时失败就重复覆盖 userdata。**

## 6. 首次启动验收

先通过 USB 串口确认进入预期根系统，并运行 [只读检查](../tools/check-device.sh)：

1. Debian13、`uname -r`、dt compatible 与预期一致，根分区标签正确。
2. 触摸固件已经加载，初始软件桌面可使用；应用连续触控修复后再测试点击、松手、滑动、返回。
3. 无线连接、DNS/HTTPS实际可用；无线密码仅在自己的设备输入。
4. 最后启用保守 GPU 合成、观察故障日志并保留软件回退。
5. 正常重启后重新确认内核、rootfs、触摸及无线。只有实际从当前槽稳定启动之后，才考虑更新其 boot-successful 状态。

不要把应用窗口能打开当成相机/麦克风已适配。当前不建议启用深度休眠。恢复与退出本实验的方式见 [recovery.md](recovery.md)。
