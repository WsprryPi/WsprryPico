#pragma once

#include "network/api.hpp"
#include "provisioning/local_access.hpp"
#include "provisioning/runtime.hpp"
#include "provisioning/storage.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <optional>
#include <span>
#include <string>

namespace wsprrypico::network {
// Authenticated radio management may retain an unarmed owner or loaded plan.
// Commissioning keeps its stricter unowned-only activity gate.
bool consumer_radio_network_idle(const provisioning::Activity& activity);
enum class ConsumerInterface { None, AccessPoint, Station };
struct ConsumerRadioBinding {
    std::array<std::uint8_t, 16> device{}, boot{}, session{}, challenge{}, browser_nonce{};
    std::array<std::uint8_t, 32> browser_key{}, pico_key{};
    std::uint64_t generation = 0;
    // Zero for the frozen Radio/1 transcript. Recovery/1 binds its separate
    // purpose and exact retirement scope without changing Radio/1 vectors.
    std::array<std::uint8_t, 32> recovery_context{};
};

// Canonical fixed-width binding, including the NUL-terminated domain prefix.
// Shared by the portable admission tests and the target crypto adapter.
inline constexpr char consumer_radio_domain[] = "WsprryPico/Consumer-Radio/1";
inline constexpr std::size_t consumer_radio_transcript_bytes =
    sizeof(consumer_radio_domain) + 16 * 5 + 32 * 2 + 8;
std::array<std::uint8_t, consumer_radio_transcript_bytes>
consumer_radio_transcript(const ConsumerRadioBinding& binding);
std::array<std::uint8_t, 32> consumer_radio_digest(const ConsumerRadioBinding& binding);
std::array<std::uint8_t, 16> consumer_recovery_selector(const ConsumerRadioBinding& binding);
std::array<std::uint8_t, 32> consumer_recovery_context(std::span<const std::uint8_t, 16> target,
                                                       ConsumerInterface interface,
                                                       std::string_view authority);
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

// Fixed volatile interface/origin-bound sessions. They reuse BrowserApi/
// JobService and the existing transactional setup authority; it owns no cursor.
class ConsumerRadioApi {
  public:
    static constexpr std::size_t session_capacity = 3;
    static constexpr std::size_t pending_capacity = 1;
    static constexpr std::uint64_t login_ms = 30'000;
    static constexpr std::uint64_t idle_ms = 30 * 60'000;
    static constexpr std::uint64_t absolute_ms = 8 * 60 * 60'000;
    ConsumerRadioApi(BrowserApi& api, provisioning::ProfileStore& store,
                     provisioning::RuntimeProfile& runtime, provisioning::RandomSource& random,
                     const std::array<ConsumerRadioCrypto*, session_capacity>& crypto,
                     std::string device, std::string boot, ConsumerRadioCrypto* recovery = nullptr)
        : api_(api), store_(store), runtime_(runtime), random_(random), device_(std::move(device)),
          boot_(std::move(boot)) {
        // Reject aliased injection without clearing another slot's keys.
        for (std::size_t i = 0; i < crypto.size(); ++i) {
            if (!crypto[i])
                return;
            for (std::size_t j = 0; j < i; ++j)
                if (crypto[i] == crypto[j])
                    return;
        }
        for (std::size_t i = 0; i < crypto.size(); ++i)
            sessions_[i].crypto = crypto[i];
        if (recovery && std::none_of(crypto.begin(), crypto.end(),
                                     [recovery](auto* c) { return c == recovery; }))
            recovery_.crypto = recovery;
    }
    ConsumerRadioApi(const ConsumerRadioApi&) = delete;
    ConsumerRadioApi& operator=(const ConsumerRadioApi&) = delete;
    ~ConsumerRadioApi() {
        close();
    }
    bool available() const;
    void password_storage(provisioning::AccessStore& store,
                          std::string_view initial_field_password) {
        password_store_ = &store;
        initial_field_password_ = initial_field_password;
        password_sequence_ = store.sequence();
        password_digest_ = password_digest();
    }
    void listeners(bool ap, std::string_view station_ip, std::string_view hostname);
    bool page_admitted(const HttpRequest& request, ConsumerInterface interface) const;
    using SetupHandler = HttpResponse (*)(const HttpRequest&, std::uint64_t,
                                          std::span<const std::uint8_t, 16>, void*);
    using SetupDelivery = void (*)(std::uint64_t, bool, void*);
    using SetupBusy = bool (*)(void*);
    using SetupClosed = void (*)(std::span<const std::uint8_t, 16>, void*);
    void setup_handler(SetupHandler handler, SetupDelivery delivery, void* context,
                       SetupBusy busy = nullptr, SetupClosed closed = nullptr) {
        setup_handler_ = handler;
        setup_delivery_ = delivery;
        setup_context_ = context;
        setup_busy_ = busy;
        setup_closed_ = closed;
    }
    void admission(bool open) {
        admission_open_ = open;
        if (!open)
            close();
    }
    bool active(std::uint64_t now_ms);
    void poll(std::uint64_t now_ms);
    HttpResponse handle(const HttpRequest& request, std::uint64_t now_ms, std::uint64_t transaction,
                        ConsumerInterface interface = ConsumerInterface::AccessPoint);
    void finish_request(std::uint64_t transaction, bool apply);
    void close();

