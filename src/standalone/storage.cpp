#include "standalone/storage.hpp"

#include <algorithm>
#include <charconv>
#include <limits>

namespace wsprrypico::standalone {
namespace {
void put(std::span<std::uint8_t> out, std::uint64_t n) {
    for (auto& byte : out) {
        byte = static_cast<std::uint8_t>(n);
        n >>= 8;
    }
}
std::uint64_t get(std::span<const std::uint8_t> in) {
    std::uint64_t n = 0;
    for (std::size_t i = 0; i < in.size(); ++i)
        n |= std::uint64_t{in[i]} << (8 * i);
    return n;
}
std::uint32_t crc32(std::span<const std::uint8_t> bytes) {
    std::uint32_t crc = 0xffffffffU;
    for (auto byte : bytes) {
        crc ^= byte;
        for (unsigned bit = 0; bit < 8; ++bit)
            crc = (crc >> 1) ^ ((crc & 1) ? 0xedb88320U : 0);
    }
    return ~crc;
}
bool erased(std::span<const std::uint8_t> bytes) {
    return std::all_of(bytes.begin(), bytes.end(), [](auto byte) { return byte == 255; });
}
} // namespace
bool Journal::load() {
    healthy_ = false;
    sequence_ = 0;
    data_.clear();
    if ((size_ != 256 && size_ != 2048) || base_ % 4096 || base_ > 8192)
        return false;
    std::vector<std::uint8_t> record(size_);
    for (std::size_t offset = 0; offset < 8192; offset += size_) {
        if (!flash_.read(base_ + offset, record))
            return false;
        if (erased(record))
            continue;
        const auto bytes = std::span(record);
        const auto checksum = crc32(bytes.first(size_ - 4));
        const auto seq = get(bytes.subspan(8, 8)), length = get(bytes.subspan(16, 4));
        const bool valid = get(bytes.first(8)) == 0x32524f5453505757ULL && seq > 0 &&
                           length <= size_ - 64 && get(bytes.last(4)) == checksum;
        if (!valid)
            return false; // Never resurrect an older enabled config or replay an ambiguous slot.
        if (seq == sequence_)
            return false;
        if (seq > sequence_) {
            sequence_ = seq;
            latest_ = offset;
            data_.assign(reinterpret_cast<const char*>(record.data() + 32), length);
        }
    }
    healthy_ = true;
    return true;
}
bool Journal::append(std::string_view data) {
    if (!healthy_ || data.size() > size_ - 64 ||
        sequence_ == std::numeric_limits<std::uint64_t>::max())
        return false;
    std::vector<std::uint8_t> record(size_, 255);
    std::size_t offset = sequence_ ? latest_ + size_ : 0;
    const auto bank = sequence_ ? latest_ / 4096 : 0;
    // Use only erased slots in the current bank. Any damaged record latches
    // a fault at boot rather than silently rolling back configuration.
    for (; offset < (bank + 1) * 4096; offset += size_) {
        if (!flash_.read(base_ + offset, record)) {
            healthy_ = false;
            return false;
        }
        if (erased(record))
            break;
    }
    if (offset >= (bank + 1) * 4096) {
        offset = (1 - bank) * 4096;
        if (!flash_.erase(base_ + offset)) {
            healthy_ = false;
            return false;
        }
    }
    std::fill(record.begin(), record.end(), 255);
    auto bytes = std::span(record);
    put(bytes.first(8), 0x32524f5453505757ULL);
    put(bytes.subspan(8, 8), sequence_ + 1);
    put(bytes.subspan(16, 4), data.size());
    std::copy(data.begin(), data.end(), record.begin() + 32);
    const auto checksum = crc32(bytes.first(size_ - 4));
    put(bytes.last(4), checksum);
    for (std::size_t page = 0; page < size_; page += 256)
        if (!flash_.program(base_ + offset + page, bytes.subspan(page, 256))) {
            healthy_ = false;
            return false;
        }
    std::vector<std::uint8_t> verified(size_);
    if (!flash_.read(base_ + offset, verified) || record != verified) {
        healthy_ = false;
        return false;
    }
    latest_ = offset;
    ++sequence_;
    data_ = data;
    return true;
}
bool Store::load() {
    healthy_ = false;
    current_.reset();
    watermark_ = 0;
    if (!config_.load() || !cursor_.load())
        return false;
    if (!config_.data().empty()) {
        current_ = parse_config(config_.data());
        if (!current_)
            return false;
    }
    if (!cursor_.data().empty()) {
        const auto& value = cursor_.data();
        const auto result = std::from_chars(value.data(), value.data() + value.size(), watermark_);
        if (result.ec != std::errc{} || result.ptr != value.data() + value.size() ||
            watermark_ == 0)
            return false;
    }
    healthy_ = true;
    return true;
}
bool Store::save(const Config& config) {
    const auto text = serialize_config(config);
    if (!healthy_ || !parse_config(text))
        return false;
    if (!config_.append(text)) {
        healthy_ = false;
        return false;
    }
    current_ = config;
    return true;
}
bool Store::reserve(std::uint64_t utc_ns) {
    if (!healthy_ || utc_ns <= watermark_)
        return false;
    if (!cursor_.append(std::to_string(utc_ns))) {
        healthy_ = false;
        return false;
    }
    watermark_ = utc_ns;
    return true;
}
} // namespace wsprrypico::standalone
