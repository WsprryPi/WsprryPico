// SPDX-License-Identifier: MIT
// Hardware-free export through the owned WTP decoder and waveform planner.
#include "rf/waveform.hpp"
#include "wtp/codec.hpp"
#include <iostream>
#include <iterator>
#include <string>
int main() {
    using namespace wsprrypico;
    const std::string raw(std::istreambuf_iterator<char>(std::cin), {});
    auto root = wtp::json::parse(raw);
    if (!root) return 1;
    const auto bytes = std::span(reinterpret_cast<const std::uint8_t*>(raw.data()), raw.size());
    auto request = wtp::decode_request(*root, "usb-physical", bytes);
    if (!request || request->operation != "LOAD") return 2;
    const auto* job = std::get_if<wtp::Job>(&request->body);
    if (!job) return 3;
    const auto plan = rf::plan_job(*job);
    if (!plan) return 4;
    std::cout << "{\"total_samples\":" << plan->total_samples << ",\"ends\":[";
    for (std::size_t n = 0; n < plan->count; ++n) {
        if (n) std::cout << ',';
        std::cout << plan->segments[n].end_sample;
    }
    std::cout << "]}\n";
}
