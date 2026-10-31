#include "mbedtls/chachapoly.h"
#include "mbedtls/platform.h"
#include "network/bootstrap_codec.hpp"
#include "network/control.hpp"
#include "network/pico/consumer_radio_crypto.hpp"
#include "network_support.hpp"
#include "response_metrics_support.hpp"
#include "wtp/codec.hpp"
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
    assert(crypto.begin_for_test(private_key));
    auto login = packet(field(*root, "login_hex"));
    assert(crypto.authenticate(login, binding, password));
    for (std::size_t count : {162, 256}) {
        wtp::Request request;
        request.operation = "LOAD";
        request.request_id = std::string(32, 'a');
        wtp::Response result;
        result.ok = true;
        result.job_id = std::string(32, 'b');
        std::vector<wtp::FrequencyAdjustment> values;
        for (std::size_t i = 0; i < count; ++i)
            values.push_back({i, 14097100000000000ULL + (i % 4) * 1464843750ULL,
                              14097100000000001ULL + (i % 4) * 1464843750ULL});
        result.adjustments = std::move(values);
        wtp::allocate_input = probe::alloc;
        wtp::deallocate_input = probe::release;
        probe::start();
        {
            network::HttpResponse response{200, {}, "application/json", {}};
#if __has_include("wtp/response_source.hpp")
            response.generated_body = wtp::load_response_source(request, result);
#else
            response.buffered_body = wtp::encode_load_response_buffer(request, result, true);
#endif
            response = network::control_response(std::move(response));
            const std::string prefix = "{\"status\":200,\"etag\":null,\"body\":";
            std::optional<network::HttpResponse> sealed;
#if __has_include("wtp/response_source.hpp")
            auto source = wtp::make_response_source<wtp::JoinedResponseSource>(
                prefix, network::response_source(std::move(response)), "}", true);
            sealed = crypto.seal_source(std::move(source), binding, count);
#else
            auto envelope = std::move(response.buffered_body);
            const auto size = prefix.size() + envelope.size() + 1;
            assert(envelope.reserve(size + 44));
            assert(envelope.prepend(wtp::InputView(prefix).at(0)));
            assert(envelope.append(wtp::InputView("}").at(0)));
            sealed = crypto.seal_buffer(std::move(envelope), binding, count);
#endif
            assert(sealed);
            probe::step(probe::started);
            std::uint64_t digest = 14695981039346656037ULL;
            for (std::size_t offset = 0; offset < sealed->body_size();) {
                const auto before = std::chrono::steady_clock::now();
                const auto part = sealed->body_at(offset);
                probe::step(before);
                assert(!part.empty());
                for (auto c : part) {
                    digest ^= c;
                    digest *= 1099511628211ULL;
                }
                offset += part.size();
            }
            char label[80];
            std::snprintf(label, sizeof(label), "encrypted-http-load-%zu", count);
            probe::report(label, sealed->body_size());
            std::printf("digest=%llu\n", static_cast<unsigned long long>(digest));
        }
        assert(probe::live == 0);
        wtp::allocate_input = std::malloc;
        wtp::deallocate_input = std::free;
    }
}
