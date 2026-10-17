#pragma once

#include "network/http.hpp"
#include "time/controller_time.hpp"

namespace wsprrypico::usb {
class TimeExchange {
  public:
    TimeExchange(time::ControllerTimeArbiter& arbiter,
                 time::ControllerTimeArbiter::MonotonicNow now, void* context)
        : arbiter_(arbiter), now_(now), context_(context) {}
    network::HttpResponse handle(const network::HttpRequest&, std::uint64_t transaction);
    void reset() {
        sample_.clear();
        sampled_ns_ = 0;
    }

  private:
    time::ControllerTimeArbiter& arbiter_;
    time::ControllerTimeArbiter::MonotonicNow now_;
    void* context_;
    std::string sample_;
    std::uint64_t sampled_ns_ = 0;
};
} // namespace wsprrypico::usb
