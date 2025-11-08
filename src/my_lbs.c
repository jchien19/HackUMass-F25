/*
 * Copyright (c) 2018 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 */

#include <zephyr/types.h>
#include <stddef.h>
#include <string.h>
#include <errno.h>
#include <zephyr/sys/printk.h>
#include <zephyr/sys/byteorder.h>
#include <zephyr/kernel.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/hci.h>
#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/uuid.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/logging/log.h>
#include "my_lbs.h"

LOG_MODULE_REGISTER(my_lbs, LOG_LEVEL_INF);

static bool button_state;
static struct my_lbs_cb lbs_cb;

static ssize_t write_led(struct bt_conn *conn, const struct bt_gatt_attr *attr, const void *buf,
                         uint16_t len, uint16_t offset, uint8_t flags)
{
    LOG_INF("Attribute write, handle: %u, conn: %p, len: %u", attr->handle, (void *)conn, len);

    if (len != 1U) {
        LOG_ERR("Write LED: Incorrect data length: %u", len);
        return BT_GATT_ERR(BT_ATT_ERR_INVALID_ATTRIBUTE_LEN);
    }

    if (offset != 0) {
        LOG_ERR("Write LED: Incorrect data offset: %u", offset);
        return BT_GATT_ERR(BT_ATT_ERR_INVALID_OFFSET);
    }

    if (lbs_cb.led_cb) {
        uint8_t val = *((uint8_t *)buf);
        LOG_INF("LED write value: 0x%02x (%s)", val, val ? "True" : "False");
        if (val == 0x00 || val == 0x01) {
            lbs_cb.led_cb(val ? true : false);
            LOG_INF("Called LED callback with state: %s", val ? "True" : "False");
        } else {
            LOG_ERR("Write LED: Incorrect value: 0x%02x", val);
            return BT_GATT_ERR(BT_ATT_ERR_VALUE_NOT_ALLOWED);
        }
    } else {
        LOG_ERR("No LED callback registered");
    }

    return len;
}

static ssize_t read_button(struct bt_conn *conn, const struct bt_gatt_attr *attr, void *buf,
                           uint16_t len, uint16_t offset)
{
    const char *value = attr->user_data;

    LOG_INF("Attribute read, handle: %u, conn: %p", attr->handle, (void *)conn);

    if (lbs_cb.button_cb) {
        button_state = lbs_cb.button_cb();
        LOG_INF("Button state read: %s", button_state ? "True" : "False");
        return bt_gatt_attr_read(conn, attr, buf, len, offset, value, sizeof(*value));
    }

    LOG_ERR("No button callback registered");
    return 0;
}

BT_GATT_SERVICE_DEFINE(my_lbs_svc,
    BT_GATT_PRIMARY_SERVICE(BT_UUID_LBS),
    BT_GATT_CHARACTERISTIC(BT_UUID_LBS_BUTTON, BT_GATT_CHRC_READ,
                           BT_GATT_PERM_READ, read_button, NULL, &button_state),
    BT_GATT_CHARACTERISTIC(BT_UUID_LBS_LED,
                           BT_GATT_CHRC_WRITE | BT_GATT_CHRC_WRITE_WITHOUT_RESP,
                           BT_GATT_PERM_WRITE, NULL, write_led, NULL),
);

int my_lbs_init(struct my_lbs_cb *callbacks)
{
    LOG_INF("Initializing LBS service");
    if (callbacks) {
        lbs_cb.led_cb = callbacks->led_cb;
        lbs_cb.button_cb = callbacks->button_cb;
        LOG_INF("LBS callbacks registered: led_cb=%p, button_cb=%p",
                (void *)lbs_cb.led_cb, (void *)lbs_cb.button_cb);
    } else {
        LOG_ERR("No LBS callbacks provided");
    }
    return 0;
}