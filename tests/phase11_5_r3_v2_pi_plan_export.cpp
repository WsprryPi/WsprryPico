// SPDX-License-Identifier: MIT
// Host-only export through the real WsprryPi compiler, adapter and WTP codec.
// Link against the explicitly identified companion source; opens no transport.
#include "WSPR-Transmitter/src/execution_plan_compiler.hpp"
#include "wtp_integration/execution_plan.hpp"
#include "non_wspr_request_builder.hpp"
#include <cstdlib>

#include <chrono>
#include <iostream>
#include <limits>
#include <string>

// WTP never queries the local RF hardware profile. Fail if that boundary changes.
int get_raspberry_pi_generation() { std::abort(); }

int main(int argc, char** argv) {
    if (argc != 2)
        return 2;
    using namespace wsprrypi;
    using namespace std::chrono_literals;
    const std::string mode = argv[1];
    ArgParserConfig cfg{};
    cfg.transmit_backend = TransmitBackendKind::WTP;
    cfg.cw_intra_element_gap = cfg.dfcw_intra_element_gap = 1;
    cfg.cw_inter_character_gap = cfg.dfcw_inter_character_gap = 3;
    cfg.cw_inter_word_gap = cfg.dfcw_inter_word_gap = 7;
    cfg.cw_fade_shape = "none";
    cfg.cw_fade_in_ms = cfg.cw_fade_out_ms = 0;
    cfg.allow_unqualified_frequency = cfg.allow_non_amateur_frequency = true;
    cfg.qrss.message = cfg.fskcw.message = cfg.dfcw.message = std::string(32, '?');
    cfg.qrss.dot_seconds = cfg.fskcw.dot_seconds = 0.25;
    cfg.dfcw.dot_seconds = 0.35;
    cfg.qrss.frequency_hz = cfg.fskcw.mark_frequency_hz = cfg.dfcw.dot_frequency_hz = 135500;
    cfg.fskcw.space_frequency_hz = 135495;
    cfg.dfcw.dash_frequency_hz = 135505;
    wsprrypi::TransmissionRequest request;
    if (mode == "qrss")
        request = scheduling_detail::make_qrss_controller_request(cfg, 0);
    else if (mode == "fskcw")
        request = scheduling_detail::make_fskcw_controller_request(cfg, 0);
    else if (mode == "dfcw")
        request = scheduling_detail::make_dfcw_controller_request(cfg, 0);
    else
        return 2;
    const auto plan = ExecutionPlanCompiler{}.compile(request);
    wtp::Capabilities caps;
    caps.profiles = {"rf-events/1"};
    caps.modes = {wtp::Mode::Qrss, wtp::Mode::Fskcw, wtp::Mode::Dfcw};
    caps.frequency_ranges = {{135490000000000ULL, 135510000000000ULL}};
    caps.max_events = 512;
    caps.max_payload_bytes = 65536;
    caps.max_job_duration_ns = 3600000000000ULL;
    caps.maximum_arm_uncertainty_ns = 500000000;
    auto converted =
        prepare_wtp_plan(plan, caps, {std::string(32, 'a'), 1800000000000000000ULL, 500000000});
    if (!converted) {
        std::cerr << converted.explanation;
        return 1;
    }
    converted.prepared->job.allow_frequency_adjustment = true;
    const auto encoded = wtp::encode_request({std::string(32, 'b'), std::string(32, 'c'),
                                              wtp::Operation::Load, converted.prepared->job});
    if (!encoded) {
        std::cerr << encoded.error;
        return 1;
    }
    std::cout << *encoded.payload << '\n';
}
