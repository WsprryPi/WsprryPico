#include "provisioning/pico/activation_platform.hpp"

namespace wsprrypico::provisioning {
bool PicoActivationPlatform::committed(const Profile& profile,
                                       std::uint64_t generation) const {
    if (!generation || generation != store_.sequence() || !store_.healthy() ||
        store_.source() != ProfileSource::RuntimeProfile || profile.device_id != device_id_)
        return false;
    auto persisted = parse_profile(store_.data());
    const bool matches = persisted && *persisted == profile;
    if (persisted)
        scrub(*persisted);
    return matches;
}

bool PicoActivationPlatform::close_admission(std::uint64_t generation) {
    if (!generation || generation != store_.sequence())
        return false;
    if (admission_closed_)
        return generation_ == generation;
    server_.set_admission(false);
    generation_ = generation;
    admission_closed_ = true;
    return true;
}

bool PicoActivationPlatform::prepare(const Profile& profile, std::uint64_t generation) {
    if (!admission_closed_ || generation != generation_ || !committed(profile, generation))
        return false;
    prepared_ = true;
    return true;
}

Activity PicoActivationPlatform::activity() const {
    const auto current = service_.activity();
    return {current.owned,
            true,
            current.output_active,
            current.state == wtp::State::Armed,
            current.state == wtp::State::Running,
            current.state == wtp::State::Failed};
}

bool PicoActivationPlatform::quiesce() {
    if (!prepared_)
        return false;
    if (!quiesced_) {
        server_.stop();
        quiesced_ = !server_.listening();
    }
    return quiesced_;
}

bool PicoActivationPlatform::install(const Profile& profile, std::uint64_t generation) {
    if (!quiesced_ || generation != generation_ || !committed(profile, generation))
        return false;
    if (!installed_)
        installed_ = runtime_.load(store_, device_id_) &&
                     runtime_.source() == RuntimeSource::Provisioned &&
                     runtime_.generation() == generation;
    return installed_;
}

bool PicoActivationPlatform::restart() {
    if (!installed_ || !restart_)
        return false;
    if (!restart_requested_)
        restart_requested_ = restart_(context_);
    return restart_requested_;
}

bool PicoActivationPlatform::fail_closed(std::uint64_t generation) {
    if (!generation || generation != store_.sequence())
        return false;
    server_.set_admission(false);
    server_.stop();
    admission_closed_ = true;
    generation_ = generation;
    if (!restart_requested_ && restart_)
        restart_requested_ = restart_(context_);
    return !server_.listening() && restart_requested_;
}
} // namespace wsprrypico::provisioning
