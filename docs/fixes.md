# 最终修复组合

以下配置是实机验证结果的拆分记录。保留纯软件桌面、原输入回退和 USB 串口之后，再一次只改变一个环节。

## 1. 连续触控，而非把丢包误判成 GPU 慢

原 Himax IRQ 路径会把持续滑动拆成约160ms的短接触。15秒采样出现87段接触，每段中位数仅2次更新；IRQ处理本身中位数约835.5µs，证据不支持简单归因于 SPI 带宽不足。

早期的 [鼠标兼容脚本](../files/usr/local/sbin/tb128-touch-compat) 抓取原输入、合并45ms间隔，并通过 Wayland virtual pointer 模拟点击、滚轮与边缘拖动。它使系统可用，但缺少原生连续触摸语义，流畅度和手势有限，现仅作为回退。

最终 [tb128_touch_poll.c](../touch/tb128_touch_poll.c) 使用原驱动已导出的、带串行化的 `himax_bus_read`，关闭原 IRQ 并等待在途处理中断完成，轮询0x30的128字节 FIFO。前56字节校验、byte52点数、坐标与接触宽度按本机协议解析；活动8ms/空闲16ms，坏数据连续100ms释放接触，卸载恢复原中断。没有直接操作另一个 SPI 控制器或引用厂商私有结构体偏移。

一次20秒诊断轮询得到2026次读取、1972个有效点、1970次运动、14次坏校验、0次总线错误；这是一次采样，不是保证的恒定刷新率。

普通熄屏的后续修复见 [display-resume.md](display-resume.md)：当前模块增加`pause/paused`握手，配合亮屏恢复服务保持同一个虚拟输入设备。不要在每次亮屏时卸载/重载模块，也不要将空闲全零FIFO帧当成需要重复重置的故障。

### 构建与导出符号检查

[构建脚本](../tools/build-touch-module.sh) 接受检出到固定提交的干净git工作树，并复制实际 kernel config；若使用SOURCES中的源码压缩包，需要自己验证完整来源并调整这一项来源检查，脚本不会把任意解压目录当可信检出。**相同 vermagic 是必要条件，不能单独证明 ABI 一致。** 本机发布内核和参考源码存在两个后续提交的差别，必须阅读 [版本边界](status.md)。

优先使用实际内核完整构建生成的 `Module.symvers`。历史环境未取得它，`CONFIG_MODVERSIONS` 和模块签名检查关闭，构建临时使用 `KBUILD_MODPOST_WARN=1`；所有最终 undefined imports 又逐个与运行内核的 `__ksymtab_*` 比较，列表保存在 [undefined-symbols-tested.json](../touch/undefined-symbols-tested.json)。**这不是通用的忽略 modpost 错误或强制载入办法。** 新脚本默认拒绝缺失 symvers，只有显式选择历史路径才允许继续；不要使用 `insmod -f`。

安装自己编译并检查的模块到 `/usr/local/lib/tb128-input/tb128_touch_poll.ko`，安装 poll-start/stop 和 service。先准备下述回退依赖，再启用 `tb128-touch-poll.service` 并关闭旧 compat 的自动启动。poll-start 等待 zero-flash 固件显示非零版本，动态查找 `himax_tp` IRQ；不要固定照抄 IRQ120。失败回退以 `--no-block` 启动，避免与 greetd 的顺序依赖形成等待环。

### 方向与桌面重建

Phoc 的 `DSI-1 rotate=180` 会变换正常输入。原厂 Himax 设备另有方向问题，需要翻转矩阵；新 `TB128 Continuous Touch` 必须是**单位矩阵**。两者规则见：

- [原触摸规则](../files/etc/udev/rules.d/90-tb128-touch-orientation.rules)
- [新触摸规则](../files/etc/udev/rules.d/91-tb128-continuous-touch.rules)

叠加两次180°曾导致能点击但位置相反。重载触摸后，内核即使已经报告全部松手，GTK/Phosh仍可能保存旧手势。停止/替换输入时先停止桌面，完成后重建整个会话，避免连续热插拔：

```sh
sudo systemctl stop greetd
# 在此检查/更新自己的输入配置，确认未留下两个竞争的输入消费者
sudo rm -f /run/greetd.run
sudo systemctl start greetd
```

`/run/greetd.run` 是 greetd 的一次自动登录状态文件。仅重启 greetd 而保留它，可能进入 `debian-pad login:`，不代表内核坏了。不要把删除命令换成通配符。

### 旧鼠标回退的依赖

安装 Debian `python3-pywayland`，用 [generate-pointer-bindings.sh](../tools/generate-pointer-bindings.sh) 生成协议到 `/usr/local/lib/tb128-input`。协议 XML 和版权声明保存在 [protocols/](../protocols/wlr-virtual-pointer-unstable-v1.xml)。回退服务里的 UID1000、Wayland socket、显示尺寸均为本机参数，其他账户须修改。

回退 script 的 virtual pointer 必须遵守 Phoc 实现要求的事件顺序：先 `axis` 再 `axis_source`，`axis_stop` 同样附对应 source。错误顺序曾触发 `cached_axis_source` 断言并把桌面打回登录。PyWayland dispatch 改成阻塞等待以免空转吃 CPU。

## 2. GPU 合成与软件应用分开配置

原始 GNOME/Phoc 全速硬件路径会遇到 GPU故障和高通 CrashDump。一次 Phoc 测试先出现 `gpu_cc_pll0 failed to enable`，调用路径涉及频率变化，之后才有 fault/context lost。离屏 EGL 绘制通过不能证明完整桌面稳定。

最终组合：

