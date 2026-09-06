#include "time/usb_time_source.hpp"

#include <charconv>
#include <vector>

namespace wsprrypico::time {
namespace {
bool number(std::string_view text, std::uint64_t& value) {
    const auto [end, error] = std::from_chars(text.data(), text.data() + text.size(), value);
    return error == std::errc{} && end == text.data() + text.size();
}
std::vector<std::string_view> words(std::string_view line) {
    std::vector<std::string_view> result;
    while (!line.empty()) {
        const auto begin = line.find_first_not_of(' ');
        if (begin == std::string_view::npos)
            break;
        line.remove_prefix(begin);
        const auto end = line.find(' ');
        result.push_back(line.substr(0, end));
        if (end == std::string_view::npos)
            break;
        line.remove_prefix(end);
    }
    return result;
}
} // namespace

std::string UsbTimeSource::command(std::string_view line) {
    const auto fields = words(line);
    if (fields.size() == 1 && fields[0] == "SAMPLE") {
        const auto sample = clock_.snapshot().monotonic_now_ns;
        sample_ = sample;
        return "{\"ok\":true,\"sample_monotonic_ns\":" + std::to_string(sample) + "}\n";
    }
    if (fields.size() >= 5 && fields[0] == "SET") {
        std::uint64_t sample{}, utc{}, uncertainty{}, transition{};
        if (!number(fields[1], sample) || !number(fields[2], utc) ||
            !number(fields[3], uncertainty) || !sample_ || sample != *sample_)
            return "{\"ok\":false,\"error\":\"invalid_observation\"}\n";
        wtp::LeapState leap = wtp::LeapState::Unknown;
        std::optional<std::uint64_t> leap_transition;
        if (fields[4] == "NORMAL" && fields.size() == 5)
            leap = wtp::LeapState::Normal;
        else if ((fields[4] == "INSERT" || fields[4] == "DELETE") && fields.size() == 6 &&
                 number(fields[5], transition)) {
            leap = fields[4] == "INSERT" ? wtp::LeapState::InsertPending
                                         : wtp::LeapState::DeletePending;
            leap_transition = transition;
        }
        sample_.reset();
        if (leap == wtp::LeapState::Unknown ||
            !clock_.observe(utc, sample, uncertainty, leap, leap_transition))
            return "{\"ok\":false,\"error\":\"observation_rejected\"}\n";
        const auto status = clock_.snapshot();
        return "{\"ok\":true,\"uncertainty_ns\":" + std::to_string(status.uncertainty_ns) + "}\n";
    }
    if (fields.size() == 1 && fields[0] == "INVALIDATE") {
        reset();
        return "{\"ok\":true,\"clock\":\"unsynchronized\"}\n";
    }
    return "{\"ok\":false,\"error\":\"unknown_command\"}\n";
}

void UsbTimeSource::reset() {
    sample_.reset();
    clock_.invalidate();
}

} // namespace wsprrypico::time
