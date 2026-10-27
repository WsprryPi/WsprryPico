#include "standalone/storage.hpp"

#include "standalone/progress.hpp"

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
bool Journal::load(bool reset_recovery) {
    healthy_ = false;
    sequence_ = 0;
    data_.clear();
    if ((size_ != 256 && size_ != 2048) || base_ % 4096 || base_ > 8192)
        return false;
    std::vector<std::uint8_t> record(size_);
    bool ignored_torn_record = false;
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
        if (!valid) {
            if (reset_recovery) {
                ignored_torn_record = true;
                continue;
            }
            return false;
        } // Never resurrect an older enabled config or replay an ambiguous slot.
        if (seq == sequence_)
            return false;
        if (seq > sequence_) {
            sequence_ = seq;
            latest_ = offset;
            data_.assign(reinterpret_cast<const char*>(record.data() + 32), length);
        }
    }
    if (ignored_torn_record && sequence_ == 0)
        return false;
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
namespace {
std::string state_record(const std::optional<Config>& config,
                         const std::optional<MessageSchedule>& schedule,
                         logging::Settings logging = {}) {
    const auto c = config ? serialize_config(*config) : "null";
    if (logging.enabled || logging.maximum_severity != 6)
        return "{\"schema\":\"standalone-state/4\",\"config\":" + c + ",\"message_schedule\":" +
               (schedule ? serialize_message_schedule(*schedule) : "null") +
               ",\"logging\":{\"enabled\":" + (logging.enabled ? "true" : "false") +
               ",\"maximum_severity\":" + std::to_string(logging.maximum_severity) + "}}";
    if (!schedule)
        return config ? c : "";
    return "{\"schema\":\"standalone-state/3\",\"config\":" + c +
           ",\"message_schedule\":" + serialize_message_schedule(*schedule) + "}";
}
} // namespace
bool Store::load(bool reset_recovery) {
    healthy_ = false;
    current_.reset();
    logging_ = {};
    message_.reset();
    message_in_flight_ = false;
    watermark_ = 0;
    last_message_start_ = 0;
    if (!config_.load(reset_recovery) || !cursor_.load())
        return false;
    if (!config_.data().empty()) {
        const auto root = wtp::json::parse(config_.data());
        if (!root)
            return false;
        if (root->get("schema")) {
            const bool logs = root->get("schema")->string() == "standalone-state/4";
            if (logs) {
                if (!wtp::json::fields(*root, {"schema", "config", "message_schedule", "logging"}))
                    return false;
                const auto settings = *root->get("logging");
                const auto severity = settings.get("maximum_severity");
                if (!wtp::json::fields(settings, {"enabled", "maximum_severity"}) ||
                    (settings.get("enabled")->raw != "true" &&
                     settings.get("enabled")->raw != "false") ||
                    !severity || severity->raw.size() != 1 || severity->integer() < 0 ||
                    severity->integer() > 7 || severity->type() < '0' || severity->type() > '7')
                    return false;
                logging_ = {settings.get("enabled")->raw == "true",
                            static_cast<unsigned>(severity->integer())};
            } else if (!wtp::json::fields(*root, {"schema", "config", "message_schedule"}) ||
                       root->get("schema")->string() != "standalone-state/3")
                return false;
            if (root->get("config")->raw != "null") {
                current_ = parse_config(std::string(root->get("config")->raw));
                if (!current_)
                    return false;
            }
            if (root->get("message_schedule")->raw != "null") {
                message_ = parse_message_schedule(*root->get("message_schedule"));
                if (!message_ || (current_ && current_->enabled && message_->enabled))
                    return false;
            } else if (!logs)
                return false;
        } else {
            current_ = parse_config(config_.data());
            if (!current_)
                return false;
        }
    }
    if (!cursor_.data().empty()) {
        const auto& value = cursor_.data();
        if (value.starts_with('{')) {
            const auto cursor = wtp::json::parse(value);
            if (!cursor ||
                !wtp::json::fields(*cursor, {"schema", "watermark_ns", "message_in_flight",
                                             "last_message_start_ns"}) ||
                cursor->get("schema")->string() != "standalone-cursor/2" ||
                !wtp::json::decimal(*cursor->get("watermark_ns"), watermark_, true))
                return false;
            if (!wtp::json::decimal(*cursor->get("last_message_start_ns"), last_message_start_) ||
                last_message_start_ > watermark_)
                return false;
            const auto flight = cursor->get("message_in_flight")->raw;
            if (flight != "true" && flight != "false")
                return false;
            message_in_flight_ = flight == "true";
            if (message_in_flight_ && last_message_start_ != watermark_)
                return false;
        } else {
            const auto result =
                std::from_chars(value.data(), value.data() + value.size(), watermark_);
            if (result.ec != std::errc{} || result.ptr != value.data() + value.size() ||
                watermark_ == 0)
                return false;
        }
    }
    healthy_ = true;
    return true;
}
bool Store::save(const Config& config) {
    const auto legacy = serialize_config(config);
    const auto text = state_record(config, message_, logging_);
    if (!healthy() || !parse_config(legacy) || text.size() > max_state_bytes ||
        (config.enabled && message_ && message_->enabled))
        return false;
    if (!config_.append(text)) {
        healthy_ = false;
        return false;
    }
    current_ = config;
    return true;
}
bool Store::save_logging(logging::Settings settings) {
    if (!healthy() || settings.maximum_severity > 7)
        return false;
    const auto text = state_record(current_, message_, settings);
    if (text.size() > max_state_bytes)
        return false;
    if (!config_.append(text)) {
        healthy_ = false;
        return false;
    }
    logging_ = settings;
    return true;
}
bool Store::config_fits(const Config& config) const {
    return state_record(config, message_, logging_).size() <= max_state_bytes;
}
bool Store::message_schedule_fits(const std::optional<MessageSchedule>& schedule) const {
    return state_record(current_, schedule, logging_).size() <= max_state_bytes;
}
bool Store::save_message_schedule(const std::optional<MessageSchedule>& schedule) {
    if (!healthy() || !message_schedule_fits(schedule) ||
        (schedule && schedule->enabled && current_ && current_->enabled))
        return false;
    if (schedule) {
        const auto encoded = serialize_message_schedule(*schedule);
        const auto parsed = wtp::json::parse(encoded);
        if (!parsed || !parse_message_schedule(*parsed))
            return false;
    }
    if (!config_.append(state_record(current_, schedule, logging_))) {
        healthy_ = false;
        return false;
    }
    message_ = schedule;
    return true;
}
bool Store::reserve_cursor(std::uint64_t utc_ns, bool flight) {
    const auto message_start = flight ? utc_ns : last_message_start_;
    const auto data =
        message_ || flight || message_start
            ? "{\"schema\":\"standalone-cursor/2\",\"watermark_ns\":" +
                  wtp::json::quote(std::to_string(utc_ns)) +
                  ",\"message_in_flight\":" + (flight ? "true" : "false") +
                  ",\"last_message_start_ns\":" + wtp::json::quote(std::to_string(message_start)) +
                  "}"
            : std::to_string(utc_ns);
    if (!cursor_.append(data)) {
        healthy_ = false;
        return false;
    }
    watermark_ = utc_ns;
    last_message_start_ = message_start;
    message_in_flight_ = flight;
    return true;
}
bool Store::reserve(std::uint64_t utc_ns) {
    return healthy() && !message_in_flight_ && utc_ns > watermark_ && reserve_cursor(utc_ns, false);
}
bool Store::reserve_message(std::uint64_t utc_ns) {
    return healthy() && !message_in_flight_ && utc_ns > watermark_ && reserve_cursor(utc_ns, true);
}
bool Store::clear_message_flight() {
    return healthy() && (!message_in_flight_ || reserve_cursor(watermark_, false));
}
bool Store::healthy() const {
    return healthy_ && (!progress_ || progress_->healthy());
}
bool Store::erase_progress() {
    return !progress_ || progress_->erase();
}
} // namespace wsprrypico::standalone

