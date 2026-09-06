#include "pico_adapters.hpp"

#include "pico/rand.h"
#include "pico/time.h"
#include "pico/unique_id.h"
#include "wtp/sha256.hpp"

#include <algorithm>
#include <array>
#include <limits>
#include <span>

#if !defined(WSPRRY_PICO_RF_OUTPUT_DISABLED) && !defined(WSPRRY_PICO_RF_WTP)
#error "Pico adapters may only be linked by an explicitly classified firmware image"
#endif

namespace wsprrypico::firmware {
namespace {

char hex_digit(std::uint8_t nibble) {
    return static_cast<char>(nibble < 10 ? '0' + nibble : 'a' + nibble - 10);
}

template <typename Bytes> std::string hex_id(const Bytes& bytes) {
    std::string result;
    result.reserve(bytes.size() * 2);
    for (const auto byte : bytes) {
        result.push_back(hex_digit(static_cast<std::uint8_t>(byte >> 4U)));
        result.push_back(hex_digit(static_cast<std::uint8_t>(byte & 0x0fU)));
    }
    return result;
}

} // namespace

wtp::ClockSnapshot PicoClock::snapshot() const {
    return {wtp::ClockState::Unsynchronized,
            0,
            time_us_64() * 1000ULL,
            std::numeric_limits<std::uint64_t>::max(),
            std::numeric_limits<std::uint64_t>::max(),
            wtp::LeapState::Unknown,
            std::nullopt};
}

PicoIdentitySource::PicoIdentitySource() {
    pico_unique_board_id_t board_id{};
    pico_get_unique_board_id(&board_id);
    constexpr std::array<std::uint8_t, 12> name{'W', 's', 'p', 'r', 'r', 'y',
                                                'P', 'i', 'c', 'o', '/', '1'};
    std::array<std::uint8_t, name.size() + PICO_UNIQUE_BOARD_ID_SIZE_BYTES> input{};
    std::copy(name.begin(), name.end(), input.begin());
    std::copy(std::begin(board_id.id), std::end(board_id.id), input.begin() + name.size());
    const auto digest = wtp::sha256(input);
    device_id_ = hex_id(std::span(digest).first<16>());
}

std::string PicoIdentitySource::new_boot_id() {
    rng_128_t random{};
    get_rand_128(&random);
    std::array<std::uint8_t, 16> bytes{};
    for (std::size_t word = 0; word < 2; ++word) {
        for (std::size_t byte = 0; byte < 8; ++byte) {
            bytes[word * 8 + byte] =
                static_cast<std::uint8_t>(random.r[word] >> static_cast<unsigned>(byte * 8));
        }
    }
    if (std::all_of(bytes.begin(), bytes.end(), [](std::uint8_t byte) { return byte == 0; })) {
        return {};
    }
    return hex_id(bytes);
}

const std::string& PicoIdentitySource::device_id() const {
    return device_id_;
}

} // namespace wsprrypico::firmware
