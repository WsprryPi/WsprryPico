#include "network/pico/bootstrap_server.hpp"

#include "network/bootstrap_http.hpp"
#ifndef WSPRRY_PICO_STANDALONE_RF
#include "network/bootstrap_codec.hpp"
#include "network/bootstrap_wire.hpp"
#include "provisioning/access.hpp"
#include "provisioning/field_runtime.hpp"
#include "provisioning/local_access.hpp"
#include "provisioning/pico/bootsel_sampler.hpp"
#include "provisioning/storage.hpp"
#include "standalone/pico/adapters.hpp"
#include "wtp/json.hpp"
#endif
#include "pico/time.h"

#include <algorithm>
#include <cstring>
#include <vector>

namespace wsprrypico::network {
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
        self.close();
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
    if (packet->tot_len > bytes.size())
        return ERR_MEM;
    const auto count = pbuf_copy_partial(packet, bytes.data(), packet->tot_len, 0);
    pbuf_free(packet);
    tcp_recved(self.client_, count);
    (void)self.parser_.receive(std::span(bytes).first(count));
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
    self.client_ = nullptr;
    self.parser_.reset_secure();
    self.parser_ = {};
    self.response_ = {};
    self.headers_.clear();
    self.header_offset_ = self.body_offset_ = self.pending_bytes_ = 0;
}

void PicoBootstrapServer::dispatch() {
    if (parser_.failed())
        response_ = http_error(400, "invalid_http");
#ifndef WSPRRY_PICO_STANDALONE_RF
    else if (parser_.request().path == "/api/bootstrap/v1/status")
        response_ =
            parser_.request().method == "GET" && parser_.request().header("host") == "192.168.4.1"
                ? status()
                : http_error(400, "invalid_request");
    else if (parser_.request().path.starts_with("/api/bootstrap/v1/"))
        response_ = mutation(parser_.request());
#endif
    else
        response_ = bootstrap_http_response(parser_.request(), device_, firmware_
#ifndef WSPRRY_PICO_STANDALONE_RF
                                            ,
                                            blank_authority() && mutation_safe_
#endif
        );
    headers_ = response_.wire_headers();
}

