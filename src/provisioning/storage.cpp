#include "provisioning/storage.hpp"

#include "wtp/sha256.hpp"

#include <algorithm>
#include <array>
#include <limits>
#include <utility>
#include <vector>

namespace wsprrypico::provisioning {
namespace {
constexpr std::uint64_t header_magic = 0x3146525050435057ULL;
constexpr std::uint64_t commit_magic = 0x31544d4d4f435057ULL;
constexpr std::uint64_t selection_magic = 0x324c455350435057ULL;
constexpr std::size_t payload_offset = profile_page_size;
constexpr std::size_t commit_offset = profile_slot_size - profile_page_size;
constexpr std::size_t selection_header_size = 16;
constexpr std::size_t maximum_payload_size = max_profile_bytes + selection_header_size;

void put(std::span<std::uint8_t> out, std::uint64_t value) {
    for (auto& byte : out) {
        byte = static_cast<std::uint8_t>(value);
        value >>= 8;
    }
}
std::uint64_t get(std::span<const std::uint8_t> in) {
    std::uint64_t result = 0;
    for (std::size_t i = 0; i < in.size(); ++i)
        result |= std::uint64_t{in[i]} << (i * 8);
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
    return std::all_of(bytes.begin(), bytes.end(), [](std::uint8_t byte) { return byte == 255; });
}
void digest_to(std::span<std::uint8_t> out, const wtp::PayloadDigest& digest) {
    std::copy(digest.begin(), digest.end(), out.begin());
}
void secure_clear(std::span<std::uint8_t> value) {
    volatile std::uint8_t* bytes = value.empty() ? nullptr : value.data();
    for (std::size_t i = 0; i < value.size(); ++i)
        bytes[i] = 0;
}
void secure_clear(std::string& value) {
    volatile char* bytes = value.empty() ? nullptr : value.data();
    for (std::size_t i = 0; i < value.size(); ++i)
        bytes[i] = 0;
    std::string{}.swap(value);
}

struct Candidate {
    enum class State {
        Empty,
        Pending,
        Valid,
        InvalidUnknown,
        InvalidCommitted
    } state = State::Empty;
    std::uint64_t sequence = 0;
    std::string data;
    Candidate() = default;
    Candidate(const Candidate&) = delete;
    Candidate& operator=(const Candidate&) = delete;
    Candidate(Candidate&&) = default;
    Candidate& operator=(Candidate&&) = default;
    ~Candidate() {
        secure_clear(data);
    }
};

Candidate scan(Media& media, std::size_t slot) {
    Candidate result;
    const auto base = slot * profile_slot_size;
    std::array<std::uint8_t, profile_page_size> header{};
    std::array<std::uint8_t, profile_page_size> commit{};
    if (!media.read(base, header) || !media.read(base + commit_offset, commit)) {
        result.state = Candidate::State::InvalidUnknown;
        return result;
    }
    const bool header_erased = erased(header);
    const bool commit_erased = erased(commit);
    if (header_erased && commit_erased)
        return result;

    const auto checksum = crc32(std::span(header).first(profile_page_size - 4));
    const auto sequence = get(std::span(header).subspan(8, 8));
    const auto length = get(std::span(header).subspan(16, 4));
    const bool header_valid = !header_erased && get(std::span(header).first(8)) == header_magic &&
                              sequence != 0 && length != 0 && length <= maximum_payload_size &&
                              get(std::span(header).last(4)) == checksum;
    if (commit_erased) {
        if (!header_valid) {
            result.state = Candidate::State::Pending;
            return result;
        }
        result.sequence = sequence;
        std::vector<std::uint8_t> payload(length);
        const bool read = media.read(base + payload_offset, payload);
        wtp::PayloadDigest digest{};
        if (read)
            digest = wtp::sha256(payload);
        const bool matches = read && std::equal(digest.begin(), digest.end(), header.begin() + 24);
        secure_clear(std::span(payload));
        result.state = matches ? Candidate::State::Pending : Candidate::State::InvalidCommitted;
        return result;
    }

    const auto commit_checksum = crc32(std::span(commit).first(profile_page_size - 4));
    const auto commit_sequence = get(std::span(commit).subspan(8, 8));
    const bool commit_header_valid = get(std::span(commit).first(8)) == commit_magic &&
                                     commit_sequence != 0 &&
                                     get(std::span(commit).last(4)) == commit_checksum;
    if (!header_valid) {
        result.state = commit_header_valid ? Candidate::State::InvalidCommitted
                                           : Candidate::State::InvalidUnknown;
        result.sequence = commit_header_valid ? commit_sequence : 0;
        return result;
    }
    result.sequence = sequence;
    if (!commit_header_valid || commit_sequence != sequence ||
        !std::equal(header.begin() + 24, header.begin() + 56, commit.begin() + 16)) {
        result.state = Candidate::State::InvalidCommitted;
        return result;
    }
    std::vector<std::uint8_t> payload(length);
    if (!media.read(base + payload_offset, payload)) {
        secure_clear(std::span(payload));
        result.state = Candidate::State::InvalidCommitted;
        return result;
    }
    const auto digest = wtp::sha256(payload);
    if (!std::equal(digest.begin(), digest.end(), header.begin() + 24)) {
        secure_clear(std::span(payload));
        result.state = Candidate::State::InvalidCommitted;
        return result;
    }
    result.data.assign(reinterpret_cast<const char*>(payload.data()), payload.size());
    secure_clear(std::span(payload));
    result.state = Candidate::State::Valid;
    return result;
}
} // namespace

ProfileStore::~ProfileStore() {
    secure_clear(data_);
}

bool ProfileStore::load() {
    healthy_ = false;
    sequence_ = 0;
    active_slot_ = 0;
    source_ = ProfileSource::LegacyBootstrap;
    secure_clear(data_);
    auto first = scan(media_, 0);
    auto second = scan(media_, 1);
    if (first.state == Candidate::State::InvalidUnknown ||
        second.state == Candidate::State::InvalidUnknown)
        return false;
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
    const std::array<const Candidate*, 2> candidates{&first, &second};
    for (const auto* candidate : candidates) {
        if (candidate->state == Candidate::State::InvalidCommitted &&
            (!best || candidate->sequence >= best->sequence))
            return false;
    }
    if (best) {
        sequence_ = best->sequence;
        active_slot_ = best_slot;
        if (best->data.size() >= selection_header_size &&
            get(std::span(reinterpret_cast<const std::uint8_t*>(best->data.data()), 8)) ==
                selection_magic) {
            const auto source = static_cast<std::uint8_t>(best->data[8]);
            const bool reserved_clear =
                std::all_of(best->data.begin() + 9,
                            best->data.begin() + selection_header_size,
                            [](char byte) { return byte == 0; });
            if (!reserved_clear || source < static_cast<unsigned>(ProfileSource::RuntimeProfile) ||
                source > static_cast<unsigned>(ProfileSource::BuildBundle))
                return false;
            source_ = static_cast<ProfileSource>(source);
            if (source_ == ProfileSource::RuntimeProfile) {
                if (best->data.size() == selection_header_size)
                    return false;
                data_.assign(best->data.begin() + selection_header_size, best->data.end());
            } else if (best->data.size() != selection_header_size)
                return false;
        } else {
            // Version-1 payloads predate source selection. They remain usable
            // only as the one-way legacy bootstrap state.
            data_ = std::move(best->data);
        }
    }
    healthy_ = true;
    return true;
}

bool ProfileStore::replace(std::string_view canonical_profile) {
    return select(ProfileSource::RuntimeProfile, canonical_profile);
}

bool ProfileStore::select(ProfileSource source, std::string_view canonical_profile) {
    if (!healthy_ || source == ProfileSource::LegacyBootstrap ||
        (source == ProfileSource::RuntimeProfile &&
         (canonical_profile.empty() || canonical_profile.size() > max_profile_bytes)) ||
        (source != ProfileSource::RuntimeProfile && !canonical_profile.empty()) ||
        sequence_ == std::numeric_limits<std::uint64_t>::max())
        return false;
    if (source == source_ && canonical_profile == data_)
        return true;
    std::string payload(selection_header_size, '\0');
    put(std::span(reinterpret_cast<std::uint8_t*>(payload.data()), 8), selection_magic);
    payload[8] = static_cast<char>(source);
    payload.append(canonical_profile);
    const auto target = sequence_ ? 1 - active_slot_ : 0;
    const auto base = target * profile_slot_size;
    if (!media_.erase(base)) {
        healthy_ = false;
        secure_clear(payload);
        return false;
    }
    const auto input = std::span(reinterpret_cast<const std::uint8_t*>(payload.data()),
                                 payload.size());
    for (std::size_t offset = 0; offset < input.size(); offset += profile_page_size) {
        std::array<std::uint8_t, profile_page_size> page;
        page.fill(255);
        const auto count = std::min(profile_page_size, input.size() - offset);
        std::copy_n(input.begin() + offset, count, page.begin());
        const bool programmed = media_.program(base + payload_offset + offset, page);
        secure_clear(std::span(page));
        if (!programmed) {
            healthy_ = false;
            secure_clear(payload);
            return false;
        }
    }
    const auto digest = wtp::sha256(input);
    std::array<std::uint8_t, profile_page_size> header;
    header.fill(255);
    put(std::span(header).first(8), header_magic);
    put(std::span(header).subspan(8, 8), sequence_ + 1);
    put(std::span(header).subspan(16, 4), payload.size());
    put(std::span(header).subspan(20, 4), 2);
    digest_to(std::span(header).subspan(24, digest.size()), digest);
    put(std::span(header).last(4), crc32(std::span(header).first(profile_page_size - 4)));
    if (!media_.program(base, header)) {
        healthy_ = false;
        secure_clear(payload);
        return false;
    }
    std::array<std::uint8_t, profile_page_size> commit;
    commit.fill(255);
    put(std::span(commit).first(8), commit_magic);
    put(std::span(commit).subspan(8, 8), sequence_ + 1);
    digest_to(std::span(commit).subspan(16, digest.size()), digest);
    put(std::span(commit).last(4), crc32(std::span(commit).first(profile_page_size - 4)));
    if (!media_.program(base + commit_offset, commit)) {
        healthy_ = false;
        secure_clear(payload);
        return false;
    }
    const auto verified = scan(media_, target);
    if (verified.state != Candidate::State::Valid || verified.sequence != sequence_ + 1 ||
        verified.data != payload) {
        healthy_ = false;
        secure_clear(payload);
        return false;
    }
    ++sequence_;
    active_slot_ = target;
    secure_clear(data_);
    data_.assign(canonical_profile);
    source_ = source;
    secure_clear(payload);
    return true;
}
} // namespace wsprrypico::provisioning
