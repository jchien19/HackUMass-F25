#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/gap.h>
#include <zephyr/bluetooth/uuid.h>
#include <zephyr/bluetooth/conn.h>
#include <zephyr/device.h>
#include <zephyr/drivers/pwm.h>
#include <dk_buttons_and_leds.h>
#include "my_lbs.h"

LOG_MODULE_REGISTER(Lesson4_Exercise1, LOG_LEVEL_INF);

/* BLE Advertising Parameters */
static const struct bt_le_adv_param *adv_param = BT_LE_ADV_PARAM(
    (BT_LE_ADV_OPT_CONN | BT_LE_ADV_OPT_USE_IDENTITY), /* Connectable advertising */
    800, /* Min Advertising Interval 500ms (800*0.625ms) */
    801, /* Max Advertising Interval 500.625ms (801*0.625ms) */
    NULL); /* Undirected advertising */

#define DEVICE_NAME CONFIG_BT_DEVICE_NAME
#define DEVICE_NAME_LEN (sizeof(DEVICE_NAME) - 1)

#define RUN_STATUS_LED DK_LED1
#define BLINKY_LED DK_LED2 /* For BLE LED characteristic */
#define RUN_LED_BLINK_INTERVAL 1000

/* PWM Definitions */
#define SERVO_MOTOR DT_NODELABEL(servo)
static const struct pwm_dt_spec pwm_servo = PWM_DT_SPEC_GET(SERVO_MOTOR);
#define PWM_PERIOD PWM_MSEC(20)
#define PWM_SERVO_MIN_PULSE_WIDTH DT_PROP(SERVO_MOTOR, min_pulse) /* 1ms */
#define PWM_SERVO_MAX_PULSE_WIDTH DT_PROP(SERVO_MOTOR, max_pulse) /* 2ms */

/* Servo Functions */
int set_motor_angle(uint32_t pulse_width_ns)
{
    int err = pwm_set_dt(&pwm_servo, PWM_PERIOD, pulse_width_ns);
    if (err) {
        LOG_ERR("pwm_set_dt returned %d", err);
    }
    return err;
}

static int run_servo_cycle(void)
{
    int err;
    if (!pwm_is_ready_dt(&pwm_servo)) {
        LOG_ERR("Error: PWM device %s is not ready", pwm_servo.dev->name);
        return -ENODEV;
    }
    LOG_INF("Starting servo cycle (22.5° -> 157.5° -> 22.5°)");
    err = set_motor_angle(1125000); /* ~22.5° */
    if (err) {
        LOG_ERR("Error setting min pulse, err %d", err);
        return err;
    }
    k_msleep(50); /* Wait for movement */
    err = set_motor_angle(1875000); /* ~157.5° */
    if (err) {
        LOG_ERR("Error setting max pulse, err %d", err);
        return err;
    }
    k_msleep(750); /* Wait for movement */
    err = set_motor_angle(1125000); /* Return to ~22.5° */
    if (err) {
        LOG_ERR("Error returning to initial, err %d", err);
        return err;
    }
    LOG_INF("Servo cycle complete");
    return 0;
}

/* BLE Advertising Data */
static const struct bt_data ad[] = {
    BT_DATA_BYTES(BT_DATA_FLAGS, (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR)),
    BT_DATA(BT_DATA_NAME_COMPLETE, DEVICE_NAME, DEVICE_NAME_LEN),
};

static const struct bt_data sd[] = {
    BT_DATA_BYTES(BT_DATA_UUID128_ALL, BT_UUID_LBS_VAL),
};

/* Advertising Work */
static struct k_work adv_work;

static void adv_work_handler(struct k_work *work)
{
    int err = bt_le_adv_start(adv_param, ad, ARRAY_SIZE(ad), sd, ARRAY_SIZE(sd));
    if (err) {
        LOG_ERR("Advertising failed to start (err %d)", err);
        return;
    }
    LOG_INF("Advertising successfully started");
}

static void advertising_start(void)
{
    k_work_submit(&adv_work);
}

