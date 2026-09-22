#pragma once

#include "provisioning/profile.hpp"

#include <cstdint>
#include <span>
#include <string>

namespace wsprrypico::provisioning {
inline constexpr std::size_t profile_page_size = 256;
inline constexpr std::size_t profile_slot_size = 8192;
inline constexpr std::size_t profile_media_size = profile_slot_size * 2;

enum class ProfileSource : std::uint8_t {
    LegacyBootstrap = 0,
    RuntimeProfile = 1,
    Unprovisioned = 2,
    BuildBundle = 3,
};

class Media {
  public:
    virtual ~Media() = default;
    virtual bool read(std::size_t offset, std::span<std::uint8_t> data) = 0;
    virtual bool erase(std::size_t slot_offset) = 0;
    virtual bool program(std::size_t offset, std::span<const std::uint8_t> page) = 0;
};

class ProfileStore {
  public:
    explicit ProfileStore(Media& media) : media_(media) {}
    ~ProfileStore();
    ProfileStore(const ProfileStore&) = delete;
    ProfileStore& operator=(const ProfileStore&) = delete;
    bool load();
    bool replace(std::string_view canonical_profile);
    bool select(ProfileSource source, std::string_view canonical_profile = {});
    bool healthy() const {
        return healthy_;
    }
    std::uint64_t sequence() const {
        return sequence_;
    }
    const std::string& data() const {
        return data_;
    }
    ProfileSource source() const {
        return source_;
    }
    bool adopted() const {
        return source_ != ProfileSource::LegacyBootstrap;
    }
    std::size_t active_slot() const {
        return active_slot_;
    }

  private:
    Media& media_;
    bool healthy_ = false;
    std::uint64_t sequence_ = 0;
    std::size_t active_slot_ = 0;
    std::string data_;
    ProfileSource source_ = ProfileSource::LegacyBootstrap;
};
} // namespace wsprrypico::provisioning
