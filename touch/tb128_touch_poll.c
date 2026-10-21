// SPDX-License-Identifier: GPL-2.0
/* HX83102E continuous input through the existing driver's serialized SPI bus. */
#include <linux/delay.h>
#include <linux/input.h>
#include <linux/input/mt.h>
#include <linux/interrupt.h>
#include <linux/jiffies.h>
#include <linux/kthread.h>
#include <linux/module.h>
#include <linux/of.h>

extern int himax_bus_read(u8 command, u8 *data, u32 length, u8 retries);
extern void himax_int_enable(int enable);

static struct task_struct *worker;
static struct input_dev *touch;
static unsigned int touch_irq = 120;
static unsigned long frames, points, motion, releases, bad_crc, errors;
static unsigned long valid_frames, invalid_frames, zeros;
static bool pause, paused;
module_param(touch_irq, uint, 0444);
module_param(frames, ulong, 0444);
module_param(points, ulong, 0444);
module_param(motion, ulong, 0444);
module_param(releases, ulong, 0444);
module_param(bad_crc, ulong, 0444);
module_param(errors, ulong, 0444);
module_param(valid_frames, ulong, 0444);
module_param(invalid_frames, ulong, 0444);
module_param(zeros, ulong, 0444);
module_param(pause, bool, 0644);
module_param(paused, bool, 0444);

static void release_touch(void)
{
	unsigned int i;
	for (i = 0; i < 10; i++) {
		input_mt_slot(touch, i);
		input_mt_report_slot_state(touch, MT_TOOL_FINGER, false);
	}
	input_mt_sync_frame(touch);
	input_mt_report_pointer_emulation(touch, true);
	input_sync(touch);
}

static int poll_touch(void *unused)
{
	u8 packet[128];
	bool active = false;
	u16 last_x = 0, last_y = 0;
	unsigned long last_good = jiffies;
	while (!kthread_should_stop()) {
		unsigned int sum = 0, zero = 0, i, count, valid = 0;
		int ret;
		if (READ_ONCE(pause)) {
			if (!READ_ONCE(paused)) {
				release_touch();
				active = false;
				WRITE_ONCE(paused, true);
			}
			usleep_range(20000, 22000);
			continue;
		}
		if (READ_ONCE(paused)) {
			/* Debug recovery may have restored the native IRQ. Hold an
			 * independent IRQ-disable reference until any handler finishes,
			 * then return ownership to polling without removing input_dev.
			 */
			disable_irq(touch_irq);
			himax_int_enable(0);
			enable_irq(touch_irq);
			last_good = jiffies;
			WRITE_ONCE(paused, false);
		}
		ret = himax_bus_read(0x30, packet, sizeof(packet), 3);
		frames++;
		if (ret) {
			errors++;
			goto invalid;
		}
		for (i = 0; i < 56; i++) {
			sum += packet[i];
			zero += packet[i] == 0;
		}
		if (zero == 56) {
			zeros++;
			goto invalid;
		}
		if (sum & 0xff) {
			bad_crc++;
			goto invalid;
		}
		count = packet[52] == 0xff ? 0 : packet[52] & 0xf;
		if (count > 10) {
			bad_crc++;
			goto invalid;
		}
		last_good = jiffies;
		valid_frames++;
		for (i = 0; i < 10; i++) {
			u16 x = ((u16)packet[4*i] << 8) | packet[4*i+1];
			u16 y = ((u16)packet[4*i+2] << 8) | packet[4*i+3];
			bool present = count && x < 1200 && y < 2000;
			input_mt_slot(touch, i);
			input_mt_report_slot_state(touch, MT_TOOL_FINGER, present);
			if (!present)
				continue;
			valid++;
			input_report_abs(touch, ABS_MT_POSITION_X, x);
			input_report_abs(touch, ABS_MT_POSITION_Y, y);
			input_report_abs(touch, ABS_MT_TOUCH_MAJOR, packet[40+i]);
			input_report_abs(touch, ABS_MT_PRESSURE, packet[40+i]);
			if (i == 0) {
				if (active && (last_x != x || last_y != y))
					motion++;
				last_x = x;
				last_y = y;
			}
		}
		input_mt_sync_frame(touch);
		input_mt_report_pointer_emulation(touch, true);
		input_sync(touch);
		if (valid)
			points++;
		else if (active)
			releases++;
		active = valid != 0;
		goto next;
invalid:
		invalid_frames++;
		/* Missing/corrupt FIFO entries must not leave a finger held forever. */
		if (active && time_after(jiffies, last_good + msecs_to_jiffies(100))) {
			release_touch();
			releases++;
			active = false;
		}
next:
		if (active)
			usleep_range(8000, 8500);
		else
			usleep_range(16000, 17000);
	}
	release_touch();
	return 0;
}

static int __init touch_poll_init(void)
{
	int ret;
	if (!of_machine_is_compatible("lenovo,tb128"))
		return -ENODEV;
	touch = input_allocate_device();
	if (!touch)
		return -ENOMEM;
	touch->name = "TB128 Continuous Touch";
	touch->id.bustype = BUS_VIRTUAL;
	input_set_capability(touch, EV_KEY, BTN_TOUCH);
	input_set_abs_params(touch, ABS_MT_POSITION_X, 0, 1199, 0, 0);
	input_set_abs_params(touch, ABS_MT_POSITION_Y, 0, 1999, 0, 0);
	input_set_abs_params(touch, ABS_MT_TOUCH_MAJOR, 0, 255, 0, 0);
	input_set_abs_params(touch, ABS_MT_PRESSURE, 0, 255, 0, 0);
	input_abs_set_res(touch, ABS_MT_POSITION_X, 9);
	input_abs_set_res(touch, ABS_MT_POSITION_Y, 9);
	ret = input_mt_init_slots(touch, 10, INPUT_MT_DIRECT | INPUT_MT_DROP_UNUSED);
	if (ret)
		goto free;
	ret = input_register_device(touch);
	if (ret)
		goto free;
	himax_int_enable(0);
	synchronize_irq(touch_irq);
	worker = kthread_run(poll_touch, NULL, "tb128-touch-poll");
	if (IS_ERR(worker)) {
		ret = PTR_ERR(worker);
		himax_int_enable(1);
		input_unregister_device(touch);
		return ret;
	}
	pr_info("tb128_touch_poll: continuous input started\n");
	return 0;
free:
	input_free_device(touch);
	return ret;
}

static void __exit touch_poll_exit(void)
{
	kthread_stop(worker);
	input_unregister_device(touch);
	himax_int_enable(1);
	pr_info("tb128_touch_poll: native IRQ restored\n");
}

module_init(touch_poll_init);
module_exit(touch_poll_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Continuous HX83102E input for Lenovo TB128FU");
