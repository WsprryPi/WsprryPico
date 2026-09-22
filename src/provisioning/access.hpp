#pragma once

#include "provisioning/activation.hpp"
#include "provisioning/storage.hpp"
#include "wtp/sha256.hpp"

#include <array>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <string_view>

namespace wsprrypico::provisioning {
inline constexpr std::size_t access_page_size = 256;
inline constexpr std::size_t access_slot_size = 4096;
inline constexpr std::size_t access_media_size = access_slot_size * 2;
inline constexpr std::size_t authorized_bond_capacity = 4;

enum class ResetLevel : std::uint8_t { None, Access, Provisioning, Full };
enum class ResetPhase : std::uint8_t {
    None,
    Intent,
    SourceSelected,
    AccessReset,
    OperationalErased,
    BondsCleared,
};

struct ResetIntent {
    ResetLevel level = ResetLevel::None;
    ResetPhase phase = ResetPhase::None;
    ProfileSource target_source = ProfileSource::Unprovisioned;
    wtp::PayloadDigest request_digest{};
    bool pending() const {
        return level != ResetLevel::None;
    }
    bool operator==(const ResetIntent&) const = default;
};

struct AccessRecord {
    std::uint64_t epoch = 0;
    std::string password;
    bool default_password = true;
    bool field_mode = false;
    bool ble_disabled = false;
    std::array<std::uint64_t, authorized_bond_capacity> bonds{};
    std::uint8_t bond_count = 0;
    ResetIntent reset;
    bool operator==(const AccessRecord&) const = default;
};

struct LocalIdentity {
    std::string suffix;
    std::string hostname;
    std::string advertising_name;
    std::string softap_ssid;
    std::string default_password;
};

bool valid_device_id(std::string_view device_id);
bool valid_local_password(std::string_view password);
std::optional<LocalIdentity> derive_local_identity(std::string_view device_id,
                                                   std::string_view station_mac);
bool idle_for_access(const Activity& activity);
void scrub(AccessRecord& record);

class AccessMedia {
  public:
    virtual ~AccessMedia() = default;
    virtual bool read(std::size_t offset, std::span<std::uint8_t> data) = 0;
    virtual bool erase(std::size_t slot_offset) = 0;
    virtual bool program(std::size_t offset, std::span<const std::uint8_t> page) = 0;
};

enum class AccessStoreState { Unloaded, Erased, Healthy, Fault };

class AccessStore {
  public:
    explicit AccessStore(AccessMedia& media) : media_(media) {}
    ~AccessStore();
    AccessStore(const AccessStore&) = delete;
    AccessStore& operator=(const AccessStore&) = delete;

    bool load();
    bool initialize(const AccessRecord& record);
    bool replace(const AccessRecord& record);
    AccessStoreState state() const {
        return state_;
    }
    bool healthy() const {
        return state_ == AccessStoreState::Healthy;
    }
    std::uint64_t sequence() const {
        return sequence_;
    }
    std::size_t active_slot() const {
        return active_slot_;
    }
    const AccessRecord* record() const {
        return healthy() ? &record_ : nullptr;
    }

  private:
    bool commit(const AccessRecord& record);
    AccessMedia& media_;
    AccessStoreState state_ = AccessStoreState::Unloaded;
    std::uint64_t sequence_ = 0;
    std::size_t active_slot_ = 0;
    AccessRecord record_;
};
} // namespace wsprrypico::provisioning
