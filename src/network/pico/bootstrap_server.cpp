#include "network/pico/bootstrap_server.hpp"

#include "network/bootstrap_http.hpp"
#ifndef WSPRRY_PICO_STANDALONE_RF
#include "network/bootstrap_codec.hpp"
#include "network/bootstrap_wire.hpp"
#include "network/owner_claim_http.hpp"
#include "network/owner_wire.hpp"
#include "provisioning/access.hpp"
#include "provisioning/field_runtime.hpp"
#include "provisioning/local_access.hpp"
#include "provisioning/pico/consumer_claim_platform.hpp"
#include "provisioning/runtime.hpp"
#include "provisioning/storage.hpp"
#include "standalone/pico/adapters.hpp"
#include "wtp/json.hpp"
#endif
#include "pico/time.h"

#include <algorithm>
#include <cstring>
#include <limits>
#include <vector>

namespace wsprrypico::network {
#ifndef WSPRRY_PICO_STANDALONE_RF
namespace {
HttpResponse json(std::string body);
void erase(std::array<std::uint8_t, 32>& bytes);
} // namespace
#endif

PicoBootstrapServer::~PicoBootstrapServer() {
    stop();
}

bool PicoBootstrapServer::start() {
    if (listener_ || !classifier_ || device_.empty())
        return false;
    auto* pcb = tcp_new_ip_type(IPADDR_TYPE_V4);
    if (!pcb)
        return false;
    if (tcp_bind(pcb, IP_ANY_TYPE, 80) != ERR_OK) {
        tcp_abort(pcb);
        return false;
    }
    listener_ = tcp_listen_with_backlog(pcb, 1);
    if (!listener_) {
        tcp_abort(pcb);
        return false;
    }
    tcp_arg(listener_, this);
    tcp_accept(listener_, accept);
    return true;
}

err_t PicoBootstrapServer::accept(void* context, tcp_pcb* pcb, err_t err) {
    auto& self = *static_cast<PicoBootstrapServer*>(context);
    if (err != ERR_OK || !self.active_ || self.client_ ||
        !self.classifier_(pcb, self.classifier_context_)) {
        tcp_abort(pcb);
        return ERR_ABRT;
    }
    self.client_ = pcb;
    self.accepted_ms_ = time_us_64() / 1000;
    tcp_arg(pcb, &self);
    tcp_recv(pcb, receive);
    tcp_sent(pcb, sent);
    tcp_err(pcb, error);
    return ERR_OK;
}

err_t PicoBootstrapServer::receive(void* context, tcp_pcb*, pbuf* packet, err_t err) {
    auto& self = *static_cast<PicoBootstrapServer*>(context);
    if (!packet || err != ERR_OK) {
        if (packet)
            pbuf_free(packet);
        self.close(!packet && err == ERR_OK);
        return ERR_ABRT;
    }
    // A connection carries one request. Never let a pipelined request replace
    // a partially transmitted static response.
    if (!self.headers_.empty()) {
        pbuf_free(packet);
        self.close();
        return ERR_ABRT;
    }
    std::array<std::uint8_t, 1024> bytes{};
    const auto total = packet->tot_len;
    std::size_t offset = 0;
    while (offset < total && !self.parser_.failed() && !self.parser_.ready()) {
        const auto wanted = std::min<std::size_t>(bytes.size(), total - offset);
        const auto count = pbuf_copy_partial(packet, bytes.data(), wanted, offset);
        if (count != wanted) {
            pbuf_free(packet);
            self.close();
            return ERR_ABRT;
        }
        (void)self.parser_.receive(std::span(bytes).first(count));
        offset += count;
    }
    pbuf_free(packet);
    if (offset != total) {
        self.close(); // One HTTP request per connection; reject pipelined bytes.
        return ERR_ABRT;
    }
    tcp_recved(self.client_, total);
    if (self.parser_.failed() || self.parser_.ready())
        self.dispatch();
    return ERR_OK;
}

err_t PicoBootstrapServer::sent(void* context, tcp_pcb*, u16_t count) {
    auto& self = *static_cast<PicoBootstrapServer*>(context);
    self.pending_bytes_ -= std::min<std::size_t>(count, self.pending_bytes_);
    return ERR_OK;
}

void PicoBootstrapServer::error(void* context, err_t) {
    auto& self = *static_cast<PicoBootstrapServer*>(context);
#ifndef WSPRRY_PICO_STANDALONE_RF
    const bool submit_response = self.bootstrap_trial_start_pending_ &&
                                 !self.bootstrap_submit_delivered_ && self.parser_.ready() &&
                                 self.parser_.request().path == "/api/bootstrap/v1/submit" &&
                                 self.response_.status == 200 && !self.headers_.empty();
    const bool delivered_submit = submit_response && self.header_offset_ == self.headers_.size() &&
                                  self.body_offset_ == self.response_.body_size() &&
                                  self.pending_bytes_ == 0;
    if (delivered_submit) {
        self.bootstrap_submit_delivered_ = true;
        self.bootstrap_submit_delivered_ms_ = time_us_64() / 1000;
    }
#endif
    self.client_ = nullptr;
    self.parser_.reset_secure();
    self.parser_ = {};
    self.response_ = {};
    self.headers_.clear();
    self.header_offset_ = self.body_offset_ = self.pending_bytes_ = 0;
#ifndef WSPRRY_PICO_STANDALONE_RF
    if (submit_response && !delivered_submit)
        self.cancel_slot();
#endif
}

void PicoBootstrapServer::dispatch() {
#ifndef WSPRRY_PICO_STANDALONE_RF
    owner_status_committed_reply_ = false;
#endif
    if (parser_.failed())
        response_ = http_error(400, "invalid_http");
#ifndef WSPRRY_PICO_STANDALONE_RF
    else if (parser_.request().path == "/api/bootstrap/v1/status")
        response_ =
            parser_.request().method == "GET" && parser_.request().header("host") == "192.168.4.1"
                ? status()
                : http_error(400, "invalid_request");
    else if (parser_.request().path == "/api/bootstrap/v1/time" &&
             parser_.request().method == "GET")
        response_ = parser_.request().header("host") == "192.168.4.1"
                        ? json("{\"version\":1,\"challenge_ns\":\"" +
                               std::to_string(time_us_64() * 1000) + "\"}")
                        : http_error(400, "invalid_request");
    else if (parser_.request().path.starts_with("/api/bootstrap/v1/"))
        response_ = mutation(parser_.request());
    else if (parser_.request().path == "/api/owner/v1/public-status" ||
             parser_.request().path == "/api/owner/v1/claim/status")
        response_ = owner_public_get_admitted(parser_.request(), parser_.request().path)
                        ? owner_status(parser_.request().path == "/api/owner/v1/claim/status")
                        : http_error(400, "invalid_request");
    else if (parser_.request().path == "/api/owner/v1/identify" ||
             parser_.request().path.starts_with("/api/owner/v1/claim/"))
        response_ = owner_mutation(parser_.request());
#endif
    else
        response_ = bootstrap_http_response(parser_.request(), device_, firmware_
#ifndef WSPRRY_PICO_STANDALONE_RF
                                            ,
                                            active_, active_
#endif
        );
    headers_ = response_.wire_headers();
}

void PicoBootstrapServer::close(bool peer_finished) {
#ifdef WSPRRY_PICO_STANDALONE_RF
    (void)peer_finished;
#else
    const bool submit_response = bootstrap_trial_start_pending_ && !bootstrap_submit_delivered_ &&
                                 parser_.ready() &&
                                 parser_.request().path == "/api/bootstrap/v1/submit" &&
                                 response_.status == 200 && !headers_.empty();
    const bool delivered_submit = submit_response && header_offset_ == headers_.size() &&
                                  body_offset_ == response_.body_size() &&
                                  (peer_finished || pending_bytes_ == 0);
    if (delivered_submit) {
        bootstrap_submit_delivered_ = true;
        bootstrap_submit_delivered_ms_ = time_us_64() / 1000;
    }
#endif
    if (client_) {
        tcp_arg(client_, nullptr);
        tcp_recv(client_, nullptr);
        tcp_sent(client_, nullptr);
        tcp_err(client_, nullptr);
        tcp_abort(client_);
    }
    client_ = nullptr;
    parser_.reset_secure();
    parser_ = {};
    response_ = {};
    headers_.clear();
    header_offset_ = body_offset_ = pending_bytes_ = 0;
#ifndef WSPRRY_PICO_STANDALONE_RF
    if (submit_response && !delivered_submit)
        cancel_slot();
#endif
}

void PicoBootstrapServer::stop() {
    close();
    if (listener_) {
        tcp_arg(listener_, nullptr);
        tcp_accept(listener_, nullptr);
        // lwIP requires tcp_close for a LISTEN PCB; tcp_abort panics here.
        const auto closed = tcp_close(listener_);
        LWIP_ASSERT("bootstrap listener close must succeed", closed == ERR_OK);
        listener_ = nullptr;
    }
}

void PicoBootstrapServer::poll(bool active, bool mutation_safe) {
    active_ = active;
#ifdef WSPRRY_PICO_STANDALONE_RF
    (void)mutation_safe;
#endif
#ifndef WSPRRY_PICO_STANDALONE_RF
    mutation_safe_ = mutation_safe;
    const auto now_ms = time_us_64() / 1000;
    // AP/STA channel changes may briefly remove the captive listener after
    // submit. Keep the consumed trial alive until it commits or expires.
    if (!active_ && (owner_slot_.state() == provisioning::ConsumerClaimState::Identify ||
                     owner_slot_.state() == provisioning::ConsumerClaimState::Granted))
        cancel_owner_slot(true);
    if (slot_.state() != BootstrapSlotState::None &&
        slot_.state() != BootstrapSlotState::Terminal && bootstrap_commit_.cancellation_allowed() &&
        (!mutation_safe_ || !network_setup_authority()))
        cancel_slot();
    const auto before_expiry = slot_.state();
    if (bootstrap_commit_.cancellation_allowed())
        slot_.expire(now_ms);
    if (before_expiry != BootstrapSlotState::None && slot_.state() == BootstrapSlotState::None) {
        if (before_expiry == BootstrapSlotState::Trial) {
            restore_bootstrap_network();
            join_.finish();
        }
        cancel_slot();
    }
    if (slot_.state() == BootstrapSlotState::None) {
        crypto_.clear();
        slot_digest_.clear();
    }
    // Leave the AP on long enough for the browser to render the accepted POST
    // result. A station channel change can otherwise destroy that response.
    if (bootstrap_trial_start_pending_ && bootstrap_submit_delivered_ && !client_ &&
        now_ms >= bootstrap_submit_delivered_ms_ &&
        now_ms - bootstrap_submit_delivered_ms_ >= 3'000)
        start_bootstrap_trial(now_ms);
    const auto old_owner_state = owner_slot_.state();
    owner_slot_.expire(now_ms);
    if (old_owner_state != provisioning::ConsumerClaimState::None &&
        owner_slot_.state() == provisioning::ConsumerClaimState::None)
        cancel_owner_slot(true);
    if (owner_trial_start_pending_ && !client_ &&
        (owner_submit_delivered_ ||
         (now_ms >= owner_submit_ms_ && now_ms - owner_submit_ms_ >= 10'000))) {
        owner_trial_start_pending_ = false;
        claim_platform_->begin_station_trial();
        // Set before stopping the station: a failed start must restore it too.
        owner_trial_switched_network_ = true;
        network_->stop_network_only_trial();
        if (network_->start_network_only(owner_trial_.ssid, owner_trial_.password,
                                         previous_network_.time_server))
            owner_trial_active_ = true;
        else
            end_owner_trial(false, now_ms);
    }
    if (owner_trial_active_ && owner_slot_.state() == provisioning::ConsumerClaimState::Trial &&
        claim_platform_ && claim_platform_->station_ready(owner_trial_.ssid) &&
        claim_platform_->trusted_utc_now()) {
        const auto* binding = owner_slot_.binding();
        const auto result = binding && profile_ && runtime_
                                ? provisioning::commit_consumer_claim(
                                      *profile_, owner_slot_, *binding,
                                      {owner_request_id_, owner_trial_.ssid, owner_trial_.password,
                                       owner_trial_.callsign, owner_trial_.locator,
                                       owner_trial_.power_dbm, previous_network_.time_server},
                                      *claim_platform_, runtime_->source(), now_ms)
                                : provisioning::ConsumerCommitResult{};
        owner_reconcile_ = result.state == provisioning::ConsumerCommitState::Reconcile;
        if (owner_reconcile_) {
            const auto digest = owner_request_digest_;
            cancel_owner_slot(false);
            owner_request_digest_ = digest;
            owner_result_restart_.begin(profile_->sequence(), owner_request_digest_,
                                        time_us_64() / 1000);
            owner_restart_pending_ = true;
        } else {
            end_owner_trial(result.state == provisioning::ConsumerCommitState::Committed, now_ms);
            if (result.state == provisioning::ConsumerCommitState::Committed) {
                owner_result_restart_.begin(profile_->sequence(), owner_request_digest_,
                                            time_us_64() / 1000);
                owner_restart_pending_ = true;
            }
        }
    }
    if (slot_.state() == BootstrapSlotState::Trial && !bootstrap_trial_start_pending_ &&
        bootstrap_commit_.trial_allowed()) {
        const bool linked = network_ && network_->link_up();
        const auto address = linked ? network_->ipv4() : std::string{};
        const auto result = join_.trial(now_ms, linked, !address.empty() && address != "0.0.0.0");
        if (result == BootstrapJoinResult::Ready && profile_ && network_setup_authority()) {
            const auto source = profile_->source();
            std::string payload;
            if (source == provisioning::ProfileSource::NetworkOnly || blank_authority()) {
                trial_.request_sha256 = slot_.request_id_digest();
                payload = provisioning::serialize_network_profile(trial_);
            } else if (source == provisioning::ProfileSource::ConsumerProfile)
                payload = provisioning::replace_consumer_network(
                    profile_->data(), device_, trial_.ssid, trial_.password, trial_.time_server,
                    slot_.request_id_digest());
            const auto target_source = source == provisioning::ProfileSource::ConsumerProfile
                                           ? provisioning::ProfileSource::ConsumerProfile
                                           : provisioning::ProfileSource::NetworkOnly;
            const auto committed =
                bootstrap_commit_.commit(*profile_, target_source, payload, now_ms);
            volatile char* bytes = payload.empty() ? nullptr : payload.data();
            for (std::size_t i = 0; i < payload.size(); ++i)
                bytes[i] = 0;
            if (committed == provisioning::SetupCommitResult::Committed)
                end_trial(true, now_ms);
            else if (committed == provisioning::SetupCommitResult::NotCommitted)
                end_trial(false, now_ms);
            else {
                // The flash may contain a durable replacement. Do not roll back,
                // retry a save, or announce failure until reboot/readback resolves it.
                bootstrap_restart_pending_ = true;
                bootstrap_ack_delivered_ = false;
                bootstrap_committed_ms_ = now_ms;
                join_.finish();
                provisioning::scrub(trial_);
                provisioning::scrub(bootstrap_previous_network_);
                bootstrap_trial_switched_network_ = false;
                erase(ack_verifier_);
                crypto_.clear();
            }
        } else if (result == BootstrapJoinResult::TimedOut)
            end_trial(false, now_ms);
    }
    const auto restart_now_ms = time_us_64() / 1000;
    if (!client_ && bootstrap_restart_pending_ && restart_ &&
        (bootstrap_commit_.reconcile() ? bootstrap_commit_.restart_due(restart_now_ms)
                                       : (bootstrap_ack_delivered_ ||
                                          (restart_now_ms >= bootstrap_committed_ms_ &&
                                           restart_now_ms - bootstrap_committed_ms_ >= 60'000)))) {
        if (restart_(restart_context_) && !bootstrap_commit_.reconcile())
            bootstrap_restart_pending_ = false;
    }
    if (!client_ && owner_restart_pending_ && restart_ &&
        owner_result_restart_.ready(restart_now_ms)) {
        // Keep setup admission blocked until the actual reboot. A scheduled
        // restart may be cancelled by a newly accepted job; retry when safe.
        (void)restart_(restart_context_);
    }
#endif
    if (!active_) {
        // Do not leave a wildcard port-80 listener on the station interface
        // if the AP stops or the service is otherwise unavailable.
#ifndef WSPRRY_PICO_STANDALONE_RF
        if (bootstrap_trial_start_pending_)
            cancel_slot();
#endif
        stop();
        return;
    }
    if (!listener_ && !start())
        return;
    if (!client_)
        return;
    if (time_us_64() / 1000 - accepted_ms_ >= 10'000) {
        close();
        return;
    }
    if (headers_.empty())
        return;
    if (header_offset_ < headers_.size() || body_offset_ < response_.body_size()) {
        const bool header = header_offset_ < headers_.size();
        const auto body =
            header ? std::span<const std::uint8_t>{} : response_.body_at(body_offset_);
        const auto* data =
            header ? headers_.data() + header_offset_ : reinterpret_cast<const char*>(body.data());
        const auto remaining = header ? headers_.size() - header_offset_ : body.size();
        const auto count = std::min<std::size_t>({remaining, tcp_sndbuf(client_), 1024});
        if (!count)
            return;
        const auto result =
            tcp_write(client_, data, static_cast<u16_t>(count), TCP_WRITE_FLAG_COPY);
        if (result == ERR_MEM)
            return;
        if (result != ERR_OK) {
            close();
            return;
        }
        if (header)
            header_offset_ += count;
        else
            body_offset_ += count;
        pending_bytes_ += count;
        (void)tcp_output(client_);
    } else if (!pending_bytes_) {
#ifndef WSPRRY_PICO_STANDALONE_RF
        const bool delivered_owner_status =
            parser_.ready() && parser_.request().method == "GET" &&
            parser_.request().path == "/api/owner/v1/claim/status" && response_.status == 200 &&
            owner_status_committed_reply_;
        const bool delivered_owner_submit =
            parser_.ready() && parser_.request().method == "POST" &&
            parser_.request().path == "/api/owner/v1/claim/submit" && response_.status == 200 &&
            owner_trial_start_pending_;
        const bool delivered_bootstrap_submit =
            parser_.ready() && parser_.request().method == "POST" &&
            parser_.request().path == "/api/bootstrap/v1/submit" && response_.status == 200 &&
            bootstrap_trial_start_pending_;
        const bool delivered_bootstrap_ack = parser_.ready() &&
                                             parser_.request().method == "POST" &&
                                             parser_.request().path == "/api/bootstrap/v1/ack" &&
                                             response_.status == 200 && bootstrap_restart_pending_;
#endif
        auto* completed = client_;
        client_ = nullptr;
        tcp_arg(completed, nullptr);
        tcp_recv(completed, nullptr);
        tcp_sent(completed, nullptr);
        tcp_err(completed, nullptr);
        if (tcp_close(completed) != ERR_OK)
            tcp_abort(completed);
        parser_.reset_secure();
        parser_ = {};
        response_ = {};
        headers_.clear();
        header_offset_ = body_offset_ = 0;
#ifndef WSPRRY_PICO_STANDALONE_RF
        if (delivered_owner_status)
            owner_result_restart_.delivered(true, time_us_64() / 1000);
        if (delivered_owner_submit)
            owner_submit_delivered_ = true;
        if (delivered_bootstrap_submit) {
            bootstrap_submit_delivered_ = true;
            bootstrap_submit_delivered_ms_ = time_us_64() / 1000;
        }
        if (delivered_bootstrap_ack)
            bootstrap_ack_delivered_ = true;
#endif
    }
}

#ifndef WSPRRY_PICO_STANDALONE_RF
namespace {
template <std::size_t N> bool decode_hex(std::string_view text, std::array<std::uint8_t, N>& out) {
    return bootstrap_unhex(text, out);
}
template <std::size_t N> bool decode_b64(std::string_view text, std::array<std::uint8_t, N>& out) {
    std::vector<std::uint8_t> bytes;
    if (!bootstrap_unb64url(text, bytes, N, N))
        return false;
    std::copy(bytes.begin(), bytes.end(), out.begin());
    return true;
}
HttpResponse json(std::string body) {
    return {200, std::move(body), "application/json", {}};
}
std::string_view slot_name(BootstrapSlotState state) {
    switch (state) {
    case BootstrapSlotState::None:
        return "none";
    case BootstrapSlotState::Identify:
        return "identify";
    case BootstrapSlotState::Granted:
        return "granted";
    case BootstrapSlotState::Trial:
        return "trial";
    case BootstrapSlotState::Terminal:
        return "terminal";
    }
    return "none";
}
void erase(std::array<std::uint8_t, 32>& bytes) {
    volatile std::uint8_t* data = bytes.data();
    for (std::size_t i = 0; i < bytes.size(); ++i)
        data[i] = 0;
}
} // namespace

void PicoBootstrapServer::configure(
    std::string boot_id, provisioning::AccessStore& access, provisioning::ProfileStore& profile,
    provisioning::RandomSource& random, provisioning::IndicatorController& indicator,
    standalone::PicoNetwork& network, provisioning::RuntimeProfile& runtime,
    provisioning::PicoConsumerClaimPlatform& claim_platform, std::string default_password) {
    boot_id_ = std::move(boot_id);
    access_ = &access;
    profile_ = &profile;
    random_ = &random;
    indicator_ = &indicator;
    network_ = &network;
    runtime_ = &runtime;
    claim_platform_ = &claim_platform;
    default_password_ = std::move(default_password);
}

bool PicoBootstrapServer::blank_authority() const {
    if (!access_ || !profile_ || !random_ || !network_ || !indicator_ || !profile_->healthy() ||
        profile_->sequence() != 0 ||
        (profile_->source() != provisioning::ProfileSource::Unprovisioned &&
         profile_->source() != provisioning::ProfileSource::LegacyBootstrap) ||
        !profile_->data().empty() || default_password_.empty())
        return false;
    if (access_->state() == provisioning::AccessStoreState::Erased)
        return true;
    const auto* record = access_->record();
    return record && !record->reset.pending() && !record->field_mode && record->bond_count == 0 &&
           record->default_password && record->password == default_password_;
}

bool PicoBootstrapServer::network_setup_authority() const {
    if (blank_authority())
        return true;
    if (!profile_ || !runtime_ || !claim_platform_ || !profile_->healthy() ||
        (profile_->source() != provisioning::ProfileSource::NetworkOnly &&
         profile_->source() != provisioning::ProfileSource::ConsumerProfile) ||
        !profile_->sequence() ||
        profile_->sequence() == std::numeric_limits<std::uint64_t>::max() ||
        !claim_platform_->safe_to_commit())
        return false;
    return (profile_->source() == provisioning::ProfileSource::NetworkOnly &&
            runtime_->source() == provisioning::RuntimeSource::NetworkOnly &&
            runtime_->network_profile() && runtime_->network_profile()->device_id == device_) ||
           (profile_->source() == provisioning::ProfileSource::ConsumerProfile &&
            runtime_->source() == provisioning::RuntimeSource::ConsumerPreClock &&
            runtime_->consumer_profile() && runtime_->consumer_profile()->device_id == device_);
}

void PicoBootstrapServer::restore_bootstrap_network() {
    if (bootstrap_trial_switched_network_ && network_) {
        network_->stop_network_only_trial();
        if (!bootstrap_previous_network_.ssid.empty())
            (void)network_->start_network_only(bootstrap_previous_network_.ssid,
                                               bootstrap_previous_network_.password,
                                               bootstrap_previous_network_.time_server);
    }
    bootstrap_trial_switched_network_ = false;
}

void PicoBootstrapServer::cancel_slot() {
    if (slot_.state() == BootstrapSlotState::Trial)
        restore_bootstrap_network();
    join_.finish();
    slot_.cancel();
    crypto_.clear();
    slot_digest_.clear();
    erase(ack_verifier_);
    provisioning::scrub(trial_);
    provisioning::scrub(bootstrap_previous_network_);
    bootstrap_trial_start_pending_ = bootstrap_submit_delivered_ = false;
    bootstrap_submit_delivered_ms_ = 0;
}

void PicoBootstrapServer::start_bootstrap_trial(std::uint64_t now_ms) {
    bootstrap_trial_start_pending_ = bootstrap_submit_delivered_ = false;
    bootstrap_submit_delivered_ms_ = 0;
    if (!network_ || slot_.state() != BootstrapSlotState::Trial) {
        cancel_slot();
        return;
    }
    const bool reuse_connected_station = !bootstrap_previous_network_.ssid.empty() &&
                                         bootstrap_previous_network_.ssid == trial_.ssid &&
                                         bootstrap_previous_network_.password == trial_.password &&
                                         network_->station_ssid() == trial_.ssid &&
                                         network_->link_up() && !network_->ipv4().empty() &&
                                         network_->ipv4() != "0.0.0.0";
    if (!reuse_connected_station) {
        if (!bootstrap_previous_network_.ssid.empty())
            network_->stop_network_only_trial();
        bootstrap_trial_switched_network_ = true;
        if (!network_->start_network_only(trial_.ssid, trial_.password, trial_.time_server)) {
            end_trial(false, now_ms);
            return;
        }
    }
    join_.begin(now_ms);
}

void PicoBootstrapServer::end_trial(bool committed, std::uint64_t now_ms) {
    if (!committed)
        restore_bootstrap_network();
    bootstrap_trial_switched_network_ = false;
    provisioning::scrub(trial_);
    provisioning::scrub(bootstrap_previous_network_);
    if (!committed)
        erase(ack_verifier_);
    join_.finish();
    bootstrap_trial_start_pending_ = bootstrap_submit_delivered_ = false;
    bootstrap_submit_delivered_ms_ = 0;
    (void)slot_.finish(committed, now_ms);
    if (committed) {
        bootstrap_restart_pending_ = true;
        bootstrap_ack_delivered_ = false;
        bootstrap_committed_ms_ = now_ms;
    }
}

HttpResponse PicoBootstrapServer::status() const {
    const bool healthy = profile_ && profile_->healthy() && bootstrap_commit_.result_verified();
    const bool saved = healthy && profile_->source() == provisioning::ProfileSource::NetworkOnly;
    const bool consumer =
        healthy && profile_->source() == provisioning::ProfileSource::ConsumerProfile;
    const auto source = !healthy            ? "fault"
                        : saved             ? "network_only"
                        : consumer          ? "consumer"
                        : blank_authority() ? "unprovisioned"
                                            : "fault";
    const bool address = network_ && network_->link_up() && !network_->ipv4().empty() &&
                         network_->ipv4() != "0.0.0.0";
    const auto join = (saved || consumer) ? (address ? "connected" : "disconnected")
                      : slot_.state() == BootstrapSlotState::Trial    ? "connecting"
                      : slot_.state() == BootstrapSlotState::Terminal ? "failed"
                                                                      : "idle";
    // Durable generation and durable digest must come from the same journal.
    // The in-flight/failed attempt has a separate identity.
    const auto request_digest =
        profile_ ? provisioning::setup_request_digest(*profile_, device_) : std::string{};
    return json(
        "{\"version\":1,\"source\":\"" + std::string(source) + "\",\"generation\":" +
        std::to_string(healthy ? profile_->sequence() : 0) + ",\"slot_state\":\"" +
        std::string(bootstrap_commit_.reconcile() ? "reconcile" : slot_name(slot_.state())) +
        "\",\"slot_id_digest\":" +
        (slot_digest_.empty() ? "null" : wtp::json::quote(slot_digest_)) + ",\"join\":\"" + join +
        "\",\"address_ready\":" + (address ? "true" : "false") + ",\"request_id_digest\":" +
        (request_digest.empty() ? "null" : wtp::json::quote(request_digest)) +
        ",\"attempt_request_id_digest\":" +
        (slot_.request_id_digest().empty() ? "null" : wtp::json::quote(slot_.request_id_digest())) +
        "}");
}

HttpResponse PicoBootstrapServer::owner_status(bool claim_status) {
    const bool healthy = profile_ && profile_->healthy();
    const bool runtime_ok = runtime_ && runtime_->source() != provisioning::RuntimeSource::Fault;
    const auto source = healthy ? profile_->source() : provisioning::ProfileSource::LegacyBootstrap;
    const auto label = !healthy || !runtime_ok                                  ? "fault"
                       : source == provisioning::ProfileSource::ConsumerProfile ? "consumer"
                       : source == provisioning::ProfileSource::NetworkOnly     ? "network_only"
                       : source == provisioning::ProfileSource::Unprovisioned ||
                               (source == provisioning::ProfileSource::LegacyBootstrap &&
                                !profile_->sequence() && profile_->data().empty())
                           ? "unprovisioned"
                           : "fault";
    const auto generation = healthy ? profile_->sequence() : 0;
    // The runtime snapshot predates a just-committed generation. Every new
    // open-setup commit writes an empty owners list; do not report its old one.
    const bool owner_exists = runtime_ && runtime_->consumer_profile() &&
                              runtime_->generation() == generation &&
                              !runtime_->consumer_profile()->owners.empty();
    const bool address = network_ && network_->link_up() && !network_->ipv4().empty() &&
                         network_->ipv4() != "0.0.0.0";
    const bool claim_available = owner_claimable() && !owner_reconcile_ &&
                                 slot_.state() == BootstrapSlotState::None &&
                                 owner_slot_.state() == provisioning::ConsumerClaimState::None;
    std::string body =
        "{\"version\":1,\"device_id\":" + wtp::json::quote(device_) +
        ",\"boot_id\":" + wtp::json::quote(boot_id_) + ",\"source\":" + wtp::json::quote(label) +
        ",\"profile_source\":" +
        std::to_string(healthy && runtime_ok ? static_cast<unsigned>(source) : 255) +
        ",\"generation\":" + wtp::json::quote(std::to_string(generation)) + ",\"owner_exists\":" +
        (healthy && runtime_ok && source == provisioning::ProfileSource::ConsumerProfile &&
                 owner_exists
             ? "true"
             : "false") +
        ",\"claim_available\":" + (claim_available ? "true" : "false") +
        ",\"address_ready\":" + (address ? "true" : "false") + ",\"clock_ready\":" +
        (claim_platform_ && claim_platform_->trusted_utc_now() ? "true" : "false");
    if (claim_status) {
        const std::string_view request_digest =
            owner_request_digest_.empty() && runtime_ && runtime_->consumer_profile()
                ? std::string_view(runtime_->consumer_profile()->request_sha256)
                : std::string_view(owner_request_digest_);
        owner_status_committed_reply_ =
            healthy && runtime_ok && !owner_reconcile_ && owner_restart_pending_ &&
            owner_result_restart_.matches(source, generation, request_digest);
        const char* state = "none";
        switch (owner_slot_.state()) {
        case provisioning::ConsumerClaimState::None:
            break;
        case provisioning::ConsumerClaimState::Identify:
            state = "identify";
            break;
        case provisioning::ConsumerClaimState::Granted:
            state = "granted";
            break;
        case provisioning::ConsumerClaimState::Trial:
            state = "trial";
            break;
        case provisioning::ConsumerClaimState::Terminal:
            state = "terminal";
            break;
        }
        if (owner_reconcile_)
            state = "reconcile";
        body += ",\"slot_state\":" + wtp::json::quote(state) + ",\"slot_id_digest\":" +
                (owner_slot_digest_.empty() ? "null" : wtp::json::quote(owner_slot_digest_)) +
                ",\"request_id_digest\":" +
                (request_digest.empty() ? "null" : wtp::json::quote(request_digest));
    }
    body += ",\"station\":" + (healthy && runtime_ok
                                   ? owner_saved_station_json(*profile_, *runtime_, device_)
                                   : std::string("null"));
    body += '}';
    return json(std::move(body));
}

HttpResponse PicoBootstrapServer::owner_mutation(const HttpRequest& request) {
    const auto now_ms = time_us_64() / 1000;
    if (request.path == "/api/owner/v1/identify") {
        const auto parsed = parse_owner_identify(request);
        if (!parsed)
            return http_error(400, "invalid_request");
        if (!owner_claimable() || parsed->device_id != device_ || parsed->boot_id != boot_id_)
            return http_error(403, "unavailable");
        if (indicator_->identify(parsed->request_id, device_, true, true, now_ms) !=
            provisioning::IndicatorCode::Ok)
            return http_error(409, "busy");
        return json("{\"version\":1,\"device_id\":" + wtp::json::quote(device_) +
                    ",\"pattern\":\"three_short_flashes\",\"duration_ms\":10000}");
    }
    if (request.path == "/api/owner/v1/claim/start") {
        const auto parsed = parse_owner_claim_start(request);
        if (!parsed)
            return http_error(400, "invalid_request");
        if (!owner_claimable() || parsed->device_id != device_ ||
            parsed->source != profile_->source() || parsed->generation != profile_->sequence())
            return http_error(403, "unavailable");
        if (slot_.state() != BootstrapSlotState::None ||
            owner_slot_.state() != provisioning::ConsumerClaimState::None || owner_reconcile_)
            return http_error(409, "busy");
        if (!claim_platform_->valid_owner_point(parsed->owner_public_key))
            return http_error(400, "invalid_owner_key");
        std::array<std::uint8_t, 16> slot_id{};
        std::array<std::uint8_t, 65> point{};
        if (!random_->fill(slot_id) || !decode_b64(parsed->owner_public_key, point) ||
            !owner_crypto_.begin()) {
            owner_crypto_.clear();
            return http_error(503, "crypto_unavailable");
        }
        const auto slot_hex = bootstrap_hex(slot_id);
        const auto pico_public_key = bootstrap_b64url(owner_crypto_.public_key());
        if (!owner_slot_.start({device_, boot_id_, slot_hex, parsed->owner_public_key,
                                parsed->browser_public_key, parsed->browser_nonce,
                                "http://192.168.4.1", parsed->source, parsed->generation},
                               now_ms, true, false, claim_platform_->safe_to_commit())) {
            owner_crypto_.clear();
            return http_error(409, "busy");
        }
        owner_slot_digest_ = bootstrap_digest(slot_id);
        owner_request_digest_.clear();
        if (!owner_slot_.grant_open_setup(now_ms, claim_platform_->safe_to_commit())) {
            cancel_owner_slot(false);
            return http_error(503, "setup_unavailable");
        }
        if (access_ && access_->state() == provisioning::AccessStoreState::Erased) {
            provisioning::AccessRecord record;
            record.epoch = 1;
            record.password = default_password_;
            const bool initialized = !record.password.empty() && access_->initialize(record);
            provisioning::scrub(record);
            if (!initialized) {
                cancel_owner_slot(false);
                return http_error(503, "access_unavailable");
            }
        }
        return json("{\"version\":1,\"device_id\":" + wtp::json::quote(device_) + ",\"boot_id\":" +
                    wtp::json::quote(boot_id_) + ",\"slot_id\":" + wtp::json::quote(slot_hex) +
                    ",\"profile_source\":" + std::to_string(static_cast<unsigned>(parsed->source)) +
                    ",\"generation\":" + wtp::json::quote(std::to_string(parsed->generation)) +
                    ",\"owner_key_sha256\":" + wtp::json::quote(bootstrap_digest(point)) +
                    ",\"browser_public_key\":" + wtp::json::quote(parsed->browser_public_key) +
                    ",\"browser_nonce\":" + wtp::json::quote(parsed->browser_nonce) +
                    ",\"pico_public_key\":" + wtp::json::quote(pico_public_key) + "}");
    }
    if (request.path == "/api/owner/v1/claim/submit") {
        const auto parsed = parse_owner_claim_submit(request);
        if (!parsed)
            return http_error(400, "invalid_request");
        const auto* binding = owner_slot_.binding();
        if (!owner_claimable() ||
            owner_slot_.state() != provisioning::ConsumerClaimState::Granted || !binding ||
            parsed->device_id != binding->device_id || parsed->boot_id != binding->boot_id ||
            parsed->slot_id != binding->slot_id || binding->source != profile_->source() ||
            binding->generation != profile_->sequence())
            return http_error(403, "unavailable");
        // This open-AP setup slot was granted without a physical button.
        if (!owner_slot_.consume(*binding, parsed->request_id, now_ms, true,
                                 claim_platform_->safe_to_commit()))
            return http_error(409, "busy");
        owner_request_id_ = parsed->request_id;
        OwnerClaimFields fields;
        std::array<std::uint8_t, 12> nonce{};
        std::array<std::uint8_t, 16> tag{};
        std::vector<std::uint8_t> ciphertext;
        const bool decoded = decode_hex(binding->device_id, fields.device_id) &&
                             decode_hex(binding->boot_id, fields.boot_id) &&
                             decode_hex(binding->slot_id, fields.slot_id) &&
                             decode_hex(binding->browser_nonce, fields.browser_nonce) &&
                             decode_hex(parsed->request_id, fields.request_id) &&
                             decode_b64(binding->owner_public_key, fields.owner_public_key) &&
                             decode_b64(binding->browser_public_key, fields.browser_public_key) &&
                             decode_b64(parsed->aead_nonce, nonce) &&
                             decode_b64(parsed->tag, tag) &&
                             bootstrap_unb64url(parsed->ciphertext, ciphertext, 11,
                                                OwnerClaimEncodedPlaintext::max_size);
        owner_request_digest_ = bootstrap_digest(fields.request_id);
        fields.pico_public_key = owner_crypto_.public_key();
        fields.source = binding->source;
        fields.generation = binding->generation;
        if (!decoded || !owner_crypto_.open(fields, nonce, ciphertext, tag, owner_trial_)) {
            end_owner_trial(false, now_ms);
            return json("{\"version\":1,\"state\":\"failed\",\"generation\":\"0\"}");
        }
        provisioning::scrub(previous_network_);
        if (profile_->source() == provisioning::ProfileSource::NetworkOnly) {
            auto current = provisioning::parse_network_profile(profile_->data());
            if (!current || current->device_id != device_) {
                end_owner_trial(false, now_ms);
                return http_error(503, "profile_unavailable");
            }
            previous_network_ = *current;
            provisioning::scrub(*current);
        } else if (profile_->source() == provisioning::ProfileSource::ConsumerProfile) {
            // The persisted generation may have changed since the boot-time runtime snapshot.
            auto current = provisioning::parse_consumer_profile(profile_->data());
            if (!current || current->device_id != device_) {
                end_owner_trial(false, now_ms);
                return http_error(503, "profile_unavailable");
            }
            previous_network_ = {current->device_id, current->ssid, current->password,
                                 current->time_server};
            provisioning::scrub(*current);
        }
        if (owner_trial_.ssid.empty()) {
            if (!owner_trial_.password.empty() || previous_network_.ssid.empty()) {
                end_owner_trial(false, now_ms);
                return http_error(403, "network_unavailable");
            }
            owner_trial_.ssid = previous_network_.ssid;
            owner_trial_.password = previous_network_.password;
        }
        owner_trial_start_pending_ = true;
        owner_submit_delivered_ = false;
        owner_submit_ms_ = now_ms;
        return json("{\"version\":1,\"state\":\"checking\",\"generation\":\"0\","
                    "\"request_id_digest\":" +
                    wtp::json::quote(owner_request_digest_) + "}");
    }
    return http_error(404, "not_found");
}

bool PicoBootstrapServer::owner_claimable() const {
    if (owner_restart_pending_ || bootstrap_restart_pending_ || !profile_ || !runtime_ ||
        !claim_platform_ || !random_ || !indicator_ || !network_ || !profile_->healthy() ||
        !claim_platform_->safe_to_commit())
        return false;
    switch (profile_->source()) {
    case provisioning::ProfileSource::LegacyBootstrap:
    case provisioning::ProfileSource::Unprovisioned:
        return false; // Station setup begins only after Wi-Fi is saved.
    case provisioning::ProfileSource::NetworkOnly:
        return profile_->sequence() && runtime_->network_profile() &&
               runtime_->network_profile()->device_id == device_ &&
               runtime_->source() == provisioning::RuntimeSource::NetworkOnly;
    case provisioning::ProfileSource::ConsumerProfile:
        return profile_->sequence() && runtime_->consumer_profile() &&
               runtime_->consumer_profile()->device_id == device_ &&
               runtime_->source() == provisioning::RuntimeSource::ConsumerPreClock;
    default:
        return false;
    }
}

void PicoBootstrapServer::restore_owner_network() {
    if (owner_trial_switched_network_ && network_) {
        network_->stop_network_only_trial();
        if (!previous_network_.ssid.empty())
            (void)network_->start_network_only(previous_network_.ssid, previous_network_.password,
                                               previous_network_.time_server);
    }
    owner_trial_switched_network_ = false;
}

void PicoBootstrapServer::cancel_owner_slot(bool restore_network) {
    if (restore_network)
        restore_owner_network();
    owner_trial_switched_network_ = false;
    owner_slot_.cancel();
    owner_crypto_.clear();
    owner_trial_.clear();
    provisioning::scrub(previous_network_);
    owner_request_id_.clear();
    owner_slot_digest_.clear();
    // The terminal slot can expire while a response or safe restart is pending.
    // Retain its non-secret result identity until the new journal is booted.
    if (!owner_restart_pending_)
        owner_request_digest_.clear();
    owner_trial_active_ = false;
    owner_trial_start_pending_ = owner_submit_delivered_ = false;
}

void PicoBootstrapServer::end_owner_trial(bool committed, std::uint64_t now_ms) {
    if (!committed)
        restore_owner_network();
    owner_trial_switched_network_ = false;
    if (!committed && claim_platform_ && claim_platform_->safe_to_commit())
        (void)owner_slot_.finish(false, {}, 0, now_ms, true);
    else if (!committed)
        owner_slot_.cancel();
    owner_crypto_.clear();
    owner_trial_.clear();
    provisioning::scrub(previous_network_);
    owner_request_id_.clear();
    owner_trial_active_ = false;
    owner_trial_start_pending_ = owner_submit_delivered_ = false;
}

HttpResponse PicoBootstrapServer::mutation(const HttpRequest& request) {
    const auto now_ms = time_us_64() / 1000;
    if (request.path == "/api/bootstrap/v1/time") {
        const auto parsed = parse_bootstrap_time(request);
        if (!parsed)
            return http_error(400, "invalid_request");
        if (!claim_platform_ || parsed->device_id != device_)
            return http_error(403, "unavailable");
        const auto now_ns = time_us_64() * 1000;
        const bool fresh = now_ns >= parsed->challenge_ns &&
                           now_ns - parsed->challenge_ns <= time::browser_challenge_max_age_ns;
        return json(std::string("{\"version\":1,\"state\":\"") +
                    (fresh && claim_platform_->seed_browser_utc(parsed->utc_ms,
                                                                now_ns - parsed->challenge_ns)
                         ? "accepted"
                         : "ignored") +
                    "\"}");
    }
    if (bootstrap_commit_.reconcile())
        return http_error(409, "busy");
    if (owner_slot_.state() != provisioning::ConsumerClaimState::None || owner_reconcile_ ||
        owner_restart_pending_)
        return http_error(409, "busy");
    if (request.path == "/api/bootstrap/v1/start") {
        const auto parsed = parse_bootstrap_start(request);
        if (!parsed)
            return http_error(400, "invalid_request");
        if (!mutation_safe_ || !network_setup_authority() || parsed->device_id != device_)
            return http_error(403, "unavailable");
        if (slot_.state() != BootstrapSlotState::None || bootstrap_restart_pending_ ||
            !bootstrap_commit_.begin())
            return http_error(409, "busy");
        std::array<std::uint8_t, 16> slot_id{};
        std::array<std::uint8_t, 32> browser_key{};
        if (!random_->fill(slot_id) || !decode_b64(parsed->browser_public_key, browser_key) ||
            !crypto_.begin()) {
            crypto_.clear();
            return http_error(503, "crypto_unavailable");
        }
        const auto slot_hex = bootstrap_hex(slot_id);
        const auto key = bootstrap_b64url(crypto_.public_key());
        if (!slot_.start(
                {device_, boot_id_, slot_hex, parsed->browser_public_key, parsed->request_nonce},
                now_ms, true, false) ||
            !slot_.grant_open_setup(now_ms)) {
            crypto_.clear();
            return http_error(409, "busy");
        }
        slot_digest_ = bootstrap_digest(slot_id);
        if (access_ && access_->state() == provisioning::AccessStoreState::Erased) {
            provisioning::AccessRecord record;
            record.epoch = 1;
            record.password = default_password_;
            const bool initialized = access_->initialize(record);
            provisioning::scrub(record);
            if (!initialized) {
                cancel_slot();
                return http_error(503, "access_unavailable");
            }
        }
        return json("{\"version\":1,\"device_id\":" + wtp::json::quote(device_) + ",\"boot_id\":" +
                    wtp::json::quote(boot_id_) + ",\"slot_id\":" + wtp::json::quote(slot_hex) +
                    ",\"pico_public_key\":" + wtp::json::quote(key) +
                    ",\"slot_expires_in_ms\":180000}");
    }
    if (request.path == "/api/bootstrap/v1/submit") {
        const auto parsed = parse_bootstrap_submit(request);
        if (!parsed)
            return http_error(400, "invalid_request");
        if (!mutation_safe_ || !network_setup_authority() ||
            slot_.state() != BootstrapSlotState::Granted)
            return http_error(409, "busy");
        const auto* binding = slot_.binding();
        if (!binding || parsed->device_id != binding->device_id ||
            parsed->boot_id != binding->boot_id || parsed->slot_id != binding->slot_id)
            return http_error(403, "unavailable");
        BootstrapTranscriptFields transcript;
        std::array<std::uint8_t, 12> nonce{};
        std::array<std::uint8_t, 16> tag{};
        std::vector<std::uint8_t> ciphertext;
        if (!decode_hex(parsed->device_id, transcript.device_id) ||
            !decode_hex(parsed->boot_id, transcript.boot_id) ||
            !decode_hex(parsed->slot_id, transcript.slot_id) ||
            !decode_hex(binding->request_nonce, transcript.request_nonce) ||
            !decode_hex(parsed->request_id, transcript.request_id) ||
            !decode_b64(binding->browser_public_key, transcript.browser_public_key) ||
            !decode_b64(parsed->aead_nonce, nonce) || !decode_b64(parsed->tag, tag) ||
            !bootstrap_unb64url(parsed->ciphertext, ciphertext, 11, 351))
            return http_error(400, "invalid_request");
        transcript.pico_public_key = crypto_.public_key();
        const auto digest = bootstrap_digest(transcript.request_id);
        const auto box_digest = bootstrap_digest(ciphertext);
        if (!slot_.consume(parsed->device_id, parsed->boot_id, parsed->slot_id, parsed->request_id,
                           digest, box_digest, now_ms))
            return http_error(409, "busy");
        trial_.device_id = device_;
        provisioning::scrub(bootstrap_previous_network_);
        if (profile_->source() == provisioning::ProfileSource::NetworkOnly) {
            auto saved = provisioning::parse_network_profile(profile_->data());
            if (!saved || saved->device_id != device_) {
                if (saved)
                    provisioning::scrub(*saved);
                end_trial(false, now_ms);
                return http_error(503, "profile_unavailable");
            }
            bootstrap_previous_network_ = *saved;
            provisioning::scrub(*saved);
        } else if (profile_->source() == provisioning::ProfileSource::ConsumerProfile) {
            auto saved = provisioning::parse_consumer_profile(profile_->data());
            if (!saved || saved->device_id != device_) {
                if (saved)
                    provisioning::scrub(*saved);
                end_trial(false, now_ms);
                return http_error(503, "profile_unavailable");
            }
            bootstrap_previous_network_ = {saved->device_id, saved->ssid, saved->password,
                                           saved->time_server};
            provisioning::scrub(*saved);
        }
        if (!crypto_.open(transcript, nonce, ciphertext, tag, trial_.ssid, trial_.password,
                          trial_.time_server, ack_verifier_)) {
            end_trial(false, now_ms);
            return json("{\"version\":1,\"state\":\"failed\",\"generation\":0,"
                        "\"request_id_digest\":" +
                        wtp::json::quote(digest) + "}");
        }
        bootstrap_trial_start_pending_ = true;
        bootstrap_submit_delivered_ = false;
        bootstrap_submit_delivered_ms_ = 0;
        return json("{\"version\":1,\"state\":\"checking\",\"generation\":0,"
                    "\"request_id_digest\":" +
                    wtp::json::quote(digest) + "}");
    }
    if (request.path == "/api/bootstrap/v1/ack") {
        const auto parsed = parse_bootstrap_ack(request);
        if (!parsed)
            return http_error(400, "invalid_request");
        std::array<std::uint8_t, 16> slot_id{}, request_id{};
        std::array<std::uint8_t, 32> tag{};
        if (!profile_ ||
            (profile_->source() != provisioning::ProfileSource::NetworkOnly &&
             profile_->source() != provisioning::ProfileSource::ConsumerProfile) ||
            parsed->device_id != device_ || parsed->boot_id != boot_id_ ||
            !decode_hex(parsed->slot_id, slot_id) || !decode_hex(parsed->request_id, request_id) ||
            !decode_b64(parsed->ack_tag, tag) || bootstrap_digest(slot_id) != slot_digest_ ||
            bootstrap_digest(request_id) != slot_.request_id_digest())
            return http_error(403, "unavailable");
        unsigned difference = 0;
        for (std::size_t i = 0; i < tag.size(); ++i)
            difference |= tag[i] ^ ack_verifier_[i];
        if (difference || !slot_.acknowledge(true, now_ms))
            return http_error(403, "unavailable");
        erase(ack_verifier_);
        slot_digest_.clear();
        return json("{\"version\":1,\"state\":\"accepted\"}");
    }
    return http_error(404, "not_found");
}

#endif

} // namespace wsprrypico::network
