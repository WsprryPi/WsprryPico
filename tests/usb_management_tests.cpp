#include "standalone/wtp_profile.hpp"
#include "usb/management_endpoint.hpp"
#include "usb/time_exchange.hpp"
#include "wtp/memory_budget.hpp"

#include <cstdlib>
#include <iostream>

#define CHECK(x)                                                                                   \
    do {                                                                                           \
        if (!(x)) {                                                                                \
            std::cerr << __LINE__ << ": " << #x << '\n';                                           \
            std::exit(1);                                                                          \
        }                                                                                          \
    } while (false)
using namespace wsprrypico;
namespace {
const std::string device(32, 'a'), boot(32, 'b'), session(32, 'c');
std::string frame(std::string body) {
    const auto n = body.size();
    std::string wire = "UMP1";
    for (int shift : {24, 16, 8, 0})
        wire.push_back(static_cast<char>(n >> shift));
    return wire + body;
}
std::string common(unsigned id, std::string_view operation) {
    return "{\"schema\":\"usb-management/1\",\"id\":" + std::to_string(id) +
           ",\"operation\":" + wtp::json::quote(operation);
}
std::string bound(unsigned id, std::string_view operation) {
    return common(id, operation) + ",\"session\":" + wtp::json::quote(session) +
           ",\"target\":{\"scope\":\"member\",\"device_id\":" + wtp::json::quote(device) +
           ",\"boot_id\":" + wtp::json::quote(boot) + "}";
}
void send(usb::ManagementEndpoint& endpoint, std::string body, std::uint64_t now = 1) {
    const auto wire = frame(std::move(body));
    // Every possible header boundary and UTF-8 byte is fragmented.
    for (auto byte : wire) {
        const auto b = static_cast<std::uint8_t>(byte);
        CHECK(endpoint.receive({&b, 1}, now) == 1);
        if (endpoint.closed())
            break;
    }
}
std::string drain(usb::ManagementEndpoint& endpoint) {
    std::string result;
    while (!endpoint.output().empty()) {
        const auto part = endpoint.output();
        // Short writes must retain exact suffixes, even inside escaped text.
        const auto count = std::min<std::size_t>(3, part.size());
        result.append(reinterpret_cast<const char*>(part.data()), count);
        endpoint.consume_output(count);
    }
    CHECK(result.starts_with("UMP1"));
    const auto payload = result.substr(8);
    std::size_t length = 0;
    for (unsigned i = 4; i < 8; ++i)
        length = length * 256 + static_cast<unsigned char>(result[i]);
    CHECK(length == payload.size());
    CHECK(wtp::json::parse(payload));
    return payload;
}
std::uint64_t now_ns = 0;
std::uint64_t clock_now(void*) {
    return now_ns;
}
std::size_t free_memory() {
    return usb::ManagementEndpoint::memory_reserve;
}
usb::ManagementEndpoint* reclaim_endpoint = nullptr;
std::size_t priority_free = 0;
unsigned priority_reclaims = 0;
std::size_t priority_memory() {
    return priority_free;
}
void reclaim_management() {
    ++priority_reclaims;
    // A cleanup callback cannot recursively spend or reclaim the same reserve.
    CHECK(!wtp::authoritative_memory_admitted(65536));
    reclaim_endpoint->disconnect();
    priority_free = 128824;
}
network::HttpRequest time_request(std::string method, std::string path, std::string body = {}) {
    network::HttpRequest r;
    r.method = std::move(method);
    r.path = std::move(path);
    r.body = std::move(body);
    return r;
}
} // namespace
int main() {
    unsigned handled = 0, delivered = 0, cancelled = 0;
    std::uint64_t last_transaction = 0;
    usb::ManagementEndpoint endpoint(
        device, boot, "test",
        [&](const network::HttpRequest& request, std::uint64_t transaction) {
            ++handled;
            CHECK(request.method == "GET");
            last_transaction = transaction;
            return network::HttpResponse{200, "{\"text\":\"name π \\\"ok\\\"\"}",
                                         "application/json", "revision"};
        },
        [&](std::uint64_t transaction, bool success) {
            CHECK(transaction == last_transaction);
            if (success)
                ++delivered;
            else
                ++cancelled;
        });
    const auto hello = [&] {
        endpoint.connect(session);
        send(endpoint, common(1, "hello") + "}");
        CHECK(!endpoint.closed());
        const auto reply = drain(endpoint);
        CHECK(reply.find("usb-management-discovery/1") != std::string::npos);
    };
    const auto request = [&](unsigned id) {
        send(
            endpoint,
            bound(id, "request") +
                ",\"method\":\"GET\",\"path\":\"/api/v1/status\",\"body\":\"\",\"if_match\":\"\"}");
    };
    hello();
    request(2);
    CHECK(handled == 1 && delivered == 0);
    const auto response = drain(endpoint);
    const auto parsed = wtp::json::parse(response);
    CHECK(parsed->get("delivery_required")->boolean());
    CHECK(parsed->get("etag")->string() == "revision");
    CHECK(wtp::json::parse(parsed->get("body")->string()));
    send(endpoint, bound(2, "ack") + "}");
    CHECK(delivered == 1);
    (void)drain(endpoint);
    request(3);
    (void)drain(endpoint);
    endpoint.disconnect();
    CHECK(cancelled == 1 && delivered == 1);
    hello();
    request(2);
    (void)drain(endpoint);
    endpoint.poll(10'001);
    CHECK(endpoint.closed() && cancelled == 2);
    hello();
    request(2);
    (void)drain(endpoint);
    auto wrong = bound(2, "ack") + "}";
    wrong.replace(wrong.find(session), session.size(), std::string(32, 'd'));
    send(endpoint, wrong);
    CHECK(endpoint.closed() && cancelled == 3 && delivered == 1);
    hello();
    send(endpoint, common(2, "hello") + ",\"id\":3}");
    CHECK(endpoint.closed()); // Duplicate member never reaches dispatch.
    hello();
    wtp::available_memory = free_memory;
    request(2);
    CHECK(endpoint.closed()); // Management cannot spend the WTP reserve.
    wtp::available_memory = nullptr;

    // Optional input, queued response and undelivered ACK state yield to the
    // original WTP budgets. Generic JSON admission never frees its own input.
    reclaim_endpoint = &endpoint;
    for (unsigned stage = 0; stage != 3; ++stage) {
        hello();
        const auto before_cancelled = cancelled;
        if (stage == 0) {
            const std::array<std::uint8_t, 8> header{'U', 'M', 'P', '1', 0, 0, 0x80, 0};
            CHECK(endpoint.receive(header, 1) == header.size());
        } else {
            request(2);
            if (stage == 2)
                (void)drain(endpoint);
        }
        const auto before_reclaims = priority_reclaims;
        priority_free = 32768;
        wtp::available_memory = priority_memory;
        wtp::reclaim_optional_memory = reclaim_management;
        CHECK(!wtp::memory_admitted(65536));
        CHECK(priority_reclaims == before_reclaims && !endpoint.closed());
        CHECK(wtp::authoritative_input_memory_admitted(65536));
        CHECK(priority_reclaims == before_reclaims + 1 && endpoint.closed());
        CHECK(cancelled == before_cancelled + (stage ? 1 : 0));
        CHECK(delivered == 1);
        wtp::reclaim_optional_memory = nullptr;
        wtp::available_memory = nullptr;
    }

    time::UtcDiscipline clock(clock_now, nullptr, standalone::clock_profile());
    time::ControllerTimeArbiter arbiter(clock, clock_now, nullptr, device);
    usb::TimeExchange time(arbiter, clock_now, nullptr);
    constexpr std::uint64_t utc = 1'800'000'000'000'000'000ULL;
    auto sample = time.handle(time_request("GET", "/api/usb/v1/time/sample"), 20);
    CHECK(sample.status == 200);
    const auto body = [&](std::string token, std::uint64_t uncertainty = 1'000'000) {
        return "{\"sample\":" + wtp::json::quote(token) +
               ",\"utc_ns\":" + wtp::json::quote(std::to_string(utc + now_ns)) +
               ",\"uncertainty_ns\":" + wtp::json::quote(std::to_string(uncertainty)) +
               ",\"leap\":\"normal\"}";
    };
    CHECK(time.handle(time_request("POST", "/api/usb/v1/time/submit", body("wrong")), 21).status ==
          409);
    CHECK(time.handle(time_request("POST", "/api/usb/v1/time/submit", body("20")), 22).status ==
          409);
    (void)time.handle(time_request("GET", "/api/usb/v1/time/sample"), 23);
    CHECK(time.handle(time_request("POST", "/api/usb/v1/time/submit", body("23")), 24).status ==
          200);
    CHECK(arbiter.status().principal == "usb-physical");
    CHECK(clock.snapshot().state == wtp::ClockState::Synchronized);
    (void)time.handle(time_request("GET", "/api/usb/v1/time/sample"), 25);
    now_ns += 2'000'000'001ULL;
    CHECK(time.handle(time_request("POST", "/api/usb/v1/time/submit", body("25")), 26).status ==
          409);
    CHECK(arbiter.observe(time::ObservationSource::Sntp, utc + now_ns, now_ns, 1'000'000,
                          wtp::LeapState::Normal, {}));
    (void)time.handle(time_request("GET", "/api/usb/v1/time/sample"), 27);
    const auto preferred =
        time.handle(time_request("POST", "/api/usb/v1/time/submit", body("27")), 28);
    CHECK(preferred.status == 200 &&
          preferred.body.find("\"selected\":false") != std::string::npos);
    time.reset();
    CHECK(arbiter.status().source == time::ActiveTimeSource::Sntp);
    CHECK(standalone::wtp_profile(true).max_events == 512);
    CHECK(standalone::wtp_profile(true).max_job_duration_ns == 3'600'000'000'000ULL);
    CHECK(standalone::wtp_profile(true).maximum_arm_uncertainty_ns == 500'000'000ULL);
    CHECK(standalone::wtp_profile(true).maximum_holdover_age_ns == 3'600'000'000'000ULL);
    std::cout << "USB framing, ACK ownership, memory refusal and time lifecycle passed\n";
}
