# 小新 Pad / Lenovo TB128FU：Debian 13 原生适配记录

把一台 **TB128FU（Snapdragon 680 / SM6225、Adreno 610、BOE HX83102P、Himax HX83102E）** 从 Android 改为原生 ARM64 Debian 13，并逐步解决触摸失灵、滑动断续、GPU 故障、启动应用等待等问题的实验记录。

最终使用 **Phosh + Phoc**。最初尝试的 GNOME Shell 出现 GPU 卡死、黑屏和触控问题，没有把它作为最终可用桌面。

**这是一台特定硬件版本的实验成果，不是所有“小新 Pad”的通刷包。** TB125FU 等其他 SoC/面板版本不适用。此仓库提供源码、配置、构建方法及复盘；不分发带个人账户的系统镜像、原厂固件或他人的分区备份。

## 从这里开始

1. [适配状态与版本边界](docs/status.md)：先核对型号、面板及内核来源。
2. [来源、下载链接与校验值](SOURCES.md)：固定上游版本，区分发布镜像与后来提交。
3. [安装与构建流程](docs/install.md)：准备自己的固件、rootfs、启动镜像及恢复材料。
4. [触控、GPU、慢启动修复](docs/fixes.md)：先理解问题，再按顺序应用配置。
5. [失败教训与排障表](docs/failures.md)：包括 Fastboot 循环、CrashDump、登录提示和坐标错位。
6. [恢复与回退](docs/recovery.md)：区分 Android 尚在、userdata 已替换和 Linux 仍可访问三种情况。

## 已达到的状态

| 项目 | 本机结果 |
| --- | --- |
| 原生 Debian 13 ARM64 | 可从 userdata 启动；不是 chroot / proot |
| Phosh 桌面、中文及屏幕键盘 | 已实际使用 |
| 点击、单指连续滑动、底边返回 | 用户确认正常，设置页滑动明显流畅 |
| 熄屏与密码解锁 | 保留同一输入设备、亮屏恢复触控SRAM；清理失配锁屏会话后，用户完成实体电源键、密码解锁及打开设置验证，见[复盘](docs/display-resume.md) |
| Wi-Fi | 实际连接、DNS、HTTPS 均已验证 |
| GPU | Freedreno FD610 / GLES2 桌面合成；应用自身仍保留软件绘图 |
| 应用启动 | 修复启动通知后，设置约 1.4 秒、计算器约 1 秒；并非所有首次启动都这么快 |
| 开机与重启 | GPU/触控配置完成正常重启验证；随后应用启动补丁完成桌面会话重启及实测 |
| 深度休眠 | 暂时禁用，曾导致触摸及 USB 无法恢复 |
| 声音、摄像头、蓝牙、传感器 | 未完成验证，不宣称可用 |
| Android 双系统 | **没有**：共享 userdata 已被 Debian 替换；B 槽留有固件不等于 Android 可直接使用 |

记录时间：2026-10-18 至 2026-10-21。长期续航、充电、热管理、挂起恢复、多点手势及不同硬件批次仍需后续验证。

## 本仓库有什么

- `touch/`：可卸载的连续触控轮询模块源码、实际内核配置和导入符号记录。它绕开了异常的 IRQ 接触上报，**尚未从根本修复中断路径**。
- `patches/`：GTK3 触摸启动 serial 上游补丁、USB configfs 修正。
- `files/`：实际验证过的桌面、GPU 保护、触控启动和时钟配置；USB gadget helper 为注明的发布整理版，实测早期控制台保留在 `/init`。不是自动覆盖整个 `/etc` 的安装包。
- `boot/`：从实际启动的 Debian boot 中取回的 `/init` 与返回引导程序辅助源码。
- `tools/`：整理后的构建、检查及回退辅助工具。
- `diagnostics/`：GPU 离屏绘制检查与经过整理的测量数据。

**先建立可用的 USB 控制台，再调桌面和 GPU。** 不要只凭 `OKAY`、DRM 节点或一张截图判断成功。未经验证不要重新锁定 bootloader。

## 仓库校验

下载源码后，可运行 `python3 tools/verify-publication.py` 检查文件SHA256、本地文档链接、Python语法、JSON和保存的GTK补丁哈希。整理时还检查了17个shell文件语法、返回bootloader辅助程序的ARM64 C语法，并在电脑上完成boot重打包与反解payload核对。这些检查不代替另一台设备的硬件验证。运行检查需要Python3.10或更新版本。

## 致谢与授权

硬件内核与面板/固件适配主要来自 [dys0re/linux-next](https://github.com/dys0re/linux-next) 及其基础 [ivoszbg/linux-next](https://github.com/ivoszbg/linux-next)。GPU 来自 Linux DRM/MSM 与 Mesa Freedreno，桌面来自 Phosh/Phoc，慢启动修复来自 GTK 上游贡献者。详细归属见 [SOURCES.md](SOURCES.md) 和 [THIRD_PARTY.md](THIRD_PARTY.md)。

原始文档与辅助脚本按 [MIT](LICENSE) 分享；内核模块保留 GPL-2.0，GTK 补丁遵循 GTK 的 LGPL 授权。上游源码、二进制与固件不因本仓库而改变许可。

## English overview

An experimental **native Debian 13 / Phosh porting log for the Lenovo TB128FU, SM6225 / Snapdragon 680, Adreno 610, BOE HX83102P panel and Himax HX83102E SPI touchscreen**.

The repository documents reproducible sources and configuration, including fragmented touch contacts, an out-of-tree polling workaround, double rotation, GPU PLL failures, software rendering fallbacks, broken suspend, A/B rollback recovery, and GTK3 touch-serial startup notification delays. It contains no personalized rootfs, device partition dumps or proprietary firmware.

The tested release kernel and the later source reference are different revisions; consult [SOURCES.md](SOURCES.md). GPU composition works under conservative settings, while applications retain software rendering. Single-finger interaction and Wi-Fi were tested; broad hardware support and long-term stability are not claimed. Please read the status, failure history and recovery notes before flashing anything.
