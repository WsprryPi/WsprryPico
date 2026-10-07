#pragma once

#include "standalone/scheduler.hpp"

#include <optional>

namespace wsprrypico::provisioning {
// Instantiated only by explicit LED test images. The ordinary consumer
// scheduler retains its boot suspension; this one admits one finite occurrence.
class LedScheduleFixture {
  public:
    bool begin(standalone::Store& store, wtp::JobService& service) {
        const auto activity = service.activity();
        const auto clock = service.clock_snapshot();
        if (scheduler_ || !store.healthy() || !store.config() || store.config()->enabled ||
            activity.owned || activity.output_active ||
            clock.state != wtp::ClockState::Synchronized || clock.leap != wtp::LeapState::Normal ||
            clock.uncertainty_ns > 500'000'000)
            return false;
        auto one = *store.config();
        const auto boundary = (clock.utc_now_ns / 120'000'000'000ULL + 1) * 120;
        one.enabled = true;
        one.expires_utc_s = boundary + 113;
        one.schedules = {{86400, static_cast<std::uint32_t>(boundary % 86400)}};
        const auto checked = standalone::parse_config(standalone::serialize_config(one));
        if (!checked || !store.save(*checked))
            return false;
        scheduler_.emplace(store, service);
        return true;
    }
    void poll() {
        if (scheduler_)
            scheduler_->poll();
    }
    std::optional<std::string> stop() {
        if (scheduler_)
            return scheduler_->command("STOP");
        return std::nullopt;
    }

  private:
    std::optional<standalone::Scheduler> scheduler_;
};
} // namespace wsprrypico::provisioning
