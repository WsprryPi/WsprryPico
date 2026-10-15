#pragma once

#include "lwip/tcp.h"
#include "network/bootstrap_join.hpp"
#include "network/bootstrap_slot.hpp"
#include "network/consumer_radio.hpp"
#include "network/http.hpp"
#include "network/owner_claim_http.hpp"
#include "network/pico/bootstrap_crypto.hpp"
#include "network/pico/http_server.hpp"
#include "network/pico/owner_claim_crypto.hpp"
#include "network/pico/recovery_crypto.hpp"
#include "provisioning/consumer_claim.hpp"
#include "provisioning/consumer_claim_commit.hpp"
#include "provisioning/network_profile.hpp"
#include "provisioning/reset.hpp"

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

// Two bounded port-80 connection tasks, admitted on AP or consumer station.
// Commissioning plaintext routes remain AP-only; station setup is authenticated.
// Setup requires idle/unowned RF authority or the established verified physical
// stop/setup gate. Automatic recovery never invokes that physical stop override.
// Static bodies stream from
// flash in bounded chunks.
class PicoBootstrapServer {
  public:
    using InterfaceClassifier = bool (*)(const tcp_pcb*, void*);
    PicoBootstrapServer(std::string device, std::string firmware, InterfaceClassifier classifier,
                        void* context)
        : device_(std::move(device)), firmware_(std::move(firmware)), classifier_(classifier),
          classifier_context_(context), http_(this, classify_client, handle_client, finish_client) {
    }
    ~PicoBootstrapServer();
    bool start();
    void stop();
#ifdef WSPRRY_PICO_STANDALONE_RF
    static constexpr bool default_setup_admission = false;
#else
    static constexpr bool default_setup_admission = true;
#endif
    void poll(bool active, bool mutation_safe = false,
              bool setup_admitted = default_setup_admission, bool station_active = false,
              bool ap_accepting = true);
    void station_classifier(InterfaceClassifier classifier, void* context) {
        station_classifier_ = classifier;
        station_classifier_context_ = context;
    }
    void restart_control(bool (*restart)(void*), void* context) {
        restart_ = restart;
        restart_context_ = context;
    }
    void configure(std::string boot_id, provisioning::AccessStore& access,
                   provisioning::ProfileStore& profile, provisioning::RandomSource& random,
                   provisioning::IndicatorController& indicator, standalone::PicoNetwork& network,
                   provisioning::RuntimeProfile& runtime,
                   provisioning::PicoConsumerClaimPlatform& claim_platform,
                   std::string default_password);
    void configure_recovery(std::string boot, provisioning::AccessStore& access,
                            provisioning::RandomSource& random) {
        recovery_boot_id_ = std::move(boot);
        recovery_access_ = &access;
        recovery_random_ = &random;
    }
    void reset_control(provisioning::ResetResult (*begin)(provisioning::ResetLevel,
                                                          const wtp::PayloadDigest&, void*),
                       void* context) {
        reset_begin_ = begin;
        reset_context_ = context;
    }
    bool listening() const {
        return http_.listening();
    }
    bool owner_claim_pending() const {
        return owner_reconcile_ || owner_restart_pending_ ||
               (owner_slot_.state() != provisioning::ConsumerClaimState::None &&
                owner_slot_.state() != provisioning::ConsumerClaimState::Terminal);
    }
    void radio_control(ConsumerRadioApi& radio);
    void setup_control(void (*pause)(void*), void* context) {
        setup_control_ = pause;
        setup_control_context_ = context;
    }
    bool reply_active() const {
        return http_.reply_active();
    }
    struct Resources {
        bool connected = false;
        bool setup_pending = false;
        bool recovery_pending = false;
        unsigned network_slot_state = 0;
        unsigned owner_slot_state = 0;
        unsigned recovery_slot_state = 0;
        std::size_t pending_tcp_bytes = 0;
    };
    Resources resources() const {
        Resources result;
        result.connected = http_.connections() != 0;
        result.setup_pending = setup_pending();
        result.recovery_pending = reset_pending_;
        result.recovery_slot_state = static_cast<unsigned>(recovery_slot_.state());
        result.pending_tcp_bytes = http_.pending_bytes();
        result.network_slot_state = static_cast<unsigned>(slot_.state());
        result.owner_slot_state = static_cast<unsigned>(owner_slot_.state());
        return result;
    }
    bool setup_pending() const {
        if (recovery_slot_.state() != BootstrapSlotState::None || reset_pending_)
            return true;
        return slot_.state() != BootstrapSlotState::None || bootstrap_restart_pending_ ||
               owner_claim_pending() || owner_restart_pending_;
    }

