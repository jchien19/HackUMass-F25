#ifndef MY_LBS_H__
#define MY_LBS_H__

#include <zephyr/bluetooth/bluetooth.h>

#define BT_UUID_LBS_VAL \
    BT_UUID_128_ENCODE(0x00001523, 0x1212, 0xefde, 0x1523, 0x785feabcd123)
#define BT_UUID_LBS BT_UUID_DECLARE_128(BT_UUID_LBS_VAL)

#define BT_UUID_LBS_BUTTON_VAL \
    BT_UUID_128_ENCODE(0x00001525, 0x1212, 0xefde, 0x1523, 0x785feabcd123)
#define BT_UUID_LBS_BUTTON BT_UUID_DECLARE_128(BT_UUID_LBS_BUTTON_VAL)

#define BT_UUID_LBS_LED_VAL \
    BT_UUID_128_ENCODE(0x00001524, 0x1212, 0xefde, 0x1523, 0x785feabcd123)
#define BT_UUID_LBS_LED BT_UUID_DECLARE_128(BT_UUID_LBS_LED_VAL)

struct my_lbs_cb {
    void (*led_cb)(bool led_state);
    bool (*button_cb)(void);
};

int my_lbs_init(struct my_lbs_cb *callbacks);

#endif