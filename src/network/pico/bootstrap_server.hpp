#pragma once

#include "lwip/tcp.h"
#include "network/http.hpp"
#ifndef WSPRRY_PICO_STANDALONE_RF
#include "network/bootstrap_join.hpp"
#include "network/bootstrap_slot.hpp"
#include "network/pico/bootstrap_crypto.hpp"
#include "network/pico/owner_claim_crypto.hpp"
#include "provisioning/consumer_claim.hpp"
#include "provisioning/consumer_claim_commit.hpp"
#include "provisioning/network_profile.hpp"
#endif

#include <array>
#include <string>

namespace wsprrypico::provisioning {
class AccessStore;
class ProfileStore;
class RandomSource;
class IndicatorController;
class RuntimeProfile;
class PicoConsumerClaimPlatform;
} // namespace wsprrypico::provisioning
namespace wsprrypico::standalone {
class PicoNetwork;
}
namespace wsprrypico::network {

// One-connection AP-local plaintext server. The standard RF-inhibited image
// admits one encrypted setup transaction from the open AP; the RF worker
// build remains read-only. Static bodies stream from
// flash in bounded chunks.
class PicoBootstrapServer {
  public:
    using InterfaceClassifier = bool (*)(const tcp_pcb*, void*);
    PicoBootstrapServer(std::string device, std::string firmware, InterfaceClassifier classifier,
                        void* context)
        : device_(std::move(device)), firmware_(std::move(firmware)), classifier_(classifier),
          classifier_context_(context) {}
    ~PicoBootstrapServer();
    bool start();
    void stop();
    void poll(bool active, bool mutation_safe = false);
    void restart_control(bool (*restart)(void*), void* context) {
        restart_ = restart;
        restart_context_ = context;
    }
#ifndef WSPRRY_PICO_STANDALONE_RF
    void configure(std::string boot_id, provisioning::AccessStore& access,
                   provisioning::ProfileStore& profile, provisioning::RandomSource& random,
                   provisioning::IndicatorController& indicator, standalone::PicoNetwork& network,
                   provisioning::RuntimeProfile& runtime,
                   provisioning::PicoConsumerClaimPlatform& claim_platform,
                   std::string default_password);
#endif
    bool listening() const {
        return listener_ != nullptr;
    }
    bool owner_claim_pending() const {
#ifndef WSPRRY_PICO_STANDALONE_RF
        return owner_reconcile_ ||
               (owner_slot_.state() != provisioning::ConsumerClaimState::None &&
                owner_slot_.state() != provisioning::ConsumerClaimState::Terminal);
#else
        return false;
#endif
    }

  private:
    static err_t accept(void*, tcp_pcb*, err_t);
    static err_t receive(void*, tcp_pcb*, pbuf*, err_t);
    static err_t sent(void*, tcp_pcb*, u16_t);
    static void error(void*, err_t);
    void close();
    void dispatch();
#ifndef WSPRRY_PICO_STANDALONE_RF
    HttpResponse mutation(const HttpRequest& request);
    HttpResponse status() const;
    HttpResponse owner_status(bool claim_status);
    HttpResponse owner_mutation(const HttpRequest& request);
    bool blank_authority() const;
    bool owner_claimable() const;
    void end_trial(bool committed, std::uint64_t now_ms);
    void cancel_slot();
    void end_owner_trial(bool committed, std::uint64_t now_ms);
    void cancel_owner_slot(bool restore_network);
    std::string boot_id_, default_password_, slot_digest_;
    provisioning::AccessStore* access_ = nullptr;
    provisioning::ProfileStore* profile_ = nullptr;
    provisioning::RandomSource* random_ = nullptr;
    provisioning::IndicatorController* indicator_ = nullptr;
    standalone::PicoNetwork* network_ = nullptr;
    provisioning::RuntimeProfile* runtime_ = nullptr;
    provisioning::PicoConsumerClaimPlatform* claim_platform_ = nullptr;
    BootstrapSlot slot_;
    BootstrapJoinGate join_;
    PicoBootstrapCrypto crypto_;
    provisioning::NetworkProfile trial_;
    std::array<std::uint8_t, 32> ack_verifier_{};
    std::uint64_t last_sample_ms_ = 0;
    bool mutation_safe_ = false;
    provisioning::ConsumerClaimSlot owner_slot_;
    PicoOwnerClaimCrypto owner_crypto_;
    OwnerClaimCredentials owner_trial_;
    provisioning::NetworkProfile previous_network_;
    std::string owner_slot_digest_, owner_request_digest_, owner_request_id_;
    std::uint64_t owner_submit_ms_ = 0;
    bool owner_trial_active_ = false, owner_trial_start_pending_ = false;
    bool owner_submit_delivered_ = false, owner_reconcile_ = false;
    std::uint64_t owner_committed_ms_ = 0;
    bool owner_restart_pending_ = false, owner_status_delivered_ = false;
#endif

    std::string device_;
    std::string firmware_;
    InterfaceClassifier classifier_ = nullptr;
    void* classifier_context_ = nullptr;
    tcp_pcb* listener_ = nullptr;
    tcp_pcb* client_ = nullptr;
    HttpParser parser_;
    HttpResponse response_;
    std::string headers_;
    std::size_t header_offset_ = 0;
    std::size_t body_offset_ = 0;
    std::size_t pending_bytes_ = 0;
    std::uint64_t accepted_ms_ = 0;
    bool active_ = false;
    bool (*restart_)(void*) = nullptr;
    void* restart_context_ = nullptr;
};

} // namespace wsprrypico::network
