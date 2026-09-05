#include "tusb.h"
#include "usb/roles.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

void pico_get_unique_board_id_string(char* output, size_t length) {
    snprintf(output, length, "%s", "0123456789ABCDEF");
}
static void check_string(unsigned index, const char* expected) {
    const uint16_t* s = tud_descriptor_string_cb(index, 0x0409);
    assert(s != NULL);
    assert((s[0] & 255) == 2 + 2 * strlen(expected));
    for (size_t i = 0; i < strlen(expected); ++i)
        assert(s[i + 1] == (unsigned char)expected[i]);
}
int main(void) {
    const tusb_desc_device_t* device = (const tusb_desc_device_t*)tud_descriptor_device_cb();
    assert(device->idVendor == 0xcafe && device->idProduct == 0x4012);
    assert(device->bDeviceClass == TUSB_CLASS_MISC && device->bDeviceProtocol == MISC_PROTOCOL_IAD);
    check_string(device->iManufacturer, "WsprryPi");
    check_string(device->iProduct, "WsprryPico");
    check_string(device->iSerialNumber, "0123456789ABCDEF");
    assert(tud_descriptor_string_cb(255, 0x0409) == NULL);
    const uint8_t* config = tud_descriptor_configuration_cb(0);
    size_t total = config[2] | (config[3] << 8);
    assert(total == TUD_CONFIG_DESC_LEN + 2 * TUD_CDC_DESC_LEN);
    assert(config[4] == USB_ITF_COUNT && CFG_TUD_CDC == USB_CDC_COUNT);
    unsigned interfaces = 0, associations = 0, endpoints = 0;
    unsigned char seen_endpoints[256] = {0};
    for (size_t offset = 0; offset < total;) {
        const uint8_t* d = config + offset;
        assert(d[0] >= 2 && offset + d[0] <= total);
        if (d[1] == TUSB_DESC_INTERFACE_ASSOCIATION) {
            assert(d[2] == associations * 2 && d[3] == 2);
            assert(d[7] == 0); // Pinned TinyUSB names control interfaces, not IADs.
            ++associations;
        } else if (d[1] == TUSB_DESC_INTERFACE) {
            assert(d[2] == interfaces++);
            if (d[5] == TUSB_CLASS_CDC) {
                check_string(d[8],
                             d[2] == USB_ITF_CONSOLE ? "WsprryPico Console" : "WsprryPico WTP");
            }
        } else if (d[1] == TUSB_DESC_ENDPOINT) {
            assert(!seen_endpoints[d[2]]++);
            ++endpoints;
        }
        offset += d[0];
    }
    assert(interfaces == 4 && associations == 2 && endpoints == 6);
    puts("Actual TinyUSB descriptor expansion passed");
}
