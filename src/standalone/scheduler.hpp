#pragma once
#include "standalone/storage.hpp"
#include "wtp/job_service.hpp"

namespace wsprrypico::standalone {
class Scheduler {
  public:
    Scheduler(Store& store, wtp::JobService& service);
    void poll();
    bool idle() const;
    bool reset_permitted() const;
    bool reboot_required() const {
        return reboot_required_;
    }
    std::string command(std::string_view line);
    std::string status() const;

  private:
    wtp::Response request(std::string_view operation, wtp::RequestBody body = {});
    Store& store_;
    wtp::JobService& service_;
    std::uint64_t sequence_ = 0;
    wtp::ErrorCode last_error_ = wtp::ErrorCode::None;
    std::string last_job_;
    bool reboot_required_ = false, suspended_ = false;
    std::optional<wtp::PayloadDigest> active_network_;
};
} // namespace wsprrypico::standalone