namespace wsprrypico::standalone {
bool Journal::purge_history() {
    if (!healthy_ || !sequence_ || sequence_ == std::numeric_limits<std::uint64_t>::max())
        return false;
    const auto original_bank = latest_ / 4096;
    const auto offset = (1 - original_bank) * 4096;
    if (!flash_.erase(base_ + offset))
        return false;
    std::vector<std::uint8_t> record(size_, 255);
    auto bytes = std::span(record);
    put(bytes.first(8), 0x32524f5453505757ULL);
    put(bytes.subspan(8, 8), sequence_ + 1);
    put(bytes.subspan(16, 4), data_.size());
    std::copy(data_.begin(), data_.end(), record.begin() + 32);
    put(bytes.last(4), crc32(bytes.first(size_ - 4)));
    for (std::size_t page = 0; page < size_; page += 256)
        if (!flash_.program(base_ + offset + page, bytes.subspan(page, 256)))
            return false;
    std::vector<std::uint8_t> verified(size_);
    if (!flash_.read(base_ + offset, verified) || verified != record)
        return false;
    latest_ = offset;
    ++sequence_;
    if (!flash_.erase(base_ + original_bank * 4096))
        return false;
    std::array<std::uint8_t, 256> erased_page{};
    for (std::size_t page = 0; page < 4096; page += erased_page.size())
        if (!flash_.read(base_ + original_bank * 4096 + page, erased_page) || !erased(erased_page))
            return false;
    return load();
}
bool Store::purge_config_history(Flash&) {
    if (!healthy_ || !current_ || !config_.purge_history()) {
        healthy_ = false;
        return false;
    }
    return load();
}
} // namespace wsprrypico::standalone
