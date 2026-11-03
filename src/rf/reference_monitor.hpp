// SPDX-License-Identifier: MIT
#pragma once
#include "rf/reference_measurement.hpp"
#include "rf/si5351_device.hpp"

namespace wsprrypico::rf {
class ReferenceCapture {
  public:
    virtual ~ReferenceCapture() = default;
    virtual bool begin(std::uint64_t generation) = 0;
    virtual bool poll(std::uint64_t generation) = 0;
    virtual ReferenceWindow finish() = 0;
    virtual std::string_view error() const {
        return "reference_capture_failed";
    }
};
// One RF owner services this monitor only while job timing permits. Captures
// are never shared with I2C, discovery or an application-core status request.
class ReferenceMonitor {
  public:
    using Now = std::uint64_t (*)(void*);
    ReferenceMonitor(const si5351::Configuration& config, const ReferencePolicy& policy,
                     si5351::Device& device, ReferenceCapture& capture, Now now, void* context,
                     bool pps_calibration = false);
    void service(bool permitted);
    bool pause(std::uint64_t deadline_ns);
    void inhibit();
    std::optional<ReferenceMeasurement> current() const;
    std::uint64_t generation() const {
        return generation_;
    }
    std::string_view diagnostic() const;
    bool measuring() const {
        return measuring_;
    }

  private:
    void fault(std::string_view error);
    const si5351::Configuration config_;
    const ReferencePolicy policy_;
    const bool pps_calibration_;
    const std::optional<si5351::ReferencePlan> plan_;
    si5351::Device& device_;
    ReferenceCapture& capture_;
    Now now_;
    void* context_;
    std::uint64_t generation_ = 1, started_ns_ = 0, retry_ns_ = 0;
    bool measuring_ = false, inhibited_ = false, faulted_ = false;
    std::optional<ReferenceMeasurement> latest_;
    std::string_view error_ = "not_measured";
};
} // namespace wsprrypico::rf
