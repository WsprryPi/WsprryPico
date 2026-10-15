#include "hardware/i2c.h"
#include "pico/stdlib.h"
#include "pico/unique_id.h"
#include <cstdint>
#include <cstdio>
#include <cstring>

namespace {
constexpr unsigned sda = 4, scl = 5;
constexpr unsigned timeout_us = 10'000;

void probe() {
    char serial[PICO_UNIQUE_BOARD_ID_SIZE_BYTES * 2 + 1];
    pico_get_unique_board_id_string(serial, sizeof(serial));
    printf("{\"sketch\":\"Si5351I2cProbe\",\"serial\":\"%s\",\"sda\":4,\"scl\":5,"
           "\"baud\":100000,\"sda_high\":%s,\"scl_high\":%s}\n",
           serial, gpio_get(sda) ? "true" : "false", gpio_get(scl) ? "true" : "false");
    unsigned found = 0, connected = 0;
    for (unsigned address = 0x08; address <= 0x77; ++address) {
        std::uint8_t byte = 0;
        if (i2c_read_timeout_us(i2c0, address, &byte, 1, false, timeout_us) != 1)
            continue;
        ++found;
        printf("{\"ack_address\":%u}\n", address);
        if (address != 0x60 && address != 0x61)
            continue;
        bool ok = true;
        for (unsigned sample = 0; sample != 3; ++sample) {
            const std::uint8_t reg = 0;
            std::uint8_t values[4]{};
            // Set only the read pointer; do not change clock/output configuration.
            const auto written = i2c_write_timeout_us(i2c0, address, &reg, 1, true, timeout_us);
            const auto read = written == 1
                                  ? i2c_read_timeout_us(i2c0, address, values, 4, false, timeout_us)
                                  : written;
            ok = ok && written == 1 && read == 4;
            printf("{\"address\":%u,\"sample\":%u,\"write_count\":%d,\"read_count\":%d,"
                   "\"status\":%u,\"interrupt_status\":%u,\"output_disable\":%u}\n",
                   address, sample, written, read, values[0], values[1], values[3]);
        }
        connected += ok;
    }
    printf("{\"result\":\"%s\",\"ack_count\":%u,\"si5351_candidates\":%u}\n",
           connected ? "CONNECTED" : "NOT_FOUND", found, connected);
    fflush(stdout);
}
} // namespace

int main() {
    stdio_init_all();
    i2c_init(i2c0, 100'000);
    gpio_set_function(sda, GPIO_FUNC_I2C);
    gpio_set_function(scl, GPIO_FUNC_I2C);
    gpio_pull_up(sda);
    gpio_pull_up(scl);
    char line[16]{};
    unsigned used = 0;
    for (;;) {
        const auto ch = getchar_timeout_us(1'000);
        if (ch == PICO_ERROR_TIMEOUT || ch == '\r')
            continue;
        if (ch == '\n') {
            if (std::strcmp(line, "PROBE") == 0)
                probe(); // One finite scan per explicit USB command; no RF or flash writes.
            used = 0;
            std::memset(line, 0, sizeof(line));
        } else if (used + 1 < sizeof(line)) {
            line[used++] = static_cast<char>(ch);
        }
    }
}
