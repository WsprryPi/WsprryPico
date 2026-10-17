#pragma once

#include <cstdint>

namespace wsprrypico::rf {
// A checked local digital output. Readback is a pad/register observation, never
// a measurement of an external amplifier or its RF output.
class EnableOutput {
  public:
    virtual ~EnableOutput() = default;
    virtual bool initialize_inactive() = 0;
    virtual bool write(bool active) = 0;
};

// Owned by the RF core. No allocation, transport, delay or cross-core handshake.
// A null adapter is disabled and causes no output access or acknowledgement.
class AmplifierEnable {
  public:
    explicit AmplifierEnable(EnableOutput* output = nullptr) : output_(output) {}
    bool initialize() {
        known_inactive_ = !output_ || output_->initialize_inactive();
        initialized_ = known_inactive_;
        return known_inactive_;
    }
    bool activate() {
        if (!output_)
            return true;
        if (!initialized_ || !known_inactive_)
            return false;
        known_inactive_ = false; // A failed write may still have changed the pad.
        return output_->write(true);
    }
    bool deactivate() {
        if (!output_)
            return true;
        // Retrying an uncertain cleanup is allowed; it never authorizes launch.
        known_inactive_ = initialized_ ? output_->write(false) : output_->initialize_inactive();
        initialized_ = initialized_ || known_inactive_;
        return known_inactive_;
    }
    bool output_active_or_unknown() const {
        return output_ && !known_inactive_;
    }

  private:
    EnableOutput* output_;
    bool initialized_ = false, known_inactive_ = false;
};

struct LaunchEnable {
    AmplifierEnable* amplifier = nullptr;
    bool activate() const {
        return !amplifier || amplifier->activate();
    }
};
} // namespace wsprrypico::rf
