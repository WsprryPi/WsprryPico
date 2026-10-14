#pragma once

#include "network/api.hpp"
#include "provisioning/local_access.hpp"
#include "provisioning/runtime.hpp"
#include "provisioning/storage.hpp"

#include <array>
#include <cstdint>
#include <optional>
#include <span>
#include <string>

namespace wsprrypico::network {
// Authenticated radio management may retain an unarmed owner or loaded plan.
// Commissioning keeps its stricter unowned-only activity gate.
bool consumer_radio_network_idle(const provisioning::Activity& activity);
struct ConsumerRadioBinding {
    std::array<std::uint8_t, 16> device{}, boot{}, session{}, challenge{}, browser_nonce{};
    std::array<std::uint8_t, 32> browser_key{}, pico_key{};
    std::uint64_t generation = 0;
};

// Canonical fixed-width binding, including the NUL-terminated domain prefix.
// Shared by the portable admission tests and the target crypto adapter.
inline constexpr char consumer_radio_domain[] = "WsprryPico/Consumer-Radio/1";
inline constexpr std::size_t consumer_radio_transcript_bytes =
    sizeof(consumer_radio_domain) + 16 * 5 + 32 * 2 + 8;
std::array<std::uint8_t, consumer_radio_transcript_bytes>
consumer_radio_transcript(const ConsumerRadioBinding& binding);
inline constexpr std::size_t consumer_radio_header_bytes = 28;
inline constexpr std::size_t consumer_radio_tag_bytes = 16;
std::array<std::uint8_t, consumer_radio_header_bytes>
consumer_radio_header(std::span<const std::uint8_t, 16> session, std::uint64_t sequence);
bool consumer_radio_header_matches(wtp::InputView packet, std::span<const std::uint8_t, 16> session,
                                   std::uint64_t sequence);

class ConsumerRadioCrypto {
  public:
    virtual ~ConsumerRadioCrypto() = default;
    virtual bool begin() = 0;
    virtual std::array<std::uint8_t, 32> public_key() const = 0;
    // Consumes the ephemeral key on every attempt. Success checks the saved
    // passphrase and derives independent request/response traffic keys.
    virtual bool authenticate(wtp::FrameBuffer& packet, const ConsumerRadioBinding& binding,
                              std::string_view password) = 0;
    // Decrypts only transport-owned pages. The returned view is usable only
    // after the complete AEAD tag has authenticated.
    virtual std::optional<wtp::InputView>
    open(wtp::FrameBuffer& packet, const ConsumerRadioBinding& binding, std::uint64_t sequence) = 0;
    virtual std::optional<HttpResponse>
    seal(wtp::InputView plaintext, const ConsumerRadioBinding& binding, std::uint64_t sequence) = 0;
    virtual void clear() = 0;
};

// One bounded, volatile AP-only session. It reuses BrowserApi/JobService and
// never changes commissioning credentials or the standalone no-repeat cursor.
class ConsumerRadioApi {
  public:
    static constexpr std::uint64_t login_ms = 30'000;
    static constexpr std::uint64_t idle_ms = 5 * 60'000;
    static constexpr std::uint64_t absolute_ms = 15 * 60'000;
    ConsumerRadioApi(BrowserApi& api, provisioning::ProfileStore& store,
                     provisioning::RuntimeProfile& runtime, provisioning::RandomSource& random,
                     ConsumerRadioCrypto& crypto, std::string device, std::string boot)
        : api_(api), store_(store), runtime_(runtime), random_(random), crypto_(crypto),
          device_(std::move(device)), boot_(std::move(boot)) {}
    ~ConsumerRadioApi() {
        close();
    }
    bool available() const;
    void admission(bool open) {
        admission_open_ = open;
        if (!open)
            close();
    }
    bool active(std::uint64_t now_ms);
    void poll(std::uint64_t now_ms);
    HttpResponse handle(const HttpRequest& request, std::uint64_t now_ms,
                        std::uint64_t transaction);
    void finish_request(std::uint64_t transaction, bool apply);
    void close();

  private:
    enum class State { None, Pending, Active };
    bool admitted(const HttpRequest& request, bool binary) const;
    HttpResponse start(const HttpRequest& request, std::uint64_t now_ms);
    HttpResponse finish(const HttpRequest& request, std::uint64_t now_ms);
    HttpResponse exchange(const HttpRequest& request, std::uint64_t now_ms,
                          std::uint64_t transaction);
    BrowserApi& api_;
    provisioning::ProfileStore& store_;
    provisioning::RuntimeProfile& runtime_;
    provisioning::RandomSource& random_;
    ConsumerRadioCrypto& crypto_;
    std::string device_, boot_;
    State state_ = State::None;
    ConsumerRadioBinding binding_{};
    std::uint64_t started_ms_ = 0, seen_ms_ = 0, next_sequence_ = 1;
    std::optional<std::uint64_t> pending_transaction_;
    bool admission_open_ = false;
    std::optional<std::uint64_t> last_start_ms_;
};
} // namespace wsprrypico::network
