// SPDX-License-Identifier: MIT
// Original diagnostic; register arithmetic follows Skyworks AN619 rev. 0.8.
// Fixed plan only: 25 MHz TCXO, PLLA x36, MS0 /72 = 12.5 MHz, 2 mA CLK0.
#include "hardware/i2c.h"
#include "pico/stdlib.h"
#include "pico/unique_id.h"

#include <cstdint>
#include <cstdio>
#include <cstring>

namespace {
constexpr uint8_t address = 0x60;
uint8_t original[188]{};
bool prepared = false, used = false;

bool read(uint8_t reg, uint8_t* values, unsigned count) {
    return i2c_write_timeout_us(i2c0, address, &reg, 1, true, 10000) == 1 &&
           i2c_read_timeout_us(i2c0, address, values, count, false, 10000) == int(count);
}
bool write(uint8_t reg, uint8_t value) {
    uint8_t bytes[]{reg, value};
    uint8_t observed = 0;
    return i2c_write_timeout_us(i2c0, address, bytes, 2, false, 10000) == 2 &&
           read(reg, &observed, 1) && observed == value;
}
bool off() {
    // Try both independent output-control mechanisms even after a failed write.
    const bool mask = write(3, 0xff);
    const bool power = write(16, 0x80);
    return mask && power;
}
bool restore() {
    bool ok = off();
    if (!prepared)
        return ok;
    constexpr uint8_t regs[]{15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 26, 27, 28, 29,
                             30, 31, 32, 33, 42, 43, 44, 45, 46, 47, 48, 49, 149};
    for (auto reg : regs)
        ok = write(reg, original[reg]) && ok;
    // The original mask/power combination was checked to keep all outputs disabled.
    ok = write(3, original[3]) && ok;
    prepared = false;
    return ok;
}
bool setup() {
    // Keep each 100 kHz read comfortably inside the 10 ms transaction deadline.
    for (unsigned reg = 0; reg < sizeof(original); reg += 16) {
        const auto count = sizeof(original) - reg < 16 ? sizeof(original) - reg : 16;
        if (!read(reg, original + reg, count))
            return false;
    }
    printf("{\"initial_status\":%u,\"initial_output_disable\":%u,\"initial_clock_controls\":[%u,%u,"
           "%u]}\n",
           original[0], original[3], original[16], original[17], original[18]);
    // Each physical output must be disabled by its mask or powered down.
    for (unsigned channel = 0; channel < 3; ++channel)
        if (!(original[3] & (1u << channel)) && !(original[16 + channel] & 0x80))
            return false;
    prepared = true;
    if (!off())
        return false;
    for (unsigned reg = 17; reg <= 23; ++reg)
        if (!write(reg, 0x80))
            return false;
    if (!write(15, original[15] & ~4u) || !write(149, original[149] & 0x7f) ||
        !write(24, original[24] & ~3u) || !write(22, 0xc0))
        return false;
    // AN619: P1=128*a-512, P2=0, P3=1 for an integer a.
    constexpr uint8_t pll[]{0, 1, 0, 0x10, 0, 0, 0, 0}; // a=36
    constexpr uint8_t ms[]{0, 1, 0, 0x22, 0, 0, 0, 0};  // a=72, R=1
    for (unsigned i = 0; i < 8; ++i)
        if (!write(26 + i, pll[i]) || !write(42 + i, ms[i]))
            return false;
    // PLLA reset is self-clearing; unlike ordinary registers, do not compare it.
    uint8_t reset[]{177, 0x20};
    if (i2c_write_timeout_us(i2c0, address, reset, 2, false, 10000) != 2)
        return false;
    for (unsigned i = 0; i < 100; ++i) {
        uint8_t status = 0xff;
        if (!read(0, &status, 1))
            return false;
        if (!(status & 0xb0))       // SYS_INIT, LOL_A, LOS_XTAL
            return write(16, 0xcc); // Configured, integer, PLLA, 2 mA; still powered down.
        sleep_ms(5);
    }
    return false;
}
void tone() {
    if (used) {
        puts("{\"error\":\"one_tone_per_boot\"}");
        return;
    }
    used = true;
    if (!setup()) {
        const bool cleaned = prepared ? restore() : false;
        printf("{\"error\":\"prepare_failed\",\"restored\":%s}\n", cleaned ? "true" : "false");
        return;
    }
    uint8_t status = 0xff;
    read(0, &status, 1);
    printf("{\"ready\":true,\"frequency_hz\":12500000,\"duration_ms\":5000,\"drive_ma\":2,"
           "\"status\":%u}\n",
           status);
    fflush(stdout);
    if (!write(16, 0x4c) || !write(3, 0xfe)) {
        const bool cleaned = restore();
        printf("{\"error\":\"enable_failed\",\"restored\":%s}\n", cleaned ? "true" : "false");
        return;
    }
    const auto start = time_us_64();
    bool aborted = false;
    while (time_us_64() - start < 5000000) {
        if (!stdio_usb_connected() || getchar_timeout_us(0) == 'S') {
            aborted = true;
            break;
        }
        sleep_us(100);
    }
    const bool disabled = off();
    const auto stopped = time_us_64();
    const bool restored = restore();
    printf("{\"done\":true,\"aborted\":%s,\"disabled_verified\":%s,\"registers_restored\":%s,"
           "\"elapsed_us\":%llu}\n",
           aborted ? "true" : "false", disabled ? "true" : "false", restored ? "true" : "false",
           static_cast<unsigned long long>(stopped - start));
    fflush(stdout);
}
} // namespace
int main() {
    stdio_init_all();
    i2c_init(i2c0, 100000);
    gpio_set_function(4, GPIO_FUNC_I2C);
    gpio_set_function(5, GPIO_FUNC_I2C);
    gpio_pull_up(4);
    gpio_pull_up(5);
    char command[16]{};
    unsigned size = 0;
    for (;;) {
        const auto ch = getchar_timeout_us(1000);
        if (ch == PICO_ERROR_TIMEOUT || ch == '\r')
            continue;
        if (ch == '\n') {
            if (std::strcmp(command, "INFO") == 0) {
                char serial[PICO_UNIQUE_BOARD_ID_SIZE_BYTES * 2 + 1];
                pico_get_unique_board_id_string(serial, sizeof(serial));
                printf("{\"sketch\":\"Si5351ToneProbe\",\"serial\":\"%s\",\"frequency_hz\":"
                       "12500000}\n",
                       serial);
            } else if (std::strcmp(command, "TONE") == 0) {
                tone();
            } else if (std::strcmp(command, "STOP") == 0) {
                printf("{\"disabled_verified\":%s}\n", off() ? "true" : "false");
            }
            size = 0;
            std::memset(command, 0, sizeof(command));
        } else if (size + 1 < sizeof(command)) {
            command[size++] = static_cast<char>(ch);
        }
    }
}
