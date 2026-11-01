#include "network/pico/consumer_radio_crypto.hpp"

#include "mbedtls/chachapoly.h"
#include "mbedtls/hkdf.h"
#include "mbedtls/md.h"
#include "wtp/sha256.hpp"

#include <algorithm>
#include <array>
#include <cstring>

namespace wsprrypico::network {
namespace {
template <typename T> void wipe(T& value) {
    volatile std::uint8_t* bytes = reinterpret_cast<volatile std::uint8_t*>(value.data());
    for (std::size_t i = 0; i < value.size(); ++i)
        bytes[i] = 0;
}
bool equal(std::span<const std::uint8_t> a, std::span<const std::uint8_t> b) {
    if (a.size() != b.size())
        return false;
    unsigned difference = 0;
    for (std::size_t i = 0; i < a.size(); ++i)
        difference |= a[i] ^ b[i];
    return difference == 0;
}
std::array<std::uint8_t, 12> nonce(std::uint64_t sequence) {
    std::array<std::uint8_t, 12> result{};
    for (unsigned i = 0; i < 8; ++i)
        result[4 + i] = static_cast<std::uint8_t>(sequence >> (56 - i * 8));
    return result;
}
bool derive(std::span<const std::uint8_t> secret, std::span<const std::uint8_t, 32> salt,
            std::string_view info, std::span<std::uint8_t> key) {
    const auto* md = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
    return md && mbedtls_hkdf(md, salt.data(), salt.size(), secret.data(), secret.size(),
                              reinterpret_cast<const unsigned char*>(info.data()), info.size(),
                              key.data(), key.size()) == 0;
}
std::array<std::uint8_t, 60> aad(const ConsumerRadioBinding& binding, std::uint64_t sequence) {
    std::array<std::uint8_t, 60> result{};
    const auto digest = consumer_radio_digest(binding);
    const auto header = consumer_radio_header(binding.session, sequence);
    std::copy(digest.begin(), digest.end(), result.begin());
    std::copy(header.begin(), header.end(), result.begin() + 32);
    return result;
}
} // namespace

bool PicoConsumerRadioCrypto::create(std::span<const std::uint8_t> private_key) {
    clear();
    if (psa_.acquire() != PSA_SUCCESS)
        return false;
    psa_key_attributes_t attributes = PSA_KEY_ATTRIBUTES_INIT;
    psa_set_key_type(&attributes, PSA_KEY_TYPE_ECC_KEY_PAIR(PSA_ECC_FAMILY_MONTGOMERY));
    psa_set_key_bits(&attributes, 255);
    psa_set_key_usage_flags(&attributes, PSA_KEY_USAGE_DERIVE);
    psa_set_key_algorithm(&attributes, PSA_ALG_ECDH);
    const auto made = private_key.empty() ? psa_generate_key(&attributes, &private_key_)
                                          : psa_import_key(&attributes, private_key.data(),
                                                           private_key.size(), &private_key_);
    psa_reset_key_attributes(&attributes);
    std::size_t size = 0;
    if (made != PSA_SUCCESS ||
        psa_export_public_key(private_key_, public_key_.data(), public_key_.size(), &size) !=
            PSA_SUCCESS ||
        size != public_key_.size()) {
        clear();
        return false;
    }
    return true;
}
bool PicoConsumerRadioCrypto::begin() {
    return create({});
}
#ifdef WSPRRY_PICO_CONSUMER_RADIO_CRYPTO_TEST
bool PicoConsumerRadioCrypto::begin_for_test(std::span<const std::uint8_t, 32> key) {
    return create(key);
}
#endif

std::optional<wtp::InputView>
PicoConsumerRadioCrypto::decrypt(wtp::FrameBuffer& packet, const ConsumerRadioBinding& binding,
                                 std::uint64_t sequence, std::span<const std::uint8_t, 32> key) {
    if (!consumer_radio_header_matches(packet.view(), binding.session, sequence))
        return {};
    const auto size = packet.size() - consumer_radio_header_bytes - consumer_radio_tag_bytes;
    std::array<std::uint8_t, 16> tag{}, calculated{};
    for (std::size_t i = 0; i < tag.size(); ++i)
        tag[i] = packet[packet.size() - tag.size() + i];
    const auto iv = nonce(sequence);
    const auto associated = aad(binding, sequence);
    mbedtls_chachapoly_context context;
    mbedtls_chachapoly_init(&context);
    bool valid = mbedtls_chachapoly_setkey(&context, key.data()) == 0 &&
                 mbedtls_chachapoly_starts(&context, iv.data(), MBEDTLS_CHACHAPOLY_DECRYPT) == 0 &&
                 mbedtls_chachapoly_update_aad(&context, associated.data(), associated.size()) == 0;
    std::size_t offset = 0;
    while (valid && offset < size) {
        auto part = packet.mutable_at(consumer_radio_header_bytes + offset);
        part = part.first(std::min(part.size(), size - offset));
        valid = mbedtls_chachapoly_update(&context, part.size(), part.data(), part.data()) == 0;
        offset += part.size();
    }
    valid = valid && mbedtls_chachapoly_finish(&context, calculated.data()) == 0 &&
            equal(tag, calculated);
    mbedtls_chachapoly_free(&context);
    wipe(calculated);
    wipe(tag);
    if (!valid) {
        // Decrypted bytes never reach JSON/application parsing on a bad tag.
        for (std::size_t at = 0; at < packet.size();) {
            auto part = packet.mutable_at(at);
            std::fill(part.begin(), part.end(), 0);
            at += part.size();
        }
        return {};
    }
    return packet.view().substr(consumer_radio_header_bytes, size);
}
bool PicoConsumerRadioCrypto::authenticate(wtp::FrameBuffer& packet,
                                           const ConsumerRadioBinding& binding,
                                           std::string_view password) {
    if (!private_key_ || password.size() < 8 || password.size() > 63 ||
        binding.pico_key != public_key_) {
        clear();
        return false;
    }
    std::array<std::uint8_t, 32> shared{}, login_key{};
    std::array<std::uint8_t, 64> secret{}, traffic{};
    transcript_hash_ = consumer_radio_digest(binding);
    std::size_t size = 0;
    bool valid = psa_raw_key_agreement(PSA_ALG_ECDH, private_key_, binding.browser_key.data(),
                                       binding.browser_key.size(), shared.data(), shared.size(),
                                       &size) == PSA_SUCCESS &&
                 size == shared.size() &&
                 std::any_of(shared.begin(), shared.end(), [](std::uint8_t b) { return b; });
    valid = (psa_destroy_key(private_key_) == PSA_SUCCESS) && valid;
    private_key_ = 0;
    auto password_hash = wtp::sha256(
        std::span(reinterpret_cast<const std::uint8_t*>(password.data()), password.size()));
    std::copy(shared.begin(), shared.end(), secret.begin());
    std::copy(password_hash.begin(), password_hash.end(), secret.begin() + 32);
    if (valid)
        valid = derive(secret, transcript_hash_, "WsprryPico radio login v1", login_key);
    const auto plaintext = valid ? decrypt(packet, binding, 0, login_key) : std::nullopt;
    valid = plaintext && plaintext->size() == transcript_hash_.size();
    unsigned difference = 0;
    if (valid)
        for (std::size_t i = 0; i < transcript_hash_.size(); ++i)
            difference |= static_cast<unsigned char>((*plaintext)[i]) ^ transcript_hash_[i];
    valid = valid && difference == 0;
    if (valid) {
        valid = derive(secret, transcript_hash_, "WsprryPico radio traffic v1", traffic);
    }
    if (valid) {
        std::copy_n(traffic.begin(), 32, request_key_.begin());
        std::copy_n(traffic.begin() + 32, 32, response_key_.begin());
        authenticated_ = true;
    }
    // Login plaintext is sensitive even on a correct passphrase.
    for (std::size_t at = 0; at < packet.size();) {
        auto part = packet.mutable_at(at);
        std::fill(part.begin(), part.end(), 0);
        at += part.size();
    }
    wipe(shared);
    wipe(login_key);
    wipe(secret);
    wipe(traffic);
    wipe(password_hash);
    psa_.release();
    if (!valid)
        clear();
    return valid;
}
std::optional<wtp::InputView> PicoConsumerRadioCrypto::open(wtp::FrameBuffer& packet,
                                                            const ConsumerRadioBinding& binding,
                                                            std::uint64_t sequence) {
    if (!authenticated_ || !sequence || transcript_hash_ != consumer_radio_digest(binding))
        return {};
    return decrypt(packet, binding, sequence, request_key_);
}
std::optional<HttpResponse>
PicoConsumerRadioCrypto::seal_parts(std::span<const wtp::InputView> plaintext,
                                    const ConsumerRadioBinding& binding, std::uint64_t sequence) {
    std::size_t size = 0;
    for (const auto part : plaintext) {
        if (part.size() >
            max_http_body - consumer_radio_header_bytes - consumer_radio_tag_bytes - size)
            return {};
        size += part.size();
    }
    if (!authenticated_ || transcript_hash_ != consumer_radio_digest(binding))
        return {};
    HttpResponse response{200, "", "application/octet-stream", {}};
    const auto header = consumer_radio_header(binding.session, sequence);
    if (!response.buffered_body.reserve(header.size() + size + 16) ||
        !response.buffered_body.append(header))
        return {};
    const auto iv = nonce(sequence);
    const auto associated = aad(binding, sequence);
    mbedtls_chachapoly_context context;
    mbedtls_chachapoly_init(&context);
    bool valid = mbedtls_chachapoly_setkey(&context, response_key_.data()) == 0 &&
                 mbedtls_chachapoly_starts(&context, iv.data(), MBEDTLS_CHACHAPOLY_ENCRYPT) == 0 &&
                 mbedtls_chachapoly_update_aad(&context, associated.data(), associated.size()) == 0;
    std::array<std::uint8_t, 1024> bytes{};
    std::array<std::uint8_t, 16> tag{};
    for (const auto view : plaintext) {
        for (std::size_t at = 0; valid && at < view.size();) {
            auto part = view.at(at);
            part = part.first(std::min(part.size(), bytes.size()));
            valid =
                mbedtls_chachapoly_update(&context, part.size(), part.data(), bytes.data()) == 0 &&
                response.buffered_body.append(std::span(bytes).first(part.size()));
            at += part.size();
        }
    }
    valid = valid && mbedtls_chachapoly_finish(&context, tag.data()) == 0 &&
            response.buffered_body.append(tag);
    mbedtls_chachapoly_free(&context);
    wipe(bytes);
    wipe(tag);
    if (!valid)
        return {};
    return response;
}
std::optional<HttpResponse>
PicoConsumerRadioCrypto::seal_buffer(wtp::OutputBuffer plaintext,
                                     const ConsumerRadioBinding& binding, std::uint64_t sequence) {
    const auto size = plaintext.size();
    if (!authenticated_ ||
        size > max_http_body - consumer_radio_header_bytes - consumer_radio_tag_bytes ||
        transcript_hash_ != consumer_radio_digest(binding))
        return {};
    const auto header = consumer_radio_header(binding.session, sequence);
    if (!plaintext.reserve(header.size() + size + consumer_radio_tag_bytes) ||
        !plaintext.prepend(header))
        return {};
    const auto iv = nonce(sequence);
    const auto associated = aad(binding, sequence);
    mbedtls_chachapoly_context context;
    mbedtls_chachapoly_init(&context);
    bool valid = mbedtls_chachapoly_setkey(&context, response_key_.data()) == 0 &&
                 mbedtls_chachapoly_starts(&context, iv.data(), MBEDTLS_CHACHAPOLY_ENCRYPT) == 0 &&
                 mbedtls_chachapoly_update_aad(&context, associated.data(), associated.size()) == 0;
    for (std::size_t at = header.size(); valid && at < header.size() + size;) {
        auto part = plaintext.mutable_at(at);
        valid = mbedtls_chachapoly_update(&context, part.size(), part.data(), part.data()) == 0;
        at += part.size();
    }
    std::array<std::uint8_t, consumer_radio_tag_bytes> tag{};
    valid = valid && mbedtls_chachapoly_finish(&context, tag.data()) == 0 && plaintext.append(tag);
    mbedtls_chachapoly_free(&context);
    wipe(tag);
    if (!valid)
        return {};
    return HttpResponse{200, "", "application/octet-stream", {}, std::move(plaintext)};
}
namespace {
class CipherResponseSource final : public wtp::ResponseSource {
  public:
    CipherResponseSource(wtp::ResponseSourcePtr plaintext, std::span<const std::uint8_t, 32> key,
                         const ConsumerRadioBinding& binding, std::uint64_t sequence)
        : plaintext_(std::move(plaintext)),
          header_(consumer_radio_header(binding.session, sequence)) {
        plaintext_->release_output();
        mbedtls_chachapoly_init(&context_);
        const auto iv = nonce(sequence);
        const auto associated = aad(binding, sequence);
        valid_ =
            mbedtls_chachapoly_setkey(&context_, key.data()) == 0 &&
            mbedtls_chachapoly_starts(&context_, iv.data(), MBEDTLS_CHACHAPOLY_ENCRYPT) == 0 &&
            mbedtls_chachapoly_update_aad(&context_, associated.data(), associated.size()) == 0;
    }
    ~CipherResponseSource() override {
        mbedtls_chachapoly_free(&context_);
        wipe(tag_);
    }
    bool replayable() const override {
        return false;
    }
    bool valid() const {
        return valid_;
    }
    std::size_t size() const override {
        return header_.size() + plaintext_->size() + tag_.size();
    }
    std::size_t copy(std::size_t offset, std::span<std::uint8_t> out) const override {
        // ResponseSource::at retains partial writes/retries. Only that window
        // owner may advance this non-replayable cipher; plaintext stays replayable.
        if (!valid_ || offset != cursor_)
            return 0;
        std::size_t done = 0;
        while (done < out.size() && cursor_ < size()) {
            if (cursor_ < header_.size()) {
                const auto n = std::min(out.size() - done, header_.size() - cursor_);
                std::copy_n(header_.begin() + cursor_, n, out.begin() + done);
                cursor_ += n;
                done += n;
            } else if (cursor_ < header_.size() + plaintext_->size()) {
                std::array<std::uint8_t, window_bytes> scratch{};
                const auto n = plaintext_->copy(
                    cursor_ - header_.size(),
                    std::span(scratch).first(std::min(scratch.size(), out.size() - done)));
                valid_ = n && mbedtls_chachapoly_update(&context_, n, scratch.data(),
                                                        out.data() + done) == 0;
                wipe(scratch);
                if (!valid_)
                    return 0;
                cursor_ += n;
                done += n;
            } else {
                if (!finished_) {
                    valid_ = mbedtls_chachapoly_finish(&context_, tag_.data()) == 0;
                    if (!valid_)
                        return 0;
                    finished_ = true;
                }
                const auto at = cursor_ - header_.size() - plaintext_->size();
                const auto n = std::min(out.size() - done, tag_.size() - at);
                std::copy_n(tag_.begin() + at, n, out.begin() + done);
                cursor_ += n;
                done += n;
            }
        }
        return done;
    }

