# 失败教训与排障

这些是实际经历，不把先后发生误写成已证明的因果。表中“推测/未确定”保留不确定性。先保留串口与备份，再缩小变量。

| 症状 | 证据与判断 | 最终处理 / 教训 |
| --- | --- | --- |
| 黑屏、长按电源仍不退出 | 曾是9008握手已过期，不是屏幕一定损坏 | 区分USB枚举、CrashDump、EDL；本机强制关机用电源+音量减，不能只重复长按电源 |
| 解锁命令返回成功 | 命令结果本身不证明启动完成 | 启动Android后复查属性、原序列号和Root；保留SELinux Enforcing；临时身份修改必须从本机备份恢复 |
| `fastboot boot` 后反复解锁警告/Logo | Android对照镜像也曾失败；B槽被标不可用、旧A回退校验失败；具体哪一步触发状态改变未完全确定 | 不把它当可靠临时启动。独立检查A/B元数据、回滚版本和真实USB模式，保留已验证槽 |
| 选A后无法进Android | A的旧回滚版本低于已推进版本；B镜像数据尚在 | 先明确选回B恢复，再做匹配版本A修复，不能只复制boot就声称全槽修好了 |
| EDL工具打印OK却无备份 | GPT命令没实际输出文件；SkipWrite=1走NULL存储无法读取 | 检查实际文件、长度、内容、哈希与读回；读操作适配器限制program/erase/patch |
| COM打开后收不到Sahara HELLO | Windows串口打开清理缓存可能丢包；底层重启后端口号会变 | 有界超时、处理分包、复核枚举，不因旧COM名字不见了就继续写入 |
| 按键进入FFBM或CrashDump | 文档、固件和实际菜单不一致 | 不凭组合键猜已进Fastboot，使用实际界面和设备协议确认 |
| mainline DTB加Android DTBO失败 | `FDT_ERR_NOTFOUND` | 两套树不是任意可叠加，使用配套板级DTB；本机清空测试槽DTBO |
| Linux启动文字停住，电脑无USB | `/init`已运行，但configfs配置空、function链接错误导致UDC -22 | 绝对function链接、先配后bind；initramfs还要保留USB控制器所需模块与固件 |
| 诊断画面几分钟后又Logo | 早期probe配置自动返回bootloader | 区分测试看门狗与内核panic；最终正常启动没有这种定时重启 |
| 写大sparse后Windows无法识别 | 描述符请求失败，boot尚未写入 | 菜单Restart bootloader恢复连接，再写剩余项目；避免重复覆盖已完成的userdata |
| GNOME桌面黑屏、卡死、CrashDump | DRM dma_fence/GPU fault，FD610全速路径不稳定 | 改Phosh，先软件绘图，再保守GPU合成，保留故障回退 |
| `LIBGL_ALWAYS_SOFTWARE`设了仍GPU故障 | Xorg glamor等服务仍可能用GPU | 分别检查合成器、Xorg和应用；当时Xorg显式AccelMethod none/ShadowFB才避开部分路径 |
| EGL离屏测试通过仍桌面故障 | 64/512/1024像素离屏绘制成功；Phoc第一次频率变化先PLL失败 | 不能将离屏通过当桌面稳定性，降低频率目标并分别验证真实合成/应用 |
| 触摸能点不能滑，或每段很短 | 原IRQ接触约160ms就断；IRQ处理本身不到1ms | 先输入采样区分“没事件”和“渲染慢”，最终改为带校验的连续FIFO轮询 |
| 兼容鼠标方案把桌面打回login | wlroots `cached_axis_source`断言 | virtual pointer事件顺序错误；修正axis/source，保留源码供复核 |
| 软件输入兼容占用CPU | 非阻塞dispatch空转 | 阻塞等待事件；不要用无休止轮询补输入时序 |
| 新触摸有反应但点位反转 | output旋转叠加原触摸翻转 | 按设备分别设置matrix，新Continuous Touch使用identity |
| 改方向后应用打不开、底边退不出 | 内核已经全部松手，桌面仍持有旧手势/输入状态 | 完整停止输入消费者及桌面，再建会话，避免反复热插拔；黑底栏上划到中部才足够触发overview |
| `debian-pad login:` | greetd的initial_session每个boot只运行一次；也可能桌面崩溃 | 查greetd日志，修复导致退出的原因，再清`/run/greetd.run`重建会话；不是直接刷系统 |
| 给OverviewActive写属性失败 | Phosh该属性只读；总线还可能选错 | 在实际会话总线上用正确接口/按键，不伪造属性成功 |
| 触控模块服务启动卡住 | Before=greetd的服务同步启动After=greetd的回退 | 回退异步`systemctl --no-block`；服务依赖也可能造成“设备卡了” |
| 重启后输入时好时坏 | Himax zero-flash还没完成就抢占IRQ | 等非零固件版本，动态找IRQ，失败回退；不固定等待几秒就假设完成 |
| 启动程序普遍10秒以上 | CPU空闲、可用内存充足；直接启动首帧快，Phosh通知超时 | GTK3保留last touch serial私有库，实测多数程序明显改善 |
| 新GDK缺符号或加载路径猜错 | 原Debian库含Broadway；库文件名为0.2417.32 | 保留三个后端、比较全部导出、不猜文件名、不覆盖系统库 |
| 查user bus看不到桌面服务 | Phosh由dbus-run-session建立另一私有总线 | 用实际进程环境定位；不要由“服务不存在”推断Phosh没有运行 |
| TLS/证书突然失败 | RTC没及时出现，时间回到1970 | 等RTC并恢复最近保存时间，再网络对时，不能关闭TLS校验蒙混过关 |
| 熄屏后触控/USB再也不回来 | 多次深度挂起恢复失败 | 当前禁用深度睡眠；不宣称平板电源管理已完成 |
| 禁用深度挂起后，普通熄屏仍无法滑动解锁 | TDDI面板断电、触控恢复路径不完整；轮询又绕开原IRQ的ESD恢复 | [原地恢复](display-resume.md)：暂停读取、重载已验证的控制器SRAM镜像、保留同一个输入设备 |
| 恢复程序有运行记录，锁屏仍可能失灵 | 首版每次删除/重建输入设备，原生IRQ恢复还存在时序依赖 | 保留input设备，用暂停握手串行化完整zero-flash恢复，并屏蔽原生输入的瞬态事件 |
| 空闲时反复重置触控 | 将所有全零FIFO读取也当故障；首次测试“95%有效帧”阈值错误 | 全零空闲帧不触发故障恢复；亮屏沿恢复一次，持续坏校验另作限速恢复 |
| 密码似乎通过却退回锁屏，ScreenSaver报告未锁 | Phosh `on_lockscreen_unlock`对象引用不匹配，旧monitor/background状态异常 | 清理并重建桌面会话后，以实体电源键、实际密码解锁和打开设置验收；软件关闭wl_output不等于真实熄屏测试，不能把触控计数正常当完整解锁成功 |
| UART内部回环通过，QCA版本查询仍超时 | 第二个唤醒IRQ申请把RX GPIO11从qup3切回普通GPIO；其他三脚mux正常 | 读实际CTL与IRQ调用链，在本机临时驱动中跳过该GPIO唤醒IRQ，之后版本/固件/连接成功，见[完整复盘](bluetooth.md) |
| 固件完成仍DOWN RAW、BlueZ没适配器 | 通用NVM占位地址触发未配置状态，缺public-address | 只读取得自己的persist地址配置当前控制器；不复制其他机器的地址、不改原厂分区 |
| 重新插拔USB仍无法登录 | getty依赖在udev就绪前超时，接口存在但写入超时 | 恢复getty；USB服务启动后重新通告已有tty并非阻塞重试。暖重启验收通过，不冒称冷启动所有原因已根治 |
| 手动RFR试验后出现900E | 无完整panic栈，精确崩溃点未证明 | 停用该模式；Sahara RESET回Linux；公开源码在硬件操作前拒绝退役参数，保留原型/整理版边界 |

## 如何形成下一份有用报告

后续[相机与蓝牙复盘](bluetooth-camera.md)还记录了四类错误：取消控制台配置意外把UART FIFO接收编译为空函数、误用另一SoC时钟编号、用诊断dump表推断实际DMA寄存器布局，以及供电别名空参数引发内核Oops。前面的阴性测试不能追认为有效，失败模块不能当成可用驱动发布。Oops后已普通重启恢复原配置。

记录实际型号/面板、内核release与提交、Mesa/Phoc/Phosh/GTK版本、变更前后渲染路径、是否能通过串口访问、当前槽及复现步骤。优先截取有关的短日志，删去序列号、MAC、SSID、密码、账户、IP和私钥。正常截图或一行 `OKAY` 不足以证明恢复、Root、GPU或触摸稳定。

本仓库不把这台设备的GPT、OEM、persist、账号配置或完整镜像当“通用救砖包”。后续内核的PLL和Himax修复有明确来源，但未在本机刷入，因此和已验证成果分开列出。