void PicoBootstrapServer::close() {
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
    if (slot_.state() != BootstrapSlotState::None &&
        slot_.state() != BootstrapSlotState::Terminal && (!mutation_safe_ || !blank_authority()))
        cancel_slot();
    const auto before_expiry = slot_.state();
    slot_.expire(now_ms);
    if (before_expiry != BootstrapSlotState::None && slot_.state() == BootstrapSlotState::None) {
        if (before_expiry == BootstrapSlotState::Trial) {
            network_->stop_network_only_trial();
            join_.finish(false);
        }
        cancel_slot();
    }
    if (slot_.state() == BootstrapSlotState::None) {
        crypto_.clear();
        slot_digest_.clear();
    }
    if (active_ && slot_.state() == BootstrapSlotState::Identify &&
        (last_sample_ms_ == 0 || now_ms - last_sample_ms_ >= 25)) {
        last_sample_ms_ = now_ms;
        const auto sample = provisioning::sample_runtime_bootsel();
        slot_.sample(now_ms, sample.safe, sample.pressed);
        if (slot_.state() == BootstrapSlotState::Granted && access_ &&
            access_->state() == provisioning::AccessStoreState::Erased) {
            provisioning::AccessRecord record;
            record.epoch = 1;
            record.password = default_password_;
            const bool initialized = access_->initialize(record);
            provisioning::scrub(record);
            if (!initialized)
                cancel_slot();
        }
    }
    if (slot_.state() == BootstrapSlotState::Trial) {
        const bool linked = network_ && network_->link_up();
        const auto address = linked ? network_->ipv4() : std::string{};
        const auto result = join_.trial(now_ms, linked, !address.empty() && address != "0.0.0.0");
        if (result == BootstrapJoinResult::Ready && profile_ && blank_authority()) {
            auto payload = provisioning::serialize_network_profile(trial_);
            const bool committed =
                !payload.empty() &&
                profile_->select(provisioning::ProfileSource::NetworkOnly, payload) &&
                profile_->healthy() &&
                profile_->source() == provisioning::ProfileSource::NetworkOnly &&
                profile_->sequence() == 1;
            volatile char* bytes = payload.empty() ? nullptr : payload.data();
            for (std::size_t i = 0; i < payload.size(); ++i)
                bytes[i] = 0;
            if (committed)
                end_trial(true, now_ms);
            else
                end_trial(false, now_ms);
        } else if (result == BootstrapJoinResult::TimedOut)
            end_trial(false, now_ms);
    }
    const bool linked = network_ && network_->link_up();
    const auto address = linked ? network_->ipv4() : std::string{};
    join_.service(now_ms, linked, !address.empty() && address != "0.0.0.0");
#endif
    if (!active_) {
        // Do not leave a wildcard port-80 listener on the station interface
        // after the captive AP withdraws. Fallback reopens it on AP return.
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

void PicoBootstrapServer::configure(std::string boot_id, provisioning::AccessStore& access,
                                    provisioning::ProfileStore& profile,
                                    provisioning::RandomSource& random,
                                    provisioning::IndicatorController& indicator,
                                    standalone::PicoNetwork& network,
                                    std::string default_password) {
    boot_id_ = std::move(boot_id);
    access_ = &access;
    profile_ = &profile;
    random_ = &random;
    indicator_ = &indicator;
    network_ = &network;
    default_password_ = std::move(default_password);
    if (profile.healthy() && profile.source() == provisioning::ProfileSource::NetworkOnly)
        join_.finish(true); // Reboot preserves the durable record, not the ACK.
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

void PicoBootstrapServer::cancel_slot() {
    if (slot_.state() == BootstrapSlotState::Trial && network_) {
        network_->stop_network_only_trial();
        join_.finish(false);
    }
    slot_.cancel();
    crypto_.clear();
    slot_digest_.clear();
    erase(ack_verifier_);
    provisioning::scrub(trial_);
}

void PicoBootstrapServer::end_trial(bool committed, std::uint64_t now_ms) {
    if (!committed && network_)
        network_->stop_network_only_trial();
    provisioning::scrub(trial_);
    if (!committed)
        erase(ack_verifier_);
    join_.finish(committed);
    (void)slot_.finish(committed, now_ms);
}

HttpResponse PicoBootstrapServer::status() const {
    const bool healthy = profile_ && profile_->healthy();
    const bool saved = healthy && profile_->source() == provisioning::ProfileSource::NetworkOnly;
    const auto source = !healthy            ? "fault"
                        : saved             ? "network_only"
                        : blank_authority() ? "unprovisioned"
                                            : "fault";
    const bool address = network_ && network_->link_up() && !network_->ipv4().empty() &&
                         network_->ipv4() != "0.0.0.0";
    const auto join = saved ? (address ? "connected" : "disconnected")
                      : slot_.state() == BootstrapSlotState::Trial    ? "connecting"
                      : slot_.state() == BootstrapSlotState::Terminal ? "failed"
                                                                      : "idle";
    return json(
        "{\"version\":1,\"source\":\"" + std::string(source) +
        "\",\"generation\":" + std::to_string(healthy ? profile_->sequence() : 0) +
        ",\"slot_state\":\"" + std::string(slot_name(slot_.state())) + "\",\"slot_id_digest\":" +
        (slot_digest_.empty() ? "null" : wtp::json::quote(slot_digest_)) + ",\"join\":\"" + join +
        "\",\"address_ready\":" + (address ? "true" : "false") + ",\"request_id_digest\":" +
        (slot_.request_id_digest().empty() ? "null" : wtp::json::quote(slot_.request_id_digest())) +
        "}");
}

HttpResponse PicoBootstrapServer::mutation(const HttpRequest& request) {
    const auto now_ms = time_us_64() / 1000;
    if (request.path == "/api/bootstrap/v1/start") {
        const auto parsed = parse_bootstrap_start(request);
        if (!parsed)
            return http_error(400, "invalid_request");
        if (!mutation_safe_ || !blank_authority() || parsed->device_id != device_)
            return http_error(403, "unavailable");
        if (slot_.state() != BootstrapSlotState::None)
            return http_error(409, "busy");
        const auto sample = provisioning::sample_runtime_bootsel();
        if (!sample.safe || sample.pressed)
            return http_error(503, "button_unavailable");
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
                now_ms, sample.safe, sample.pressed)) {
            crypto_.clear();
            return http_error(409, "busy");
        }
        slot_digest_ = bootstrap_digest(slot_id);
        if (indicator_->identify(slot_hex, device_, true, true, now_ms) !=
            provisioning::IndicatorCode::Ok) {
            cancel_slot();
            return http_error(503, "indicator_unavailable");
        }
        return json("{\"version\":1,\"device_id\":" + wtp::json::quote(device_) + ",\"boot_id\":" +
                    wtp::json::quote(boot_id_) + ",\"slot_id\":" + wtp::json::quote(slot_hex) +
                    ",\"pico_public_key\":" + wtp::json::quote(key) +
                    ",\"tap_expires_in_ms\":60000,\"slot_expires_in_ms\":180000}");
    }
    if (request.path == "/api/bootstrap/v1/submit") {
        const auto parsed = parse_bootstrap_submit(request);
        if (!parsed)
            return http_error(400, "invalid_request");
        if (!mutation_safe_ || !blank_authority() || slot_.state() != BootstrapSlotState::Granted)
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
            !bootstrap_unb64url(parsed->ciphertext, ciphertext, 11, 97))
            return http_error(400, "invalid_request");
        transcript.pico_public_key = crypto_.public_key();
        const auto digest = bootstrap_digest(transcript.request_id);
        const auto box_digest = bootstrap_digest(ciphertext);
        if (!slot_.consume(parsed->device_id, parsed->boot_id, parsed->slot_id, parsed->request_id,
                           digest, box_digest, now_ms))
            return http_error(409, "busy");
        trial_.device_id = device_;
        if (!crypto_.open(transcript, nonce, ciphertext, tag, trial_.ssid, trial_.password,
                          ack_verifier_) ||
            !network_->start_network_only(trial_.ssid, trial_.password)) {
            end_trial(false, now_ms);
            return json("{\"version\":1,\"state\":\"failed\",\"generation\":0,"
                        "\"request_id_digest\":" +
                        wtp::json::quote(digest) + "}");
        }
        join_.begin(now_ms);
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
        if (!profile_ || profile_->source() != provisioning::ProfileSource::NetworkOnly ||
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
        acked_ = true;
        erase(ack_verifier_);
        slot_digest_.clear();
        return json("{\"version\":1,\"state\":\"accepted\"}");
    }
    return http_error(404, "not_found");
}

bool PicoBootstrapServer::withdraw_ready() const {
    if (!profile_ || profile_->source() != provisioning::ProfileSource::NetworkOnly || !network_ ||
        !network_->link_up() || client_)
        return false;
    const auto now_ms = time_us_64() / 1000;
    return join_.withdraw(now_ms, acked_, false);
}
#endif

} // namespace wsprrypico::network