  private:
    wtp::ResponseSourcePtr plaintext_;
    std::array<std::uint8_t, consumer_radio_header_bytes> header_;
    mutable std::array<std::uint8_t, consumer_radio_tag_bytes> tag_{};
    mutable mbedtls_chachapoly_context context_{};
    mutable std::size_t cursor_ = 0;
    mutable bool valid_ = false, finished_ = false;
};
} // namespace
std::optional<HttpResponse>
PicoConsumerRadioCrypto::seal_source(wtp::ResponseSourcePtr plaintext,
                                     const ConsumerRadioBinding& binding, std::uint64_t sequence) {
    if (!plaintext || !authenticated_ || transcript_hash_ != consumer_radio_digest(binding) ||
        plaintext->size() > max_http_body - consumer_radio_header_bytes - consumer_radio_tag_bytes)
        return {};
    auto source = wtp::make_response_source<CipherResponseSource>(std::move(plaintext),
                                                                  response_key_, binding, sequence);
    if (!source || !source->valid())
        return {};
    HttpResponse response{200, {}, "application/octet-stream", {}};
    response.generated_body = std::move(source);
    return response;
}
void PicoConsumerRadioCrypto::clear() {
    if (private_key_) {
        (void)psa_destroy_key(private_key_);
        private_key_ = 0;
    }
    wipe(public_key_);
    wipe(request_key_);
    wipe(response_key_);
    wipe(transcript_hash_);
    authenticated_ = false;
    psa_.release();
}
} // namespace wsprrypico::network