  private:
    HttpResponse recovery(const HttpRequest& request);
    HttpResponse consumer_setup(const HttpRequest& request, std::uint64_t transaction);
    void setup_delivered(std::uint64_t transaction, bool apply);
    std::string setup_reply_path_;
    std::uint64_t setup_transaction_ = 0;
    void (*setup_control_)(void*) = nullptr;
    void* setup_control_context_ = nullptr;
    ConsumerRadioApi* radio_ = nullptr;
    bool setup_owner_status_committed_ = false;
    BootstrapSlot recovery_slot_;
    PicoRecoveryCrypto recovery_crypto_;
    bool reset_pending_ = false;
    provisioning::ResetResult (*reset_begin_)(provisioning::ResetLevel, const wtp::PayloadDigest&,
                                              void*) = nullptr;
    void* reset_context_ = nullptr;
    std::string recovery_boot_id_;
    provisioning::AccessStore* recovery_access_ = nullptr;
    provisioning::RandomSource* recovery_random_ = nullptr;
    static ConsumerInterface classify_client(void*, const tcp_pcb*, bool accepting);
    static HttpResponse handle_client(void*, const HttpRequest&, ConsumerInterface, std::uint64_t);
    static void finish_client(void*, std::uint64_t, bool);
    HttpResponse dispatch(const HttpRequest&, ConsumerInterface, std::uint64_t);
    void remember_setup_reply(const HttpRequest&, std::uint64_t);
    HttpResponse mutation(const HttpRequest& request);
    HttpResponse status() const;
    HttpResponse owner_status(bool claim_status);
    HttpResponse owner_mutation(const HttpRequest& request);
    bool blank_authority() const;
    bool network_setup_authority() const;
    bool owner_claimable() const;
    void end_trial(bool committed, std::uint64_t now_ms);
    void start_bootstrap_trial(std::uint64_t now_ms);
    void cancel_slot();
    void restore_bootstrap_network();
    void end_owner_trial(bool committed, std::uint64_t now_ms);
    void restore_owner_network();
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
    provisioning::NetworkProfile bootstrap_previous_network_;
    std::array<std::uint8_t, 32> ack_verifier_{};
    bool mutation_safe_ = false;
    bool setup_admitted_ = default_setup_admission;
    provisioning::ConsumerClaimSlot owner_slot_;
    PicoOwnerClaimCrypto owner_crypto_;
    OwnerClaimCredentials owner_trial_;
    provisioning::NetworkProfile previous_network_;
    std::string owner_slot_digest_, owner_request_digest_, owner_request_id_;
    std::uint64_t owner_submit_ms_ = 0;
    bool owner_trial_active_ = false, owner_trial_start_pending_ = false;
    bool owner_trial_switched_network_ = false;
    bool owner_submit_delivered_ = false, owner_reconcile_ = false;
    OwnerResultRestart owner_result_restart_;
    bool owner_restart_pending_ = false, owner_status_committed_reply_ = false;
    bool bootstrap_restart_pending_ = false, bootstrap_ack_delivered_ = false;
    BootstrapCommitGate bootstrap_commit_;
    bool bootstrap_trial_switched_network_ = false;
    bool bootstrap_trial_start_pending_ = false, bootstrap_submit_delivered_ = false;
    std::uint64_t bootstrap_submit_delivered_ms_ = 0;
    std::uint64_t bootstrap_committed_ms_ = 0;

    std::string device_;
    std::string firmware_;
    InterfaceClassifier classifier_ = nullptr;
    void* classifier_context_ = nullptr;
    InterfaceClassifier station_classifier_ = nullptr;
    void* station_classifier_context_ = nullptr;
    bool ap_active_ = false, station_active_ = false, ap_accepting_ = false;
    bool ap_setup_admitted_ = false;
    std::uint64_t next_listen_attempt_ms_ = 0;
    PicoHttpServer http_;
    bool active_ = false;
    bool (*restart_)(void*) = nullptr;
    void* restart_context_ = nullptr;
};

} // namespace wsprrypico::network
