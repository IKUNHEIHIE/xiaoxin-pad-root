# 来源、固定版本与下载

最后整理：2026-10-21。分支和合并请求会变化；优先使用固定提交、保存补丁，并检查 SHA256。这里的“已验证”仅指本机记录中的版本。

## 1. 内核、面板、触摸及固件工具

- 基础项目：[ivoszbg/linux-next，v6.14rc5-khaje](https://github.com/ivoszbg/linux-next/tree/v6.14rc5-khaje)。
- 面板适配项目：[dys0re/linux-next](https://github.com/dys0re/linux-next)。
- [发布版源码提交 1334abd…](https://github.com/dys0re/linux-next/tree/1334abd31ef30a6dfadd57c7fa9b0a3c6217607e)。
- [后续源码提交 bd4ad888…](https://github.com/dys0re/linux-next/tree/bd4ad8882d7c500cba79db8b35501960febf0f11)。
- [该版本适配说明](https://github.com/dys0re/linux-next/blob/bd4ad8882d7c500cba79db8b35501960febf0f11/TB128FU.md)。
- [固定源码压缩包](https://github.com/dys0re/linux-next/archive/bd4ad8882d7c500cba79db8b35501960febf0f11.tar.gz)。
- 同提交的固件工具：[prepare-firmware.py](https://github.com/dys0re/linux-next/blob/bd4ad8882d7c500cba79db8b35501960febf0f11/tools/tb128fu/prepare-firmware.py)、[install-firmware.sh](https://github.com/dys0re/linux-next/blob/bd4ad8882d7c500cba79db8b35501960febf0f11/tools/tb128fu/install-firmware.sh)、[服务配置目录](https://github.com/dys0re/linux-next/tree/bd4ad8882d7c500cba79db8b35501960febf0f11/tools/tb128fu/services)。下载时保留目录结构，不能只取一个安装脚本。
- [原始 Ubuntu boot 发布页](https://github.com/dys0re/linux-next/releases/tag/tb128fu-hx83102-20260908)。
- [上游 boot 镜像直接下载](https://github.com/dys0re/linux-next/releases/download/tb128fu-hx83102-20260908/boot-tb128fu-hx83102-gpu-wifi.img)。
- [上游 SHA256 文件](https://github.com/dys0re/linux-next/releases/download/tb128fu-hx83102-20260908/boot-tb128fu-hx83102-gpu-wifi.img.sha256)。

上游镜像大小 **63418368 bytes**，本机下载 SHA256：

```text
00889e28f9bed168a7aae4e4dbe65b69c8e54aeccdbaae162214894543ee74ae
```

它含 Ubuntu dracut initramfs，不是这里最终使用的小型 Debian initramfs，不能混淆两个镜像。

上游后来两个提交值得研究，但**本机没有刷入验证**：

- [7dd2c179：SM6225 GPU PLL programming](https://github.com/dys0re/linux-next/commit/7dd2c179d6b3fecf9dd6670013fc01fe746b2188)，[补丁下载](https://github.com/dys0re/linux-next/commit/7dd2c179d6b3fecf9dd6670013fc01fe746b2188.patch)。
- [bd4ad888：Himax preserve contacts across empty frames](https://github.com/dys0re/linux-next/commit/bd4ad8882d7c500cba79db8b35501960febf0f11)，[补丁下载](https://github.com/dys0re/linux-next/commit/bd4ad8882d7c500cba79db8b35501960febf0f11.patch)。

它们与本仓库的轮询模块/用户态 GPU 配置是不同方案，不应混称为“已经采用的上游驱动修复”。

## 2. 本仓库新增或整理的修复

| 修复 | 源码 / 配置 |
| --- | --- |
| 连续触控轮询 | [C 源码](touch/tb128_touch_poll.c)、[Kbuild](touch/Makefile)、[内核配置](touch/kernel-release.config)、[构建](tools/build-touch-module.sh) |
| GPU 保守合成、频率目标及自动回退 | [配置目录](files/usr/local)、[说明](docs/fixes.md) |
| 启动早期 USB、根系统检查 | [实际 `/init`](boot/init)、[重打包工具](tools/repack-boot.py) |
| configfs 绝对符号链接 | [差异补丁](patches/usb-configfs-absolute-symlink.patch)、[修正脚本](files/usr/local/sbin/tb128-usb-serial-gadget) |
| GTK3 应用启动通知 | 下面的上游补丁及 [私有库构建工具](tools/build-gtk-library.sh) |

这不是重新发明 Freedreno 或整套硬件内核；上游作者保留各自贡献的归属。

## 3. GTK3 触摸启动 serial 补丁

作者 Guido Günther，上游 [GNOME/gtk MR 5628](https://gitlab.gnome.org/GNOME/gtk/-/merge_requests/5628)，分支 `gtk-3-24`，标题 `gdk/wayland: Track last touch serial on seat`。

- [上游补丁下载](https://gitlab.gnome.org/GNOME/gtk/-/merge_requests/5628.patch)。
- [本仓库保存的确切补丁](patches/gtk3-preserve-touch-serial.patch)。
- 补丁内提交：`5733409d087d8658179d116fed3ed56c1c1965b4`。
- SHA256：`0b4cc0f5306ae18856a9b40e86e7b5c3fffa5eda2ddc736df43d6bbaa2976f25`。

构建基于 Debian `gtk+3.0 3.24.49-3`，包含发行版原有补丁：

| 文件 | 下载 | SHA256 |
| --- | --- | --- |
| orig | [gtk+3.0_3.24.49.orig.tar.xz](https://deb.debian.org/debian/pool/main/g/gtk+3.0/gtk+3.0_3.24.49.orig.tar.xz) | `5ea52c6a28f0e5ecf2e9a3c2facbb30d040b73871fcd5f33cd1317e9018a146e` |
| Debian 补丁 | [gtk+3.0_3.24.49-3.debian.tar.xz](https://deb.debian.org/debian/pool/main/g/gtk+3.0/gtk+3.0_3.24.49-3.debian.tar.xz) | `0d20b6ef612ca462929f0f27ad0e359881938a7e44088687f2ce632a4bc0fcd7` |
| DSC | [gtk+3.0_3.24.49-3.dsc](https://deb.debian.org/debian/pool/main/g/gtk+3.0/gtk+3.0_3.24.49-3.dsc) | `513599dc090f48106d1e2fc4d570c4d6e682e52e0ce6c059ea0218f624d48e22` |

若版本已从镜像移除，可在 [Debian Snapshot](https://snapshot.debian.org/package/gtk%2B3.0/3.24.49-3/) 查找同版本，核对上述哈希，不要把更新版本强行套入旧库包装器。

## 4. 系统与桌面

- [Debian 13 发布信息](https://www.debian.org/releases/trixie/)、[Debian 签名公钥](https://ftp-master.debian.org/keys.html)。
- [Phosh](https://gitlab.gnome.org/World/Phosh/phosh)、[Phoc](https://gitlab.gnome.org/World/Phosh/phoc)。
- [Phosh 0.46.0 原始源码](https://deb.debian.org/debian/pool/main/p/phosh/phosh_0.46.0.orig.tar.xz)。
- [Phosh Debian 补丁](https://deb.debian.org/debian/pool/main/p/phosh/phosh_0.46.0-3+deb13u1.debian.tar.xz)。
- [Phoc 0.46.0 源码](https://deb.debian.org/debian/pool/main/p/phoc/phoc_0.46.0.orig.tar.xz)。
- [wlroots 0.18.2 源码](https://deb.debian.org/debian/pool/main/w/wlroots/wlroots_0.18.2.orig.tar.bz2)。
- [PyWayland](https://github.com/flacjacket/pywayland)：仅旧鼠标兼容方案需要。
- [wlr virtual pointer 协议](https://gitlab.freedesktop.org/wlroots/wlr-protocols/-/blob/master/unstable/wlr-virtual-pointer-unstable-v1.xml)：保留原版权说明。
- [Squeekboard](https://gitlab.gnome.org/World/Phosh/squeekboard)、[greetd](https://sr.ht/~kennylevinsen/greetd/)。

## 5. GPU、启动与恢复工具

- [Mesa Freedreno 官方文档](https://docs.mesa3d.org/drivers/freedreno.html)：`FD_MESA_DEBUG` 的 `sysmem`、`noubwc`、`nolrz` 选项。
- [Adreno 610 CI 社区研究](https://github.com/skblt/freedreno-CI-Adreno610)：背景资料，本机没有用它替换 Mesa 二进制。
- [AOSP mkbootimg](https://android.googlesource.com/platform/system/tools/mkbootimg/)：使用完整源码中的 `mkbootimg.py`、`unpack_bootimg.py`，避免某些发行版包缺少 `gki` 模块。
- [linux-msm/qbootctl](https://github.com/linux-msm/qbootctl)，本机参考提交 [39a6e6d…](https://github.com/linux-msm/qbootctl/tree/39a6e6daaf029fb0a083777679a15ea2c18f72de)。
- [Android A/B 原理](https://source.android.com/docs/core/ota/ab)、[动态分区](https://source.android.com/docs/core/ota/dynamic_partitions)。
- [bkerler/edl](https://github.com/bkerler/edl)：Sahara/Firehose 研究及救援；必须配套本机匹配 programmer。
- [Magisk 官方项目](https://github.com/topjohnwu/Magisk)、[安装说明](https://topjohnwu.github.io/Magisk/install.html)、[本机使用 v30.7](https://github.com/topjohnwu/Magisk/releases/tag/v30.7)。
- [联想按键/强制关机说明](https://iknow.lenovo.com.cn/app/detail/196528)：实际界面与 USB 枚举仍需确认，不把组合键当成跨固件保证。

## 6. 原厂固件及非官方解锁参考

- 社区固件镜像目录：[TB128FU_CN](https://mirrors.lolinet.com/firmware/lenowow/2022/Tab_M10_Plus_3rd_Gen/TB128FU_CN/)。这是第三方镜像，不是本仓库提供的固件。
- 本机匹配包：[TB128FU_CN_OPEN_USER_Q00126_T_ZUI_15.0.619_ST_240531.7z](https://mirrors.lolinet.com/firmware/lenowow/2022/Tab_M10_Plus_3rd_Gen/TB128FU_CN/TB128FU_CN_OPEN_USER_Q00126_T_ZUI_15.0.619_ST_240531.7z)，4167763384 bytes，SHA256 `d82d66f6dfd70250da3b7b79fa84e6d900f2e80c5bd931fb1ebfa6dafa6ec268`。
- 历史解锁讨论：[4PDA 同型号主题](https://4pda.to/forum/index.php?showtopic=1047797&st=640)；发布整理时自动访问返回403，可能需要浏览器或站点访问权限。
- 历史公共签名解锁镜像地址：`http://cdn.zui.lenovomm.com/developer/tabletboot/HAHAHAHA/sn.img`，5386 bytes，SHA256 `fe6785fe49baadd74f221bc135b6d0caff14c68e5de2dc17c00d89609504e294`。该地址为 HTTP；本机做过离线签名校验，不能只凭下载成功认定可信或当前仍可用。

本仓库不托管 proprietary firmware、签名解锁镜像、EDL programmer 或用户分区。解锁历史与恢复限制见 [恢复文档](docs/recovery.md)，不要照抄本机扇区地址到另一台设备。