static void recycled_cb(void)
{
    LOG_INF("Connection object recycled. Disconnect complete!");
    advertising_start();
}

/* BLE Connection Callbacks */
static void on_connected(struct bt_conn *conn, uint8_t err)
{
    if (err) {
        LOG_ERR("Connection failed (err %u)", err);
        return;
    }
    LOG_INF("Connected");
}

static void on_disconnected(struct bt_conn *conn, uint8_t reason)
{
    LOG_INF("Disconnected (reason %u)", reason);
}

struct bt_conn_cb connection_callbacks = {
    .connected = on_connected,
    .disconnected = on_disconnected,
    .recycled = recycled_cb,
};

/* LBS Callbacks */
static bool app_button_state;

static void app_led_cb(bool led_state)
{
    int err;
    LOG_INF("LED characteristic write: %s", led_state ? "True" : "False");
    if (led_state) {
        err = run_servo_cycle();
        if (err) {
            LOG_ERR("Failed to run servo cycle (err %d)", err);
        }
    } else {
        err = set_motor_angle(PWM_SERVO_MIN_PULSE_WIDTH);
        if (err) {
            LOG_ERR("Failed to set servo angle (err %d)", err);
        }
    }
    err = dk_set_led(BLINKY_LED, led_state);
    if (err) {
        LOG_ERR("Failed to set BLINKY_LED (err %d)", err);
    }
    LOG_INF("Set BLINKY_LED (DK_LED2) to %s", led_state ? "ON" : "OFF");
}

static bool app_button_cb(void)
{
    LOG_INF("Button characteristic read: %s", app_button_state ? "True" : "False");
    return app_button_state;
}

static struct my_lbs_cb app_callbacks = {
    .led_cb = app_led_cb,
    .button_cb = app_button_cb,
};

/* Button Handler */
static void button_handler(uint32_t button_state, uint32_t has_changed)
{
    if (has_changed & button_state & DK_BTN1_MSK) {
        LOG_INF("Button 1 pressed");
        app_button_state = true;
    } else if (has_changed & DK_BTN1_MSK) {
        app_button_state = false;
    }
}

static int init_button(void)
{
    int err = dk_buttons_init(button_handler);
    if (err) {
        LOG_ERR("Cannot init buttons (err: %d)", err);
    }
    return err;
}

int main(void)
{
    int err;
    int blink_status = 0;

    LOG_INF("Starting BLE Servo App");

    /* Initialize PWM servo */
    if (!pwm_is_ready_dt(&pwm_servo)) {
        LOG_ERR("Error: PWM device %s is not ready", pwm_servo.dev->name);
        return -1;
    }
    err = pwm_set_dt(&pwm_servo, PWM_PERIOD, PWM_SERVO_MIN_PULSE_WIDTH);
    if (err) {
        LOG_ERR("pwm_set_dt returned %d", err);
        return -1;
    }

    /* Initialize LEDs and Buttons */
    err = dk_leds_init();
    if (err) {
        LOG_ERR("LEDs init failed (err %d)", err);
        return -1;
    }

    err = init_button();
    if (err) {
        LOG_ERR("Button init failed (err %d)", err);
        return -1;
    }

    /* Initialize Bluetooth */
    err = bt_enable(NULL);
    if (err) {
        LOG_ERR("Bluetooth init failed (err %d)", err);
        return -1;
    }
    LOG_INF("Bluetooth initialized");
    bt_conn_cb_register(&connection_callbacks);

    err = my_lbs_init(&app_callbacks);
    if (err) {
        LOG_ERR("Failed to init LBS (err:%d)", err);
        return -1;
    }
    LOG_INF("LBS initialized");

    k_work_init(&adv_work, adv_work_handler);
    advertising_start();

    /* Main loop for status LED */
    for (;;) {
        dk_set_led(RUN_STATUS_LED, (++blink_status) % 2);
        k_sleep(K_MSEC(RUN_LED_BLINK_INTERVAL));
    }
}