  private:
    friend struct ConsumerRadioTestAccess;
    enum class State { None, Pending, Active };
    struct Session {
        ConsumerRadioCrypto* crypto = nullptr;
        State state = State::None;
        ConsumerRadioBinding binding{};
        std::uint64_t started_ms = 0, seen_ms = 0, next_sequence = 1;
        std::optional<std::uint64_t> pending_transaction;
        std::string authority;
        ConsumerInterface interface = ConsumerInterface::None;
    };
    void close(Session& session);
    std::string_view authentication_password() const;
    HttpResponse password_resource(const HttpRequest& request);
    std::array<std::uint8_t, 32> password_digest() const;
    Session* select(wtp::InputView packet);
    bool admitted(const HttpRequest& request, bool binary) const;
    HttpResponse start(const HttpRequest& request, std::uint64_t now_ms,
                       ConsumerInterface interface);
    HttpResponse finish(Session& session, const HttpRequest& request, std::uint64_t now_ms);
    HttpResponse exchange(Session& session, const HttpRequest& request, std::uint64_t now_ms,
                          std::uint64_t transaction);
    HttpResponse recovery_start(const HttpRequest&, std::uint64_t, ConsumerInterface);
    HttpResponse recovery_finish(const HttpRequest&, ConsumerInterface);
    HttpResponse recovery_discovery(const HttpRequest&, ConsumerInterface) const;
    BrowserApi& api_;
    provisioning::ProfileStore& store_;
    provisioning::RuntimeProfile& runtime_;
    provisioning::RandomSource& random_;
    std::string device_, boot_;
    std::array<Session, session_capacity> sessions_{};
    Session recovery_{}; // Pending proof only; never an application session.
    std::array<std::uint8_t, 16> recovery_target_{};
    std::optional<std::uint64_t> last_recovery_ms_;
    std::uint64_t session_serial_ = 0;
    bool admission_open_ = false;
    provisioning::AccessStore* password_store_ = nullptr;
    std::string initial_field_password_;
    std::uint64_t password_sequence_ = 0;
    std::array<std::uint8_t, 32> password_digest_{};
    std::optional<std::uint64_t> last_start_ms_;
    bool ap_available_ = false;
    std::string station_ip_, hostname_;
    SetupHandler setup_handler_ = nullptr;
    SetupDelivery setup_delivery_ = nullptr;
    SetupBusy setup_busy_ = nullptr;
    SetupClosed setup_closed_ = nullptr;
    void* setup_context_ = nullptr;
};
} // namespace wsprrypico::network
