// SPDX-License-Identifier: MIT
// Original diagnostic; register arithmetic follows Skyworks AN619 rev. 0.8.
// Receive-only truth fixture: CLK2 / GP7 and independent QLG3 PPS / GP3.
// Fixed 25 MHz reference, PLLA x36, MS2 /900; CLK0 and CLK1 remain disabled.
#include "hardware/clocks.h"
#include "hardware/i2c.h"
#include "hardware/pwm.h"
#include "hardware/structs/io_bank0.h"
#include "hardware/uart.h"
#include "pico/bootrom.h"
#include "pico/stdio/driver.h"
#include "pico/stdio_usb.h"
#include "pico/stdlib.h"
#include "pico/unique_id.h"
#include "tusb.h"

#include <algorithm>
#if TRUTH_PRODUCTION_CAPTURE
#include "production.hpp"
#endif
#include <cstdint>
#include <cstdio>
#include <cstring>

namespace {
#ifndef TRUTH_INPUT_GP
#define TRUTH_INPUT_GP 7
#endif
#ifndef TRUTH_PPS_GP
#define TRUTH_PPS_GP 3
#endif
#ifndef TRUTH_EXTERNAL_REFERENCE
#define TRUTH_EXTERNAL_REFERENCE 0
#endif
constexpr unsigned input_gp = TRUTH_INPUT_GP, pps_gp = TRUTH_PPS_GP;
constexpr bool external_reference = TRUTH_EXTERNAL_REFERENCE;
static_assert(input_gp <= 27 && pps_gp <= 27 && (input_gp & 1) && (pps_gp & 1));
static_assert(((input_gp >> 1) & 7) != ((pps_gp >> 1) & 7));
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
    if (external_reference)
        return true; // External inputs never configure or write the Si5351.
    // Try both independent output-control mechanisms even after a failed write.
    const bool mask = write(3, 0xff);
    const bool power = write(18, 0x80);
    return mask && power;
}
bool restore() {
    bool ok = off();
    if (!prepared)
        return ok;
    constexpr uint8_t regs[]{15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 26, 27, 28, 29,
                             30, 31, 32, 33, 58, 59, 60, 61, 62, 63, 64, 65, 149};
    for (auto reg : regs)
        ok = write(reg, original[reg]) && ok;
    // The original mask/power combination was checked to keep CLK0 and CLK1 disabled.
    ok = write(3, original[3]) && ok;
    prepared = false;
    return ok;
}
bool setup() {
    if (external_reference)
        return true;
    // Keep each 100 kHz read comfortably inside the 10 ms transaction deadline.
    for (unsigned reg = 0; reg < sizeof(original); reg += 16) {
        const auto count = sizeof(original) - reg < 16 ? sizeof(original) - reg : 16;
        if (!read(reg, original + reg, count))
            return false;
    }
    printf("{\"initial_status\":%u,\"initial_output_disable\":%u,\"initial_clock_controls\":[%u,%u,"
           "%u]}\n",
           original[0], original[3], original[16], original[17], original[18]);
    // CLK0/CLK1 must be disabled. An existing CLK2 input reference is allowed.
    for (unsigned channel = 0; channel < 2; ++channel)
        if (!(original[3] & (1u << channel)) && !(original[16 + channel] & 0x80))
            return false;
    prepared = true;
    if (!off())
        return false;
    for (unsigned reg = 16; reg <= 23; ++reg)
        if (!write(reg, 0x80))
            return false;
    if (!write(15, original[15] & ~4u) || !write(149, original[149] & 0x7f) ||
        !write(24, original[24] & ~0x30u) || !write(22, 0xc0))
        return false;
    // AN619: P1=128*a-512, P2=0, P3=1 for an integer a.
    constexpr uint8_t pll[]{0, 1, 0, 0x10, 0, 0, 0, 0}; // a=36
    constexpr uint8_t ms[]{0, 1, 1, 0xc0, 0, 0, 0, 0};  // a=900, R=1
    for (unsigned i = 0; i < 8; ++i)
        if (!write(26 + i, pll[i]) || !write(58 + i, ms[i]))
            return false;
    // PLLA reset is self-clearing; unlike ordinary registers, do not compare it.
    uint8_t reset[]{177, 0x20};
    if (i2c_write_timeout_us(i2c0, address, reset, 2, false, 10000) != 2)
        return false;
    for (unsigned i = 0; i < 100; ++i) {
        uint8_t status = 0xff;
        if (!read(0, &status, 1))
            return false;
        if (!(status & 0xa8))       // SYS_INIT, LOL_A, LOS_XTAL
            return write(18, 0xcc); // Configured, integer, PLLA, 2 mA; still powered down.
        sleep_ms(5);
    }
    return false;
}

