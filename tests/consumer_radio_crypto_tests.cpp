#include "mbedtls/chachapoly.h"
#include "mbedtls/platform.h"
#include "network/bootstrap_codec.hpp"
#include "network/pico/consumer_radio_crypto.hpp"
#include "wtp/json.hpp"
#include "wtp/sha256.hpp"

#include <algorithm>
#include <cassert>
#include <chrono>
#include <fstream>
#include <random>
#include <vector>
using namespace wsprrypico;
extern "C" mbedtls_ms_time_t mbedtls_ms_time(void) {
    using namespace std::chrono;
    return duration_cast<milliseconds>(steady_clock::now().time_since_epoch()).count();
}
extern "C" int mbedtls_hardware_poll(void*, unsigned char* out, std::size_t count,
                                     std::size_t* received) {
    std::random_device random;
    for (std::size_t i = 0; i < count; ++i)
        out[i] = static_cast<unsigned char>(random());
    *received = count;
    return 0;
}
namespace {
std::string field(wtp::json::Value root, std::string_view name) {
    auto value = root.get(name);
    assert(value);
    return value->string();
}
std::vector<std::uint8_t> unhex(std::string_view value) {
    assert(value.size() % 2 == 0);
    std::vector<std::uint8_t> bytes;
    for (std::size_t i = 0; i < value.size(); i += 2)
        bytes.push_back(
            static_cast<std::uint8_t>(std::stoul(std::string(value.substr(i, 2)), nullptr, 16)));
    return bytes;
}
wtp::FrameBuffer packet(std::string_view input) {
    auto bytes = unhex(input);
    wtp::FrameBuffer result;
    assert(result.reserve(bytes.size()));
    result.append(bytes);
    return result;
}
} // namespace
int main(int argc, char** argv) {
    assert(argc == 2);
    std::ifstream stream(argv[1]);
    std::string bytes(std::istreambuf_iterator<char>{stream}, {});
    auto root = wtp::json::parse(bytes);
    assert(root);
    network::ConsumerRadioBinding binding;
    assert(network::bootstrap_unhex(field(*root, "device_id"), binding.device));
    assert(network::bootstrap_unhex(field(*root, "boot_id"), binding.boot));
    assert(network::bootstrap_unhex(field(*root, "session_id"), binding.session));
    assert(network::bootstrap_unhex(field(*root, "challenge"), binding.challenge));
    assert(network::bootstrap_unhex(field(*root, "browser_nonce"), binding.browser_nonce));
    std::vector<std::uint8_t> key;
    assert(network::bootstrap_unb64url(field(*root, "browser_public_key"), key, 32, 32));
    std::copy(key.begin(), key.end(), binding.browser_key.begin());
    assert(network::bootstrap_unb64url(field(*root, "pico_public_key"), key, 32, 32));
    std::copy(key.begin(), key.end(), binding.pico_key.begin());
    binding.generation = std::stoull(field(*root, "generation"));
    if (root->get("selector_for_session_id"))
        assert(network::bootstrap_hex(network::consumer_recovery_selector(binding)) ==
               field(*root, "selector_for_session_id"));
    if (const auto recovery = root->get("recovery")) {
        std::array<std::uint8_t, 16> target{};
        assert(network::bootstrap_unhex(field(*recovery, "target_selector"), target));
        binding.recovery_context = network::consumer_recovery_context(
            target,
            field(*recovery, "interface") == "ap" ? network::ConsumerInterface::AccessPoint
                                                  : network::ConsumerInterface::Station,
            field(*recovery, "authority"));
    }
    const auto hash = network::consumer_radio_digest(binding);
    assert(network::bootstrap_hex(hash) == field(*root, "transcript_sha256"));
    std::array<std::uint8_t, 32> private_key{};
    assert(network::bootstrap_unhex(field(*root, "pico_private_key_hex"), private_key));
    const auto password = field(*root, "password");
    network::PicoConsumerRadioCrypto crypto;
    const auto login = [&]() {
        assert(crypto.begin_for_test(private_key));
        assert(crypto.public_key() == binding.pico_key);
        auto request = packet(field(*root, "login_hex"));
        assert(crypto.authenticate(request, binding, password));
        assert(std::all_of(request.begin(), request.end(), [](char c) { return c == 0; }));
        assert(!crypto.authenticate(request, binding,
                                    password)); // consumed private key closes attempt
        assert(crypto.begin_for_test(private_key));
        request = packet(field(*root, "login_hex"));
        assert(crypto.authenticate(request, binding, password));
        assert(network::PsaCryptoOwner::owners() == 0);
    };
    login();
    auto request = packet(field(*root, "request_hex"));
    auto plain = crypto.open(request, binding, 1);
    assert(plain && *plain == field(*root, "request_plain"));
    auto response = crypto.seal(field(*root, "response_plain"), binding, 1);
    assert(response);
    const auto expected_response = unhex(field(*root, "response_hex"));
    assert(response->body_text() ==
           std::string(expected_response.begin(), expected_response.end()));
    const auto response_plain = field(*root, "response_plain");
    const wtp::InputView response_view(response_plain);
    const std::array<wtp::InputView, 4> parts{
        response_view.substr(0, 1), {}, response_view.substr(1, 7), response_view.substr(8)};
    auto segmented = crypto.seal_parts(parts, binding, 1);
    assert(segmented && segmented->body_text() == response->body_text());
    wtp::OutputBuffer owned;
    assert(owned.reserve(response_plain.size()) && owned.append(response_view.at(0)));
    auto inplace = crypto.seal_buffer(std::move(owned), binding, 1);
    assert(inplace && inplace->body_text() == response->body_text());
    std::array<std::uint8_t, 32> request_key{};
    assert(network::bootstrap_unhex(field(*root, "request_key_hex"), request_key));
    const auto large_plain = "{\"pad\":\"" + std::string(32714, 'x') + "\"}";
    const auto large_header = network::consumer_radio_header(binding.session, 2);
    std::array<std::uint8_t, 12> large_nonce{};
    large_nonce.back() = 2;
    std::array<std::uint8_t, 60> large_aad{};
    std::copy(hash.begin(), hash.end(), large_aad.begin());
    std::copy(large_header.begin(), large_header.end(), large_aad.begin() + 32);
    std::vector<std::uint8_t> large_bytes(32768);
    std::copy(large_header.begin(), large_header.end(), large_bytes.begin());
    mbedtls_chachapoly_context context;
    mbedtls_chachapoly_init(&context);
    assert(mbedtls_chachapoly_setkey(&context, request_key.data()) == 0);
    assert(mbedtls_chachapoly_encrypt_and_tag(
               &context, large_plain.size(), large_nonce.data(), large_aad.data(), large_aad.size(),
               reinterpret_cast<const unsigned char*>(large_plain.data()), large_bytes.data() + 28,
               large_bytes.data() + 32752) == 0);
    mbedtls_chachapoly_free(&context);
    assert(network::bootstrap_hex(wtp::sha256(large_bytes)) ==
           field(*root, "large_request_sha256"));
    wtp::FrameBuffer large;
    assert(large.reserve(large_bytes.size()));
    large.append(large_bytes);
    auto opened = crypto.open(large, binding, 2);
    assert(opened && opened->size() == 32724 && wtp::json::parse(*opened));
    // A maximum-size paged reply and boundaries inside cipher blocks must
    // produce exactly the same authenticated bytes as one contiguous value.
    auto large_response = crypto.seal(large_plain, binding, 2);
    const std::array<wtp::InputView, 4> large_parts{
        opened->substr(0, 3), opened->substr(3, 4100), {}, opened->substr(4103)};
    auto large_segmented = crypto.seal_parts(large_parts, binding, 2);
    assert(large_response && large_segmented &&
           large_response->body_text() == large_segmented->body_text());
    assert(owned.reserve(large_plain.size()));
    assert(owned.append(wtp::InputView(large_plain).at(0)));
    inplace = crypto.seal_buffer(std::move(owned), binding, 2);
    assert(inplace && inplace->body_text() == large_response->body_text());
    // The streaming cipher owns its state across session retirement and emits
    // exactly the existing packet, including partial writes inside cipher blocks.
    auto streamed = crypto.seal_source(
        wtp::make_response_source<wtp::TextResponseSource>(large_plain), binding, 2);
    assert(streamed && streamed->body_size() == large_response->body_size());
    const auto expected_stream = large_response->body_text();
    crypto.clear();
    std::string actual_stream;
    const auto allocator = wtp::allocate_input;
    wtp::allocate_input = [](std::size_t) -> void* { return nullptr; };
    while (actual_stream.size() < streamed->body_size()) {
        const auto part = streamed->body_at(actual_stream.size());
        assert(!part.empty() && part.size() <= 1024);
        assert(streamed->body_at(actual_stream.size()).data() == part.data());
        actual_stream.push_back(static_cast<char>(part.front()));
    }
    wtp::allocate_input = allocator;
    assert(actual_stream == expected_stream);
    // A forward-only packet cannot be replayed after its first window is gone.
    // Convenience serializers must return failure instead of spinning forever.
    assert(streamed->body_text().empty());
    assert(streamed->wire().empty());
    login();
    const std::array<wtp::InputView, 2> oversized{*opened, wtp::InputView(" ")};
    assert(!crypto.seal_parts(oversized, binding, 2));
    auto altered = binding;
    ++altered.generation;
    request = packet(field(*root, "request_hex"));
    assert(!crypto.open(request, altered, 1));
    assert(!crypto.open(request, binding, 2));
    request = packet(field(*root, "request_hex"));
    request.mutable_at(30)[0] ^= 1;
    assert(!crypto.open(request, binding, 1));
    assert(std::all_of(request.begin(), request.end(), [](char c) { return c == 0; }));
    crypto.clear();
    assert(!crypto.seal("{}", binding, 1));
    assert(crypto.begin_for_test(private_key));
    request = packet(field(*root, "login_hex"));
    assert(!crypto.authenticate(request, binding, "wrong-password"));
    assert(network::PsaCryptoOwner::owners() == 0);
    assert(std::all_of(request.begin(), request.end(), [](char c) { return c == 0; }));
    assert(!crypto.authenticate(request, binding, password));
}
