#pragma once
#include <cassert>
#include <cstddef>
#include <cstdint>
#define FLASH_SECTOR_SIZE 4096
#define FLASH_PAGE_SIZE 256
#define PICO_FLASH_SIZE_BYTES (4 * 1024 * 1024)
#define XIP_BASE 0
inline void flash_range_erase(std::uint32_t, std::size_t) {
    assert(false);
}
inline void flash_range_program(std::uint32_t, const std::uint8_t*, std::size_t) {
    assert(false);
}