- `/etc/environment` 保留应用软件绘图：`LIBGL_ALWAYS_SOFTWARE=true`、`GALLIUM_DRIVER=llvmpipe`、`GSK_RENDERER=cairo`。
- [GPU session](../files/usr/local/bin/tb128-phosh-session) 只为 Phoc 清除软件变量，指定 GLES2、msm、DRM card1 和 `FD_MESA_DEBUG=sysmem,noubwc,nolrz`。
- `GNOME_SESSION` 指向 [软件应用包装器](../files/usr/local/bin/tb128-gnome-session-software)，避免应用再次触发激进硬件路径。
- [safe-clock](../files/usr/local/sbin/tb128-gpu-safe-clock) 在 greetd 前设置320MHz最大目标；若检查失败，session 自动选 [Pixman软件会话](../files/usr/local/bin/tb128-phosh-session.software)。运行中 `cur_freq` 曾短暂465MHz，不能把目标上限说成绝对硬锁。
- [guard](../files/usr/local/sbin/tb128-gpu-guard) 监控本次启动的新故障日志，触发 [fallback](../files/usr/local/sbin/tb128-gpu-fallback) 恢复软件会话并重启桌面。它无法在内核已彻底失去响应时保证救回设备。

按实际 `/dev/dri` 对应关系检查，不假定 card1 永远固定。先完成纯软件桌面，之后启用 safe-clock/guard 两个服务，再切换 GPU session。[gpu-egl-probe.py](../diagnostics/gpu-egl-probe.py) 是离屏像素正确性检查，运行时必须已配置保守频率并监视故障；它不是整机稳定性认证，也不是内核 PLL 修补。

发生故障可通过仍可访问的串口运行 `sudo /usr/local/sbin/tb128-gpu-fallback`。完整内核新 PLL 修复尚未在本机验证，单独列于 [SOURCES.md](../SOURCES.md)，不默认启用。

## 3. 应用打开10秒以上：GTK touch serial / startup notification

桌面滑动流畅以后，设置和多数应用仍常等10秒以上。此时 CPU大多空闲，内存仍有约2.5GiB可用；直接启动计算器约0.825秒就有首帧。Phosh app-tracker 的启动通知和触摸 serial 路径指向另一问题，不能继续只降分辨率或调 CPU。

采用 Guido Günther 的 [GTK MR5628](https://gitlab.gnome.org/GNOME/gtk/-/merge_requests/5628)，让 Wayland seat 保存最近的 touch serial，避免手指离开后取到0。补丁作者、完整下载和哈希见 [SOURCES.md](../SOURCES.md)。

[build-gtk-library.sh](../tools/build-gtk-library.sh) 基于 Debian **3.24.49-3** 加原 Debian patches，再加保存的上游补丁；仅构建 GDK。必须包含原库的 X11/Wayland/**Broadway** 后端，历史比较为旧768个导出符号、新768个，缺失0。

在 ARM64 Debian13安装脚本中列出的构建依赖，再运行（不需要 root）：

```sh
bash tools/build-gtk-library.sh /path/to/new-build-directory
```

产物是私有 `libgdk-3.so.0.2417.32`。检查 `ldd -r`、与系统库的导出符号差集，确认没有缺失后才安装到 `/opt/tb128-gtk3-startup/lib/`，创建同目录 `libgdk-3.so.0` 指向该文件。**不覆盖 `/usr/lib` 的发行版库。**

安装 [tb128-phosh-startup-fixed](../files/usr/local/bin/tb128-phosh-startup-fixed) 为0755，并把 [desktop模板](../templates/mobi.phosh.Shell.desktop) 放入桌面用户的 `~/.local/share/applications/mobi.phosh.Shell.desktop`。其 Exec 包装真正的 Phosh 进程。仅在运行时软件包版本仍等于 `3.24.49-3` 时使用私有库；系统更新后包装器自动停用旧库，需要重新评估补丁而非修改版本检查蒙混过关。

停止 greetd、清除它的已登录标记、再启动，建立完整新会话，实测启动速度。Phosh、应用和 portal 在同一个 `dbus-run-session` 私有总线上；排障时读实际 Phosh 进程的总线环境，不要向另一个 `/run/user/1000/bus` 发命令后误判服务不存在。

实测设置1.378秒、计算器1.042秒、时钟0.930秒，用户确认改善；Calendar首次约6秒再开约1秒、Software约5.4秒、Help约5秒。补丁后也有一次设置首次约26.5秒，未完全解释。因此不承诺所有冷启动都在1秒内，也不把 GTK3补丁当成 GTK4全体应用的直接修复。

回退：删去用户的该 desktop 覆盖，或将其 Exec 改回发行版默认，再重建会话。保留私有库文件本身不会替换系统库。

## 4. 时钟、休眠、USB

- RTC曾加载过晚，早期系统时间回到1970导致TLS失败。[clock服务](../files/etc/systemd/system/tb128-clock.service) 保存/恢复最近合理时间，之后仍需网络对时；不把某次安装日期硬编码进系统。
- 深度挂起曾让 USB/触摸无法唤回；本机 mask 了 `suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target`，并关闭桌面空闲睡眠。这会影响续航，不是电源管理已经适配完成。
- USB configfs 必须先有 function、有效绝对链接，再绑定UDC。见 [USB补丁](../patches/usb-configfs-absolute-symlink.patch)。空配置会报 `needs at least one function`、`failed ... -22`。
- `tb128-usb-serial.service` 只建立 ACM设备；正常系统登录还需自己的 `serial-getty@ttyGS0.service`，不要为日常系统部署无认证 root shell。
