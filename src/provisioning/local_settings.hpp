#pragma once

#include "provisioning/hostname.hpp"
#include "standalone/progress.hpp"

namespace wsprrypico::provisioning {
// Serialized by the same application owner as BrowserApi. Callers establish
// physical USB authority, target binding, idle safety and revision first.
class LocalSettings {
  public:
    LocalSettings(ProfileStore& profiles, RuntimeProfile& runtime, standalone::Store& store,
                  standalone::Progress& progress, std::string device, std::string default_name)
        : profiles_(profiles), runtime_(runtime), store_(store), progress_(progress),
          device_(std::move(device)), default_(std::move(default_name)) {}
    ~LocalSettings() {
        if (factory_)
            scrub(*factory_);
    }
    void factory_profile(Profile value) {
        if (factory_)
            scrub(*factory_);
        factory_ = std::move(value);
    }
    bool healthy() const;
    std::string revision_context() const;
    std::string wifi_readback(std::string_view boot) const;
    // Explicit no-network is null; password null preserves only the current
    // network's password. Return empty on success; errors contain no secrets.
    std::string wifi_save(wtp::json::Value wifi);
    std::string ensure_local_profile();
    std::string station_save(const standalone::Config& candidate);
    bool pending_restart() const {
        return pending_restart_;
    }

  private:
    std::string commit(ProfileSource source, std::string_view payload);
    std::optional<ConsumerProfile> consumer_candidate() const;
    ProfileStore& profiles_;
    RuntimeProfile& runtime_;
    standalone::Store& store_;
    standalone::Progress& progress_;
    std::string device_, default_;
    std::optional<Profile> factory_;
    bool pending_restart_ = false;
};
} // namespace wsprrypico::provisioning
