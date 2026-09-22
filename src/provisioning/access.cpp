#include "provisioning/access.hpp"

#include <algorithm>
#include <array>
#include <limits>
#include <utility>

namespace wsprrypico::provisioning {
namespace {
constexpr std::uint64_t header_magic = 0x3248434341505357ULL;
constexpr std::uint64_t commit_magic = 0x3254434341505357ULL;
constexpr std::uint64_t record_magic = 0x3244455241505357ULL;
constexpr std::size_t payload_offset = access_page_size;
constexpr std::size_t commit_offset = access_slot_size - access_page_size;

void put(std::span<std::uint8_t> out, std::uint64_t value) {
    for (auto& byte : out) {
        byte = static_cast<std::uint8_t>(value);
        value >>= 8;
    }
}

std::uint64_t get(std::span<const std::uint8_t> in) {
    std::uint64_t result = 0;
    for (std::size_t i = 0; i < in.size(); ++i)
        result |= std::uint64_t{in[i]} << (8 * i);
    return result;
}

std::uint32_t crc32(std::span<const std::uint8_t> bytes) {
    std::uint32_t crc = 0xffffffffU;
    for (auto byte : bytes) {
        crc ^= byte;
        for (unsigned bit = 0; bit < 8; ++bit)
            crc = (crc >> 1) ^ ((crc & 1U) ? 0xedb88320U : 0U);
    }
    return ~crc;
}

bool erased(std::span<const std::uint8_t> bytes) {
    return std::all_of(bytes.begin(), bytes.end(), [](std::uint8_t value) { return value == 255; });
}

void secure_clear(std::span<std::uint8_t> bytes) {
    volatile std::uint8_t* data = bytes.empty() ? nullptr : bytes.data();
    for (std::size_t i = 0; i < bytes.size(); ++i)
        data[i] = 0;
}

void secure_clear(std::string& value) {
    volatile char* data = value.empty() ? nullptr : value.data();
    for (std::size_t i = 0; i < value.size(); ++i)
        data[i] = 0;
    std::string{}.swap(value);
}

bool valid_record(const AccessRecord& record) {
    if (!record.epoch || !valid_local_password(record.password) ||
        record.bond_count > authorized_bond_capacity)
        return false;
    for (std::size_t i = 0; i < record.bond_count; ++i) {
        if (!record.bonds[i])
            return false;
        for (std::size_t j = 0; j < i; ++j)
            if (record.bonds[i] == record.bonds[j])
                return false;
    }
    for (std::size_t i = record.bond_count; i < record.bonds.size(); ++i)
        if (record.bonds[i])
            return false;
    if (record.reset.level > ResetLevel::Full ||
        record.reset.phase > ResetPhase::BondsCleared ||
        record.reset.target_source > ProfileSource::BuildBundle)
        return false;
    if (!record.reset.pending())
        return record.reset.phase == ResetPhase::None;
    if (record.reset.phase == ResetPhase::None ||
        record.reset.phase > ResetPhase::BondsCleared)
        return false;
    if (record.reset.level == ResetLevel::Access &&
        record.reset.target_source != ProfileSource::Unprovisioned)
        return false;
    if (record.reset.level != ResetLevel::Access &&
        record.reset.target_source != ProfileSource::Unprovisioned &&
        record.reset.target_source != ProfileSource::BuildBundle)
        return false;
    return std::any_of(record.reset.request_digest.begin(), record.reset.request_digest.end(),
                       [](std::uint8_t value) { return value != 0; });
}

std::array<std::uint8_t, access_page_size> serialize(const AccessRecord& record) {
    std::array<std::uint8_t, access_page_size> out{};
    put(std::span(out).subspan(0, 8), record_magic);
    put(std::span(out).subspan(8, 4), 2);
    put(std::span(out).subspan(16, 8), record.epoch);
    std::uint8_t flags = 0;
    if (record.default_password)
        flags |= 1;
    if (record.field_mode)
        flags |= 2;
    if (record.ble_disabled)
        flags |= 4;
    out[24] = flags;
    out[25] = record.bond_count;
    out[26] = static_cast<std::uint8_t>(record.reset.level);
    out[27] = static_cast<std::uint8_t>(record.reset.phase);
    out[28] = static_cast<std::uint8_t>(record.reset.target_source);
    for (std::size_t i = 0; i < record.bonds.size(); ++i)
        put(std::span(out).subspan(32 + i * 8, 8), record.bonds[i]);
    std::copy(record.reset.request_digest.begin(), record.reset.request_digest.end(),
              out.begin() + 64);
    out[96] = static_cast<std::uint8_t>(record.password.size());
    std::copy(record.password.begin(), record.password.end(), out.begin() + 97);
    return out;
}

std::optional<AccessRecord> deserialize(std::span<const std::uint8_t> bytes) {
    if (bytes.size() != access_page_size || get(bytes.subspan(0, 8)) != record_magic ||
        get(bytes.subspan(8, 4)) != 2 || bytes[24] & ~std::uint8_t{7} || bytes[29] || bytes[30] ||
        bytes[31] || bytes[96] > 63)
        return {};
    AccessRecord record;
    record.epoch = get(bytes.subspan(16, 8));
    record.default_password = bytes[24] & 1;
    record.field_mode = bytes[24] & 2;
    record.ble_disabled = bytes[24] & 4;
    record.bond_count = bytes[25];
    record.reset.level = static_cast<ResetLevel>(bytes[26]);
    record.reset.phase = static_cast<ResetPhase>(bytes[27]);
    record.reset.target_source = static_cast<ProfileSource>(bytes[28]);
    for (std::size_t i = 0; i < record.bonds.size(); ++i)
        record.bonds[i] = get(bytes.subspan(32 + i * 8, 8));
    std::copy_n(bytes.begin() + 64, record.reset.request_digest.size(),
                record.reset.request_digest.begin());
    record.password.assign(reinterpret_cast<const char*>(bytes.data() + 97), bytes[96]);
    const auto used = 97 + bytes[96];
    if (!std::all_of(bytes.begin() + used, bytes.end(), [](std::uint8_t value) { return value == 0; }) ||
        !valid_record(record)) {
        scrub(record);
        return {};
    }
    return record;
}

struct Candidate {
    enum class State { Empty, Pending, Valid, Invalid } state = State::Empty;
    std::uint64_t sequence = 0;
    AccessRecord record;
    ~Candidate() {
        scrub(record);
    }
};

Candidate scan(AccessMedia& media, std::size_t slot) {
    Candidate result;
    const auto base = slot * access_slot_size;
    std::array<std::uint8_t, access_slot_size> image{};
    if (!media.read(base, image)) {
        result.state = Candidate::State::Invalid;
        return result;
    }
    if (erased(image))
        return result;
    const auto header = std::span<const std::uint8_t>(image).first(access_page_size);
    const auto payload = std::span<const std::uint8_t>(image).subspan(payload_offset, access_page_size);
    const auto commit = std::span<const std::uint8_t>(image).subspan(commit_offset, access_page_size);
    if (erased(header) || erased(commit)) {
        result.state = Candidate::State::Pending;
        secure_clear(image);
        return result;
    }
    const auto header_crc = crc32(header.first(access_page_size - 4));
    const auto commit_crc = crc32(commit.first(access_page_size - 4));
    const auto sequence = get(header.subspan(8, 8));
    const auto commit_sequence = get(commit.subspan(8, 8));
    const auto digest = wtp::sha256(payload);
    const bool valid = get(header.first(8)) == header_magic && sequence &&
                       get(header.subspan(16, 4)) == access_page_size &&
                       get(header.subspan(20, 4)) == 2 &&
                       get(header.last(4)) == header_crc &&
                       std::equal(digest.begin(), digest.end(), header.begin() + 24) &&
                       get(commit.first(8)) == commit_magic && commit_sequence == sequence &&
                       get(commit.last(4)) == commit_crc &&
                       std::equal(digest.begin(), digest.end(), commit.begin() + 16);
    if (!valid) {
        result.state = Candidate::State::Invalid;
        secure_clear(image);
        return result;
    }
    auto decoded = deserialize(payload);
    if (!decoded) {
        result.state = Candidate::State::Invalid;
        secure_clear(image);
        return result;
    }
    result.sequence = sequence;
    result.record = std::move(*decoded);
    scrub(*decoded);
    result.state = Candidate::State::Valid;
    secure_clear(image);
    return result;
}
} // namespace

bool valid_device_id(std::string_view device_id) {
    return device_id.size() == 32 &&
           std::all_of(device_id.begin(), device_id.end(), [](char value) {
               return (value >= '0' && value <= '9') || (value >= 'a' && value <= 'f');
           });
}

bool valid_local_password(std::string_view password) {
    return password.size() >= 8 && password.size() <= 63 &&
           std::all_of(password.begin(), password.end(),
                       [](unsigned char value) { return value >= 32 && value < 127; });
}

std::optional<LocalIdentity> derive_local_identity(std::string_view device_id,
                                                   std::string_view station_mac) {
    if (!valid_device_id(device_id) || station_mac.size() != 17)
        return {};
    std::array<std::uint8_t, 6> bytes{};
    const auto digit = [](char value) -> unsigned {
        if (value >= '0' && value <= '9')
            return static_cast<unsigned>(value - '0');
        if (value >= 'a' && value <= 'f')
            return static_cast<unsigned>(value - 'a' + 10);
        if (value >= 'A' && value <= 'F')
            return static_cast<unsigned>(value - 'A' + 10);
        return 16;
    };
    for (std::size_t octet = 0; octet < bytes.size(); ++octet) {
        const auto offset = octet * 3;
        const auto high = digit(station_mac[offset]);
        const auto low = digit(station_mac[offset + 1]);
        if (high > 15 || low > 15 || (octet != bytes.size() - 1 &&
                                      station_mac[offset + 2] != ':'))
            return {};
        bytes[octet] = static_cast<std::uint8_t>((high << 4) | low);
    }
    if ((bytes[0] & 1) ||
        std::all_of(bytes.begin(), bytes.end(), [](std::uint8_t value) { return value == 0; }))
        return {};
    constexpr char hex[] = "0123456789abcdef";
    std::string suffix;
    suffix.reserve(6);
    for (std::size_t i = 3; i < bytes.size(); ++i) {
        suffix.push_back(hex[bytes[i] >> 4]);
        suffix.push_back(hex[bytes[i] & 15]);
    }
    LocalIdentity result;
    result.suffix = suffix;
    result.hostname = "wsprrypico-" + suffix + ".local";
    result.advertising_name = "WsprryPico-" + suffix;
    result.softap_ssid = result.advertising_name;
    result.default_password = "wspr-" + suffix;
    return result;
}

bool idle_for_access(const Activity& activity) {
    return !activity.owned && activity.output_known && !activity.output_active && !activity.armed &&
           !activity.running && !activity.failed;
}

void scrub(AccessRecord& record) {
    secure_clear(record.password);
    record.epoch = 0;
    record.default_password = false;
    record.field_mode = false;
    record.ble_disabled = true;
    record.bonds.fill(0);
    record.bond_count = 0;
    record.reset = {};
}

AccessStore::~AccessStore() {
    scrub(record_);
}

bool AccessStore::load() {
    state_ = AccessStoreState::Fault;
    sequence_ = 0;
    active_slot_ = 0;
    scrub(record_);
    auto first = scan(media_, 0);
    auto second = scan(media_, 1);
    if (first.state == Candidate::State::Invalid || second.state == Candidate::State::Invalid)
        return false;
    if (first.state == Candidate::State::Empty && second.state == Candidate::State::Empty) {
        state_ = AccessStoreState::Erased;
        return true;
    }
    Candidate* best = nullptr;
    std::size_t best_slot = 0;
    for (std::size_t slot = 0; slot < 2; ++slot) {
        auto& candidate = slot ? second : first;
        if (candidate.state != Candidate::State::Valid)
            continue;
        if (best && candidate.sequence == best->sequence)
            return false;
        if (!best || candidate.sequence > best->sequence) {
            best = &candidate;
            best_slot = slot;
        }
    }
    if (!best)
        return false;
    sequence_ = best->sequence;
    active_slot_ = best_slot;
    record_ = best->record;
    secure_clear(best->record.password);
    state_ = AccessStoreState::Healthy;
    return true;
}

bool AccessStore::initialize(const AccessRecord& record) {
    if (state_ != AccessStoreState::Erased || record.epoch != 1 || !record.default_password ||
        record.field_mode || record.ble_disabled || record.bond_count || record.reset.pending())
        return false;
    return commit(record);
}

bool AccessStore::replace(const AccessRecord& record) {
    if (!healthy() || record.epoch < record_.epoch)
        return false;
    if (record == record_)
        return true;
    return commit(record);
}

bool AccessStore::commit(const AccessRecord& record) {
    if (!valid_record(record) || sequence_ == std::numeric_limits<std::uint64_t>::max())
        return false;
    const auto target = sequence_ ? 1 - active_slot_ : 0;
    const auto base = target * access_slot_size;
    if (!media_.erase(base)) {
        state_ = AccessStoreState::Fault;
        return false;
    }
    auto payload = serialize(record);
    const auto digest = wtp::sha256(payload);
    if (!media_.program(base + payload_offset, payload)) {
        secure_clear(payload);
        state_ = AccessStoreState::Fault;
        return false;
    }
    std::array<std::uint8_t, access_page_size> header;
    header.fill(255);
    put(std::span(header).first(8), header_magic);
    put(std::span(header).subspan(8, 8), sequence_ + 1);
    put(std::span(header).subspan(16, 4), payload.size());
    put(std::span(header).subspan(20, 4), 2);
    std::copy(digest.begin(), digest.end(), header.begin() + 24);
    put(std::span(header).last(4), crc32(std::span(header).first(access_page_size - 4)));
    if (!media_.program(base, header)) {
        secure_clear(payload);
        state_ = AccessStoreState::Fault;
        return false;
    }
    std::array<std::uint8_t, access_page_size> commit;
    commit.fill(255);
    put(std::span(commit).first(8), commit_magic);
    put(std::span(commit).subspan(8, 8), sequence_ + 1);
    std::copy(digest.begin(), digest.end(), commit.begin() + 16);
    put(std::span(commit).last(4), crc32(std::span(commit).first(access_page_size - 4)));
    if (!media_.program(base + commit_offset, commit)) {
        secure_clear(payload);
        state_ = AccessStoreState::Fault;
        return false;
    }
    auto verified = scan(media_, target);
    secure_clear(payload);
    if (verified.state != Candidate::State::Valid || verified.sequence != sequence_ + 1 ||
        verified.record != record) {
        state_ = AccessStoreState::Fault;
        return false;
    }
    ++sequence_;
    active_slot_ = target;
    scrub(record_);
    record_ = record;
    state_ = AccessStoreState::Healthy;
    return true;
}
} // namespace wsprrypico::provisioning
