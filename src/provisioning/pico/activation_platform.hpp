#pragma once

#include "network/pico/server.hpp"
#include "provisioning/activation.hpp"
#include "provisioning/runtime.hpp"
#include "provisioning/storage.hpp"
#include "wtp/job_service.hpp"

#include <cstdint>
#include <string>

namespace wsprrypico::provisioning {
// Production network-only activation boundary. It observes JobService but has
// no API capable of aborting, releasing, or changing job/RF ownership.
class PicoActivationPlatform final : public ActivationPlatform {
  public:
    using Restart = bool (*)(void*);
    PicoActivationPlatform(ProfileStore& store, RuntimeProfile& runtime,
                           wtp::JobService& service, network::PicoServer& server,
                           std::string device_id, Restart restart, void* context)
        : store_(store), runtime_(runtime), service_(service), server_(server),
          device_id_(std::move(device_id)), restart_(restart), context_(context) {}

    bool close_admission(std::uint64_t generation) override;
    bool prepare(const Profile& profile, std::uint64_t generation) override;
    Activity activity() const override;
    bool quiesce() override;
    bool install(const Profile& profile, std::uint64_t generation) override;
    bool restart() override;
    bool fail_closed(std::uint64_t generation) override;

  private:
    bool committed(const Profile& profile, std::uint64_t generation) const;

    ProfileStore& store_;
    RuntimeProfile& runtime_;
    wtp::JobService& service_;
    network::PicoServer& server_;
    std::string device_id_;
    Restart restart_ = nullptr;
    void* context_ = nullptr;
    std::uint64_t generation_ = 0;
    bool admission_closed_ = false;
    bool prepared_ = false;
    bool quiesced_ = false;
    bool installed_ = false;
    bool restart_requested_ = false;
};
} // namespace wsprrypico::provisioning
