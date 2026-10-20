#define _GNU_SOURCE
#include <linux/reboot.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <stdio.h>
int main(void) {
    /* The matching qcom-pon module records mode-bootloader=2 in the PMIC.
       No partition writes are performed by this helper. */
    sync();
    if (syscall(SYS_reboot, LINUX_REBOOT_MAGIC1, LINUX_REBOOT_MAGIC2,
                LINUX_REBOOT_CMD_RESTART2, "bootloader") < 0) {
        perror("reboot bootloader");
        return 1;
    }
    return 0;
}
