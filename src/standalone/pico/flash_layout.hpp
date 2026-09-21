#pragma once

#include <cstddef>

namespace wsprrypico::standalone::flash_layout {
inline constexpr std::size_t physical_size = 4 * 1024 * 1024;
inline constexpr std::size_t erase_sector_size = 4096;
inline constexpr std::size_t profile_size = 16 * 1024;
inline constexpr std::size_t standalone_size = 16 * 1024;
inline constexpr std::size_t boot_workaround_size = erase_sector_size;
inline constexpr std::size_t boot_workaround_base = physical_size - boot_workaround_size;
inline constexpr std::size_t standalone_base = boot_workaround_base - standalone_size;
inline constexpr std::size_t profile_base = standalone_base - profile_size;
inline constexpr std::size_t linked_flash_size = profile_base;

static_assert(profile_base == 0x3f7000);
static_assert(standalone_base == 0x3fb000);
static_assert(boot_workaround_base == 0x3ff000);
static_assert(profile_base + profile_size == standalone_base);
static_assert(standalone_base + standalone_size == boot_workaround_base);
static_assert(boot_workaround_base + boot_workaround_size == physical_size);
static_assert(profile_size % erase_sector_size == 0);
static_assert(standalone_size % erase_sector_size == 0);
} // namespace wsprrypico::standalone::flash_layout
