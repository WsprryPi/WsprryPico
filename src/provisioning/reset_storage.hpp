#pragma once
#include "provisioning/local_access.hpp"
#include "provisioning/reset.hpp"
#include "standalone/ntp_retention.hpp"
#include "standalone/storage.hpp"
namespace wsprrypico::logging {
class UdpStore;
}
namespace wsprrypico::provisioning {
// Shared production/host implementation. Access intent is stored separately and
// remains authoritative throughout every erase below.
class ResetStorageTargets final : public ResetTargets {
  public:
    using ActivitySource = Activity (*)(void*);
    ResetStorageTargets(standalone::Store& store, standalone::Flash& flash, Media& profiles,
                        BondStore& bonds, ActivitySource activity, void* context,
                        bool (*erase_bonds)(void*) = nullptr, void* bond_context = nullptr,
                        standalone::NtpRetention* ntp = nullptr)
        : store_(store), flash_(flash), media_(profiles), bonds_(bonds), activity_(activity),
          context_(context), bond_erase_(erase_bonds), bond_context_(bond_context), ntp_(ntp) {}
    void udp_logging(logging::UdpStore& store) {
        udp_ = &store;
    }
    Activity activity() const override {
        return activity_(context_);
    }
    bool preserve_operational(const ProfileStore& profiles) override;
    bool clear_profile(ProfileStore& profiles, ProfileSource target) override;
    bool erase_operational() override;
    bool operational_erased() const override;
    bool erase_bonds() override {
        bonds_done_ = bond_erase_ ? bond_erase_(bond_context_) : bonds_.erase_all();
        return bonds_done_;
    }
    bool bonds_erased() const override {
        return bonds_done_;
    }

  private:
    logging::UdpStore* udp_ = nullptr;
    standalone::Store& store_;
    standalone::Flash& flash_;
    Media& media_;
    BondStore& bonds_;
    ActivitySource activity_;
    void* context_;
    bool bonds_done_ = false;
    bool (*bond_erase_)(void*);
    void* bond_context_;
    standalone::NtpRetention* ntp_;
};
} // namespace wsprrypico::provisioning
