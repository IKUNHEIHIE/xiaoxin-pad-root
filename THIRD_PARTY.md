# Attribution and license boundaries

The top-level MIT license covers original project documentation and original userspace helpers. It does not relicense upstream code, patches, firmware, or generated protocol bindings.

| Material | Origin / credit | License / treatment |
| --- | --- | --- |
| `touch/tb128_touch_poll.c`, Kbuild | Original workaround for this experiment; calls existing Himax exported API | GPL-2.0-only; [text](LICENSES/GPL-2.0-only.txt). Existing `GPL-2.0` SPDX spelling is retained from the tested source |
| `bluetooth/tb128_bt_uart.c`, UART comparison/guard patches | Derived from Linux Foundation GENI UART driver in pinned dys0re/linux-next; original copyright retained, plus this board-specific experimental adaptation | GPL-2.0; original `GPL-2.0` SPDX and GPL module notice retained. [Source and tested/publication differences](docs/bluetooth.md) |
| Kernel config and imported-symbol list | Running upstream Linux release / tested module build | Linux kernel context, GPL-2.0; upstream component notices still apply |
| `patches/gtk3-preserve-touch-serial.patch` | Guido Günther, GNOME/gtk MR5628; original author and commit header retained | GTK3 GDK, LGPL-2.1-or-later; [text](LICENSES/LGPL-2.1-or-later.txt). Source URLs and matching Debian source checksums in [SOURCES.md](SOURCES.md) |
| `protocols/wlr-virtual-pointer-unstable-v1.xml` | Josef Gajdusek, wlr-protocols | MIT notice embedded in the XML, preserved verbatim |
| `tb128-usb-serial-gadget` | Original publication rewrite of the documented configfs operations; not re-tested on device | MIT. The historical one-line fix to the upstream ramdisk helper is kept separately as a diff, not as a redistribution of the full upstream helper |
| Desktop entry template | Derived from the installed Phosh desktop-entry fields | Phosh project, GPL-3.0-or-later context; [text](LICENSES/GPL-3.0-or-later.txt) |
| Linux hardware support | dys0re/linux-next, based on ivoszbg/linux-next and Linux DRM/MSM/Himax contributors | Kernel licenses, upstream source/commit links retained; no complete kernel binary distributed here |
| Mesa / Freedreno | Mesa contributors | Upstream licenses; only configuration and a diagnostic script included here |
| Firmware, signed unlock image, programmer | Lenovo / Qualcomm / firmware vendors | Not redistributed; links only. Obtain matching files and respect their terms |

The released ramdisk did not supply a separate license notice for its userspace gadget helper. We therefore link the upstream image, retain the narrow historical diff, and provide our own helper implementation. The actual tested early `/init` remains in `boot/init`. The publication rewrite is explicitly distinguished from the tested script.

No ownership is claimed over upstream driver development. The two newer upstream GPU PLL/Himax changes are linked separately because they were not flashed in the tested setup. Contributions should preserve this distinction and all author notices.
