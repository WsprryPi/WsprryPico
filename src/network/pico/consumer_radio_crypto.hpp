#pragma once

#include "network/consumer_radio.hpp"
#include "network/pico/psa_lifetime.hpp"

namespace wsprrypico::network {
class PicoConsumerRadioCrypto final : public ConsumerRadioCrypto {
  public:
    ~PicoConsumerRadioCrypto() override {
        clear();
    }
    bool begin() override;
#ifdef WSPRRY_PICO_CONSUMER_RADIO_CRYPTO_TEST
    bool begin_for_test(std::span<const std::uint8_t, 32> private_key);
#endif
    std::array<std::uint8_t, 32> public_key() const override {
        return public_key_;
    }
    bool authenticate(wtp::FrameBuffer& packet, const ConsumerRadioBinding& binding,
                      std::string_view password) override;
    std::optional<wtp::InputView> open(wtp::FrameBuffer& packet,
                                       const ConsumerRadioBinding& binding,
                                       std::uint64_t sequence) override;
    std::optional<HttpResponse> seal_parts(std::span<const wtp::InputView> plaintext,
                                           const ConsumerRadioBinding& binding,
                                           std::uint64_t sequence) override;
    std::optional<HttpResponse> seal_buffer(wtp::OutputBuffer plaintext,
                                            const ConsumerRadioBinding& binding,
                                            std::uint64_t sequence) override;
    void clear() override;

  private:
    bool create(std::span<const std::uint8_t> private_key);
    std::optional<wtp::InputView> decrypt(wtp::FrameBuffer& packet,
                                          const ConsumerRadioBinding& binding,
                                          std::uint64_t sequence,
                                          std::span<const std::uint8_t, 32> key);
    PsaCryptoOwner psa_;
    psa_key_id_t private_key_ = 0;
    std::array<std::uint8_t, 32> public_key_{}, request_key_{}, response_key_{}, transcript_hash_{};
    bool authenticated_ = false;
};
} // namespace wsprrypico::network
