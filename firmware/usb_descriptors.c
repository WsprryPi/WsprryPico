/*
 * Based on TinyUSB's cdc_dual_ports example.
 *
 * The MIT License (MIT)
 * Copyright (c) 2019 Ha Thach (tinyusb.org)
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

#include "pico/unique_id.h"
#include "tusb.h"
#include "usb/roles.h"

#include <stddef.h>
#include <string.h>

_Static_assert(CFG_TUD_CDC == USB_CDC_COUNT, "CDC role/configuration mismatch");

enum {
    STRID_LANGID = 0,
    STRID_MANUFACTURER,
    STRID_PRODUCT,
    STRID_SERIAL,
    STRID_CONSOLE,
    STRID_WTP,
};

#define USB_VID 0xcafe
#define USB_PID 0x4012
#define USB_BCD 0x0100
#define CONFIG_TOTAL_LEN (TUD_CONFIG_DESC_LEN + (2 * TUD_CDC_DESC_LEN))

#define EPNUM_CONSOLE_NOTIF 0x81
#define EPNUM_CONSOLE_OUT 0x02
#define EPNUM_CONSOLE_IN 0x82
#define EPNUM_WTP_NOTIF 0x83
#define EPNUM_WTP_OUT 0x04
#define EPNUM_WTP_IN 0x84

static tusb_desc_device_t const device_descriptor = {
    .bLength = sizeof(tusb_desc_device_t),
    .bDescriptorType = TUSB_DESC_DEVICE,
    .bcdUSB = 0x0200,
    .bDeviceClass = TUSB_CLASS_MISC,
    .bDeviceSubClass = MISC_SUBCLASS_COMMON,
    .bDeviceProtocol = MISC_PROTOCOL_IAD,
    .bMaxPacketSize0 = CFG_TUD_ENDPOINT0_SIZE,
    .idVendor = USB_VID,
    .idProduct = USB_PID,
    .bcdDevice = USB_BCD,
    .iManufacturer = STRID_MANUFACTURER,
    .iProduct = STRID_PRODUCT,
    .iSerialNumber = STRID_SERIAL,
    .bNumConfigurations = 1,
};

static uint8_t const configuration_descriptor[] = {
    TUD_CONFIG_DESCRIPTOR(1, USB_ITF_COUNT, 0, CONFIG_TOTAL_LEN, 0, 100),
    TUD_CDC_DESCRIPTOR(USB_ITF_CONSOLE, STRID_CONSOLE, EPNUM_CONSOLE_NOTIF, 8, EPNUM_CONSOLE_OUT,
                       EPNUM_CONSOLE_IN, 64),
    TUD_CDC_DESCRIPTOR(USB_ITF_WTP, STRID_WTP, EPNUM_WTP_NOTIF, 8, EPNUM_WTP_OUT, EPNUM_WTP_IN, 64),
};

uint8_t const* tud_descriptor_device_cb(void) {
    return (uint8_t const*)&device_descriptor;
}

uint8_t const* tud_descriptor_configuration_cb(uint8_t index) {
    (void)index;
    return configuration_descriptor;
}

uint16_t const* tud_descriptor_string_cb(uint8_t index, uint16_t langid) {
    (void)langid;
    static uint16_t descriptor[33];
    static char serial[(PICO_UNIQUE_BOARD_ID_SIZE_BYTES * 2) + 1];
    static char const* const strings[] = {
#ifdef WSPRRY_PICO_RF_BENCH
        NULL, "WsprryPi", "WsprryPico-RFBench", serial, "RFBench Console", "RFBench Commands",
#elif defined(WSPRRY_PICO_RF_WTP)
        NULL, "WsprryPi", "WsprryPico-RFWTP", serial, "RFWTP Time", "RFWTP WTP",
#else
        NULL, "WsprryPi", "WsprryPico", serial, "WsprryPico Console", "WsprryPico WTP",
#endif
    };

    if (index == STRID_LANGID) {
        descriptor[0] = (uint16_t)((TUSB_DESC_STRING << 8) | 4);
        descriptor[1] = 0x0409;
        return descriptor;
    }
    if (index >= (sizeof(strings) / sizeof(strings[0]))) {
        return NULL;
    }
    if (index == STRID_SERIAL) {
        pico_get_unique_board_id_string(serial, sizeof(serial));
    }
    const char* string = strings[index];
    size_t count = strlen(string);
    if (count > 32) {
        count = 32;
    }
    for (size_t position = 0; position < count; ++position) {
        descriptor[position + 1] = (uint8_t)string[position];
    }
    descriptor[0] = (uint16_t)((TUSB_DESC_STRING << 8) | (2 * count + 2));
    return descriptor;
}