struct Endpoint {
    uint64_t before_us, after_us, count_low, count_high;
    bool high;
};
struct Pulse {
    Endpoint low, high;
};
Pulse pulses[301];
char nmea[TRUTH_PRODUCTION_CAPTURE ? 1 : 240000];
unsigned nmea_size = 0;
uint slice;
uint16_t previous_count;
uint64_t extended_count = 0, previous_us = 0, max_gap = 0;
bool coherent = true;
Endpoint snapshot() {
    Endpoint s{};
    s.before_us = time_us_64();
    const uint16_t count_low = pwm_get_counter(slice);
    s.high = gpio_get(pps_gp);
    const uint16_t count_high = pwm_get_counter(slice);
    s.after_us = time_us_64() + 1;
    if (previous_us && s.after_us - previous_us >= 400)
        coherent = false;
    if (previous_us)
        max_gap = std::max(max_gap, s.after_us - previous_us);
    s.count_low = extended_count + uint16_t(count_low - previous_count);
    extended_count = s.count_low + uint16_t(count_high - count_low);
    previous_count = count_high;
    previous_us = s.before_us;
    s.count_high = extended_count;
    return s;
}
void test(bool loaded) {
    if (used) {
        puts("ERROR one_test_per_boot");
        return;
    }
    used = true;
    if (!setup()) {
        const bool clean = restore();
        printf("END error=setup restored=%d\n", clean);
        return;
    }
    if (!external_reference && (!write(18, 0x4c) || !write(3, 0xfb))) {
        const bool clean = restore();
        printf("END error=enable restored=%d\n", clean);
        return;
    }
    const auto uart_settle = time_us_64();
    while (time_us_64() - uart_settle < 2000000ULL)
        if (uart_is_readable(uart0))
            (void)uart_get_hw(uart0)->dr;
    uart_get_hw(uart0)->rsr = 0;
    auto config = pwm_get_default_config();
    pwm_config_set_clkdiv_mode(&config, PWM_DIV_B_RISING);
    pwm_init(slice, &config, false);
    pwm_set_counter(slice, 0);
    pwm_set_enabled(slice, true);
    previous_count = 0;
    previous_us = 0;
    unsigned count = 0, uart_errors = 0;
    uint64_t first_error_us = 0;
    unsigned error_bits = 0;
    // Register setup can overlap a GPS sentence. Drain that pre-window FIFO
    // and clear its sticky receive errors before the defined capture interval.
    while (uart_is_readable(uart0))
        (void)uart_get_hw(uart0)->dr;
    uart_get_hw(uart0)->rsr = 0;
    const auto start = time_us_64();
    Endpoint prior = snapshot();
    unsigned load_writes = 0;
    auto next_load = start + 10000;
    constexpr char load[] = "LOAD 0123456789012345678901234567890123456789012345678901234567\n";
    static_assert(sizeof(load) - 1 == 64);
    while (count < 301 && time_us_64() - start < 310000000ULL && coherent) {
        Endpoint current = snapshot();
        if (current.high && !prior.high)
            pulses[count++] = {prior, current};
        prior = current;
        // One writer on core 0. Background USB service can only drain this
        // queue. A full queue skips the load; it never waits for the host.
        if (loaded && current.after_us >= next_load) {
            next_load = current.after_us + 10000;
            if (stdio_usb_connected() && tud_cdc_write_available() >= sizeof(load) - 1) {
                stdio_usb.out_chars(load, sizeof(load) - 1);
                ++load_writes;
            }
        }
        // Bounded draining: one byte per pass keeps count extension independent
        // of a long UART FIFO or USB print operation. Retain exact NMEA bytes.
        if (uart_is_readable(uart0)) {
            const auto data = uart_get_hw(uart0)->dr;
            if (data & 0xf00u) {
                ++uart_errors;
                error_bits |= data & 0xf00u;
                if (!first_error_us)
                    first_error_us = time_us_64() - start;
            }
            if (nmea_size < sizeof(nmea))
                nmea[nmea_size++] = char(data & 0xffu);
        }
    }
    pwm_set_enabled(slice, false);
    const bool clean = restore();
    for (unsigned i = 0; i < count; ++i) {
        const auto& p = pulses[i];
        printf("PULSE i=%u raw_low=%llu raw_high=%llu count_low=%llu count_high=%llu\n", i,
               (unsigned long long)p.low.before_us, (unsigned long long)p.high.after_us,
               (unsigned long long)p.low.count_low, (unsigned long long)p.high.count_high);
    }
    puts("NMEA_BEGIN");
    fwrite(nmea, 1, nmea_size, stdout);
    puts("\nNMEA_END");
    printf("END pulses=%u coherent=%d max_gap_us=%llu uart_errors=%u nmea_bytes=%u restored=%d "
           "first_error_us=%llu error_bits=%u loaded=%u load_writes=%u\n",
           count, coherent, (unsigned long long)max_gap, uart_errors, nmea_size, clean,
           (unsigned long long)first_error_us, error_bits, unsigned(loaded), load_writes);
    fflush(stdout);
}
#if TRUTH_PRODUCTION_CAPTURE
#include "production.inc.hpp"
#endif
} // namespace
int main() {
    set_sys_clock_khz(138000, true);
    stdio_init_all();
#if !TRUTH_PRODUCTION_CAPTURE
    uart_init(uart0, 9600);
    uart_set_hw_flow(uart0, false, false);
    uart_set_format(uart0, 8, 1, UART_PARITY_NONE);
    uart_set_fifo_enabled(uart0, true);
    gpio_set_function(1, GPIO_FUNC_UART);
    gpio_set_oeover(1, GPIO_OVERRIDE_LOW);
    gpio_init(pps_gp);
    gpio_set_dir(pps_gp, GPIO_IN);
    gpio_disable_pulls(pps_gp);
#endif
    if (!external_reference) {
        i2c_init(i2c0, 100000);
        gpio_set_function(4, GPIO_FUNC_I2C);
        gpio_set_function(5, GPIO_FUNC_I2C);
        gpio_pull_up(4);
        gpio_pull_up(5);
    }
#if !TRUTH_PRODUCTION_CAPTURE
    gpio_init(input_gp);
    gpio_set_dir(input_gp, GPIO_IN);
    gpio_disable_pulls(input_gp);
    gpio_set_oeover(input_gp, GPIO_OVERRIDE_LOW);
    gpio_set_input_enabled(input_gp, true);
    hw_write_masked(&io_bank0_hw->io[input_gp].ctrl,
                    GPIO_FUNC_PWM << IO_BANK0_GPIO0_CTRL_FUNCSEL_LSB,
                    IO_BANK0_GPIO0_CTRL_FUNCSEL_BITS);
#endif
    slice = pwm_gpio_to_slice_num(input_gp);
    const auto boot = time_us_64();
    char command[24]{};
    unsigned size = 0;
    while (time_us_64() - boot < 400000000ULL) {
#if !TRUTH_PRODUCTION_CAPTURE
        while (uart_is_readable(uart0))
            (void)uart_get_hw(uart0)->dr;
#endif
        int c = getchar_timeout_us(1000);
        if (c == PICO_ERROR_TIMEOUT || c == '\r')
            continue;
        if (c == '\n') {
            if (!strcmp(command, "INFO")) {
                char serial[PICO_UNIQUE_BOARD_ID_SIZE_BYTES * 2 + 1];
                pico_get_unique_board_id_string(serial, sizeof(serial));
                printf("INFO serial=%s clock_hz=%lu ram_only=1 pps_gp=%u input_gp=%u seconds=300 "
                       "source=%s production=%u\n",
                       serial, (unsigned long)clock_get_hz(clk_sys), pps_gp, input_gp,
                       external_reference ? "known_ratio" : "si5351",
                       unsigned(TRUTH_PRODUCTION_CAPTURE));
                fflush(stdout);
            } else if (!strcmp(command, "TEST"))
#if TRUTH_PRODUCTION_CAPTURE
                test_production(false);
#else
                test(false);
#endif
            else if (!strcmp(command, "TEST LOAD"))
#if TRUTH_PRODUCTION_CAPTURE
                test_production(true);
#else
                test(true);
#endif
            else if (!strcmp(command, "BOOTSEL"))
                break;
            else
                puts("ERROR unsupported");
            size = 0;
            command[0] = 0;
        } else if (size < sizeof(command) - 1) {
            command[size++] = char(c);
            command[size] = 0;
        }
    }
    (void)off();
    reset_usb_boot(0, 0);
}
