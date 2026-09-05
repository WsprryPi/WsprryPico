#pragma once
#include <cstdint>
extern "C" {
bool tud_cdc_n_connected(std::uint8_t);
std::uint32_t tud_cdc_n_write(std::uint8_t, const void*, std::uint32_t);
std::uint32_t tud_cdc_n_read(std::uint8_t, void*, std::uint32_t);
std::uint32_t tud_cdc_n_write_flush(std::uint8_t);
bool tud_cdc_n_write_clear(std::uint8_t);
void tud_cdc_n_read_flush(std::uint8_t);
void tud_cdc_line_state_cb(std::uint8_t, bool, bool);
void tud_umount_cb();
void tud_mount_cb();
}
