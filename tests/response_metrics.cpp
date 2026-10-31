#include "network_support.hpp"
#include "standalone/progress.hpp"
#include "usb/management_endpoint.hpp"
#include "wtp/codec.hpp"

#include <chrono>
#include <cstddef>
#include <cstdio>
#include <new>
using namespace wsprrypico;
#include "response_metrics_support.hpp"
int main() {
    wtp::allocate_input = probe::alloc;
    wtp::deallocate_input = probe::release;
    network_test::Fixture f;
    network_test::Flash flash;
    standalone::Progress progress(flash);
    if (!progress.load())
        return 2;
    f.api.progress_settings(progress);
    if (f.scheduler.command("CONFIG " + network_test::config).find("true") == std::string::npos)
        return 3;
    for (const auto name : {"capabilities", "application", "progress", "hardware", "status",
                            "operations", "config", "station", "pins", "filter-selector"}) {
        network::HttpRequest q{"GET",
                               "/api/control/v1/" + std::string(name),
                               "",
                               {{"host", "127.0.0.1:8443"}, {"origin", "https://127.0.0.1:8443"}}};
        probe::start();
        {
            auto r = f.api.handle(q, "research", "127.0.0.1:8443");
            probe::step(probe::started);
            if (r.status != 200) {
                probe::tracking = false;
                std::printf("%s status=%u\n", name, r.status);
            } else {
                std::uint64_t digest = 14695981039346656037ULL;
                for (std::size_t offset = 0; offset < r.body_size();) {
                    const auto before = std::chrono::steady_clock::now();
                    const auto part = r.body_at(offset);
                    probe::step(before);
                    if (part.empty())
                        return 8;
                    for (auto c : part) {
                        digest ^= c;
                        digest *= 1099511628211ULL;
                    }
                    offset += part.size();
                }
                probe::report(name, r.body_size());
                std::printf("digest=%llu\n", static_cast<unsigned long long>(digest));
            }
        }
    }
    for (const std::size_t n : {0, 1, 16, 17, 32, 33, 162, 256, 512}) {
        wtp::Request q;
        q.operation = "LOAD";
        q.request_id = std::string(32, '1');
        q.session_id = std::string(32, '2');
        wtp::Response s;
        s.ok = true;
        s.boot_id = std::string(32, '3');
        s.job_id = std::string(32, '4');
        std::vector<wtp::FrequencyAdjustment> a;
        for (std::size_t i = 0; i < n; ++i)
            a.push_back({i, 14097100000000000ULL + (i % 4) * 1464843750ULL,
                         14097100000000001ULL + (i % 4) * 1464843750ULL});
        s.adjustments = std::move(a);
        char label[80];
        std::snprintf(label, sizeof(label), "http-load-%zu", n);
        probe::start();
        {
            network::HttpResponse r{200, {}, "application/json", {}};
#if __has_include("wtp/response_source.hpp")
            r = network::browser_load_response(q, s);
#else
            r.buffered_body = wtp::encode_load_response_buffer(q, s, true);
#endif
            probe::step(probe::started);
            std::uint64_t digest = 14695981039346656037ULL;
            for (std::size_t offset = 0; offset < r.body_size();) {
                const auto before = std::chrono::steady_clock::now();
                auto p = r.body_at(offset);
                probe::step(before);
                if (p.empty())
                    return 8;
                for (auto b : p) {
                    digest ^= b;
                    digest *= 1099511628211ULL;
                }
                offset += p.size();
            }
            probe::report(label, r.body_size());
            std::printf("digest=%llu\n", static_cast<unsigned long long>(digest));
        }
    }
    // Production USB framing and escaping with identical frozen response bytes.
    struct UsbCase {
        std::size_t size;
        bool generated;
    };
    for (const auto fixture :
         {UsbCase{512, false}, UsbCase{18000, false}, UsbCase{28000, false}, UsbCase{0, true},
          UsbCase{1, true}, UsbCase{16, true}, UsbCase{17, true}, UsbCase{32, true},
          UsbCase{33, true}, UsbCase{162, true}, UsbCase{256, true}, UsbCase{512, true}}) {
        const auto size = fixture.size;
        const bool generated = fixture.generated;
        wtp::Request job_request;
        job_request.operation = "LOAD";
        job_request.request_id = std::string(32, '1');
        wtp::Response job_response;
        job_response.ok = true;
        job_response.job_id = std::string(32, '4');
        if (generated) {
            std::vector<wtp::FrequencyAdjustment> adjustments;
            const auto count = size;
            for (std::size_t i = 0; i < count; ++i)
                adjustments.push_back({i, 14097100000000000ULL + (i % 4) * 1464843750ULL,
                                       14097100000000001ULL + (i % 4) * 1464843750ULL});
            job_response.adjustments = std::move(adjustments);
        }
        const std::string payload = "{\"data\":\"" + std::string(size, 'x') + "\"}";
        usb::ManagementEndpoint endpoint(
            std::string(32, 'a'), std::string(32, 'b'), "test",
            [&](const network::HttpRequest&, std::uint64_t) {
                if (!generated)
                    return network::HttpResponse{200, payload, "application/json", {}};
                network::HttpResponse result{200, {}, "application/json", {}};
#if __has_include("wtp/response_source.hpp")
                result = network::browser_load_response(job_request, job_response);
#else
                result.buffered_body =
                    wtp::encode_load_response_buffer(job_request, job_response, true);
#endif
                return result;
            },
            [](std::uint64_t, bool) {});
        endpoint.connect(std::string(32, 'c'));
        const auto send = [&](const std::string& body) {
            std::string wire = "UMP1";
            for (int shift : {24, 16, 8, 0})
                wire.push_back(static_cast<char>(body.size() >> shift));
            wire += body;
            endpoint.receive({reinterpret_cast<const std::uint8_t*>(wire.data()), wire.size()}, 1);
        };
        send("{\"schema\":\"usb-management/1\",\"id\":1,\"operation\":\"hello\"}");
        while (!endpoint.output().empty())
            endpoint.consume_output(endpoint.output().size());
        const std::string request =
            "{\"schema\":\"usb-management/1\",\"id\":2,\"operation\":\"request\",\"session\":\"" +
            std::string(32, 'c') + "\",\"target\":{\"scope\":\"member\",\"device_id\":\"" +
            std::string(32, 'a') + "\",\"boot_id\":\"" + std::string(32, 'b') +
            "\"},\"method\":\"GET\",\"path\":\"/api/control/v1/"
            "config\",\"body\":\"\",\"if_match\":\"\"}";
        char label[80];
        std::snprintf(label, sizeof(label), generated ? "usb-load-%zu" : "usb-%zu", size);
        probe::start();
        send(request);
        probe::step(probe::started);
        if (endpoint.closed())
            return 9;
        for (unsigned step = 0; endpoint.output().empty() && step < 65; ++step) {
            const auto before = std::chrono::steady_clock::now();
            endpoint.poll(1);
            probe::step(before);
        }
        if (endpoint.output().empty())
            return 10;
        std::size_t bytes = 0;
        std::uint64_t digest = 14695981039346656037ULL;
        while (!endpoint.output().empty()) {
            const auto before = std::chrono::steady_clock::now();
            const auto p = endpoint.output();
            probe::step(before);
            const auto count = std::min<std::size_t>(37, p.size());
            for (auto b : p.first(count)) {
                digest ^= b;
                digest *= 1099511628211ULL;
            }
            bytes += count;
            endpoint.consume_output(count);
        }
        probe::report(label, bytes);
        std::printf("digest=%llu\n", static_cast<unsigned long long>(digest));
    }
}
