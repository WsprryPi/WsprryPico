#pragma once

#include "rf/amplifier_timing.hpp"

#include <cstdint>

namespace wsprrypico::rf {
// A checked local digital output. Readback is a pad/register observation, never
// a measurement of an external amplifier or its RF output.
class EnableOutput {
  public:
    virtual ~EnableOutput() = default;
    virtual bool initialize_inactive() = 0;
    virtual bool write(bool active) = 0;
    // Nonmutating launch check after a lead interval. Unsupported adapters
    // refuse rather than reasserting a changed output without settling.
    virtual bool verify_active() const {
        return false;
    }
};

// Owned by the RF core. No allocation, transport, delay or cross-core handshake.
// A null adapter is disabled and causes no output access or acknowledgement.
class AmplifierEnable {
  public:
    explicit AmplifierEnable(EnableOutput* output = nullptr, AmplifierTiming timing = {})
        : output_(output), timing_(timing) {}
    bool enabled() const {
        return output_ != nullptr;
    }
    const AmplifierTiming& timing() const {
        return timing_;
    }
    bool initialize() {
        known_inactive_ = timing_.valid() && (!output_ || output_->initialize_inactive());
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
    bool verify_active() const {
        return output_ && initialized_ && !known_inactive_ && output_->verify_active();
    }

  private:
    EnableOutput* output_;
    const AmplifierTiming timing_;
    bool initialized_ = false, known_inactive_ = false;
};

struct LaunchEnable {
    AmplifierEnable* amplifier = nullptr;
    bool already_active = false;
    void (*verified)(void*) = nullptr;
    void* context = nullptr;
    bool (*chain_verified)(void*) = nullptr;
    bool activate() const {
        if (chain_verified && !chain_verified(context))
            return false;
        const bool accepted =
            !amplifier || (already_active ? amplifier->verify_active() : amplifier->activate());
        if (accepted && amplifier && amplifier->enabled() && !already_active && verified)
            verified(context);
        return accepted;
    }
};
} // namespace wsprrypico::rf
