// SPDX-License-Identifier: MIT
#pragma once
#include "hardware/si5351_settings.hpp"
#include "rf/reference_counter.hpp"
#include "rf/reference_monitor.hpp"
#include "time/gps_calibration.hpp"
#include <atomic>

namespace wsprrypico::rf {
// RF-owner-only, input-only PWM capture. Clock output control belongs to the
// Si5351 device owner; opening capture never enables an external clock.
class PicoReferenceCapture final : public ReferenceCapture {
  public:
    PicoReferenceCapture() = default;
    ~PicoReferenceCapture() {
        close();
    }
    PicoReferenceCapture(const PicoReferenceCapture&) = delete;
    PicoReferenceCapture& operator=(const PicoReferenceCapture&) = delete;
    bool open(const hardware::PinPlan&, const hardware::Si5351Settings&,
              const hardware::FilterSettings& filters = {});
    bool begin(std::uint64_t plan_generation) override;
    bool poll(std::uint64_t plan_generation) override;
    ReferenceWindow finish() override;
    void close();
    // Bounded read-only core-0 PPS IRQ snapshot. Every published word is
    // atomic; a concurrent worker update/refusal returns an incoherent sample.
    time::gps::CycleSnapshot pps_snapshot() const;
    std::string_view error() const override {
        return counter_.error();
    }

  private:
    CounterSample snapshot() const;
    std::optional<unsigned> gpio_, slice_;
    std::uint32_t system_hz_ = 0, reference_hz_ = 0;
    bool running_ = false;
    ReferenceCounter counter_;
    CounterSample previous_;
    std::uint64_t generation_ = 0;
    static unsigned claimed_slices_;
    void publish();
    void unpublish();
    mutable std::atomic<std::uint32_t> publication_sequence_{0};
    static_assert(std::atomic<std::uint32_t>::is_always_lock_free);
    std::array<std::atomic<std::uint32_t>, 14> publication_{};
    std::uint64_t capture_id_ = 0, last_publication_ns_ = 0;
};
} // namespace wsprrypico::rf
