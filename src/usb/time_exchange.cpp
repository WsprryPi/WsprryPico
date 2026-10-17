#include "usb/time_exchange.hpp"

#include "wtp/json.hpp"

namespace wsprrypico::usb {
network::HttpResponse TimeExchange::handle(const network::HttpRequest& request,
                                           std::uint64_t transaction) {
    using namespace wtp::json;
    if (request.method == "GET" && request.path == "/api/usb/v1/time/sample") {
        sampled_ns_ = now_(context_);
        sample_ = std::to_string(transaction);
        return {200,
                "{\"sample\":" + quote(sample_) +
                    ",\"monotonic_ns\":" + quote(std::to_string(sampled_ns_)) + "}",
                "application/json",
                {}};
    }
    if (request.method != "POST" || request.path != "/api/usb/v1/time/submit")
        return network::http_error(404, "unsupported_usb_time_operation");
    const auto root = parse(request.body_view());
    if (!root || !fields(*root, {"sample", "utc_ns", "uncertainty_ns", "leap"})) {
        reset();
        return network::http_error(400, "invalid_time_observation");
    }
    const auto token = root->get("sample"), leap = root->get("leap");
    const auto now = now_(context_);
    const auto sampled = sampled_ns_;
    const bool matching = !sample_.empty() && token->type() == '"' && token->string() == sample_;
    reset(); // Every submission consumes the sample, including a refused one.
    std::uint64_t utc{}, uncertainty{};
    if (!matching || !decimal(*root->get("utc_ns"), utc, true) ||
        !decimal(*root->get("uncertainty_ns"), uncertainty) || leap->type() != '"' ||
        leap->string() != "normal" || uncertainty > time::standalone_max_uncertainty_ns ||
        utc < time::sntp_min_utc_ns || utc >= time::sntp_max_utc_ns || now < sampled ||
        now - sampled > 2'000'000'000ULL)
        return network::http_error(409, "stale_or_invalid_time_observation");
    const auto accepted = arbiter_.observe(time::ObservationSource::Controller, utc, sampled,
                                           uncertainty, wtp::LeapState::Normal, {}, "usb-physical");
    const auto status = arbiter_.status();
    const bool sntp_selected = status.source == time::ActiveTimeSource::Sntp;
    const auto source = sntp_selected                                           ? "sntp"
                        : status.source == time::ActiveTimeSource::Controller   ? "controller"
                        : status.source == time::ActiveTimeSource::Disagreement ? "disagreement"
                                                                                : "none";
    if (!accepted && !sntp_selected)
        return network::http_error(409, "time_source_refused");
    // Healthy SNTP retains priority. This is an available but unselected USB
    // observation, not an instruction to overwrite or invalidate SNTP.
    return {200,
            "{\"accepted\":" + std::string(accepted ? "true" : "false") +
                ",\"selected\":" + (accepted ? "true" : "false") + ",\"source\":" + quote(source) +
                ",\"uncertainty_ns\":" + quote(std::to_string(status.uncertainty_ns)) +
                ",\"age_ns\":" + quote(std::to_string(status.age_ns)) + "}",
            "application/json",
            {}};
}
} // namespace wsprrypico::usb
