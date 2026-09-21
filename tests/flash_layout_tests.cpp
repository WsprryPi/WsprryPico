#include "standalone/pico/flash_layout.hpp"

#include <cstdlib>
#include <iostream>

#define CHECK(condition)                                                                           \
    do {                                                                                           \
        if (!(condition)) {                                                                        \
            std::cerr << __LINE__ << ": " #condition "\n";                                       \
            std::exit(1);                                                                          \
        }                                                                                          \
    } while (false)

int main() {
    using namespace wsprrypico::standalone::flash_layout;
    CHECK(linked_flash_size == profile_base);
    CHECK(profile_base == 0x3f7000);
    CHECK(profile_base + profile_size == standalone_base);
    CHECK(standalone_base == 0x3fb000);
    CHECK(standalone_base + standalone_size == boot_workaround_base);
    CHECK(boot_workaround_base == 0x3ff000);
    CHECK(boot_workaround_base + boot_workaround_size == physical_size);
    CHECK(profile_size == 2 * 8192);
    CHECK(profile_size % erase_sector_size == 0);
    std::cout << "flash layout tests passed\n";
}
