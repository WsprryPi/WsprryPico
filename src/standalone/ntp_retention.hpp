#pragma once

#include "microchrony.hpp"
#include "standalone/storage.hpp"
#include "time/mapping.hpp"
#include "time/ntp_filter.hpp"

#include <algorithm>
#include <cstdlib>

namespace wsprrypico::standalone {
// Independent, non-runnable learning cache. No Config, UTC epoch, freshness or
// RF authority is restored by loading it. Manual PPM is never written here.
class NtpRetention {
  public:
    struct Provenance {
        std::string boot;
        std::uint32_t endpoint = 0;
        std::uint64_t epoch = 0, generation = 0, reference_utc_ns = 0;
        bool operator==(const Provenance&) const = default;
    };
    // Legacy journal payload only; no production NTP-to-RF consumer or new RF learning.
    struct RfPrior {
        std::int32_t utc_rate_ppb = 0;
        std::uint32_t uncertainty_ppb = 0, samples = 0;
        std::uint64_t span_ns = 0;
        Provenance source;
        bool operator==(const RfPrior&) const = default;
    };
    struct Record {
        std::int32_t utc_rate_ppb = 0;
        Provenance utc_source;
        std::optional<RfPrior> rf;
        std::uint32_t utc_skew_ppb = 2'000'000;
    };
    NtpRetention(Flash& flash, std::string device, std::uint64_t topology)
        : flash_(flash), journal_(flash, 0, 256), device_(std::move(device)), topology_(topology) {}
    bool load() {
        record_.reset();
        pending_.reset();
        healthy_ = false;
        // A torn cache write can discard that update, never configuration or
        // consumed-slot authority. Unknown/foreign data is never auto-erased.
        if (!hex(device_) || !topology_ || !journal_.load(true))
            return false;
        if (!journal_.data().empty()) {
            const auto& data = journal_.data();
            if (data.size() != 192)
                return false;
            std::size_t cursor = 0;
            auto get = [&](unsigned width) {
                std::uint64_t value = 0;
                for (unsigned i = 0; i < width; ++i)
                    value |= std::uint64_t(std::uint8_t(data[cursor++])) << (8 * i);
                return value;
            };
            if (get(4) != 0x50544e57)
                return false;
            const auto version = get(2);
            if ((version != 1 && version != 2) || data.substr(cursor, 32) != device_)
                return false;
            cursor += 32;
            if (get(8) != topology_ || (version == 1 && get(1) != 1))
                return false;
            Record next;
            next.utc_rate_ppb = signed_rate(get(4));
            if (version == 2)
                next.utc_skew_ppb = std::uint32_t(get(4));
            auto provenance = [&]() {
                Provenance value;
                value.boot = data.substr(cursor, 32);
                cursor += 32;
                value.endpoint = std::uint32_t(get(4));
                value.epoch = get(8);
                value.generation = get(8);
                value.reference_utc_ns = get(8);
                return value;
            };
            next.utc_source = provenance();
            const auto has_rf = get(1);
            RfPrior rf;
            rf.utc_rate_ppb = signed_rate(get(4));
            rf.uncertainty_ppb = std::uint32_t(get(4));
            rf.samples = std::uint32_t(get(version == 1 ? 4 : 1));
            rf.span_ns = get(8);
            rf.source = provenance();
            if (has_rf > 1 || !valid(next.utc_source) ||
                std::abs(std::int64_t(next.utc_rate_ppb)) > 100'000 ||
                next.utc_skew_ppb > time::utc_max_rate_uncertainty_ppb || (has_rf && !valid(rf)))
                return false;
            if (has_rf)
                next.rf = rf;
            record_ = next;
        }
        healthy_ = true;
        return true;
    }
    // At most one automatic write per five minutes, and only for a meaningful
    // 0.1 ppm change or the first strict RF prior. First learned UTC save is immediate.
    bool stage(std::optional<std::int32_t> utc_rate, const Provenance& source,
               std::optional<RfPrior> rf, std::uint32_t utc_skew_ppb = 2'000'000) {
        if (!healthy_ || (!utc_rate && !rf) ||
            (utc_rate && (std::abs(std::int64_t(*utc_rate)) > 100'000 || !valid(source) ||
                          utc_skew_ppb > time::utc_max_rate_uncertainty_ppb)) ||
            (rf && !valid(*rf)))
            return false;
        // Capture the two learners independently, even while a job owns the
        // device or a flash-write cooldown is active. Pending values are historical.
        auto next = pending_ ? *pending_ : record_.value_or(Record{});
        if (utc_rate) {
            next.utc_rate_ppb = *utc_rate;
            next.utc_skew_ppb = utc_skew_ppb;
            next.utc_source = source;
        } else if (!pending_ && !record_) {
            // A strict recent raw slope can also seed broadly bounded UTC;
            // this does not restore its qualification or absolute UTC.
            next.utc_rate_ppb = rf->utc_rate_ppb;
            next.utc_source = rf->source;
            next.utc_skew_ppb = rf->uncertainty_ppb;
        }
        if (rf)
            next.rf = rf;
        pending_ = std::move(next);
        return true;
    }
    bool save(std::int32_t utc_rate, const Provenance& source, std::optional<RfPrior> rf,
              std::uint64_t now_ns, std::uint32_t utc_skew_ppb = 2'000'000) {
        return stage(utc_rate, source, rf, utc_skew_ppb) && flush(now_ns);
    }
    // Only the production idle/unowned/normal-operation boundary calls flush.
    bool flush(std::uint64_t now_ns) {
        if (!healthy_ || !pending_)
            return false;
        const auto utc_rate = pending_->utc_rate_ppb;
        const auto& source = pending_->utc_source;
        const auto& rf = pending_->rf;
        const bool changed =
            !record_ || std::abs(std::int64_t(utc_rate) - record_->utc_rate_ppb) >= 100 ||
            (pending_->utc_skew_ppb < record_->utc_skew_ppb / 2) ||
            (rf && (!record_->rf ||
                    std::abs(std::int64_t(rf->utc_rate_ppb) - record_->rf->utc_rate_ppb) >= 100));
        if (!changed) {
            pending_.reset();
            return false;
        }
        if (saved_at_ && (now_ns < *saved_at_ || now_ns - *saved_at_ < 300'000'000'000ULL))
            return false;
        std::string data;
        auto put = [&](std::uint64_t value, unsigned width) {
            for (unsigned i = 0; i < width; ++i) {
                data.push_back(char(value & 255));
                value >>= 8;
            }
        };
        auto provenance = [&](const Provenance& p) {
            data += p.boot;
            put(p.endpoint, 4);
            put(p.epoch, 8);
            put(p.generation, 8);
            put(p.reference_utc_ns, 8);
        };
        put(0x50544e57, 4);
        put(2, 2); // Statistical frequency + skew; v1 remains readable.
        data += device_;
        put(topology_, 8);
        put(std::uint32_t(utc_rate), 4);
        put(pending_->utc_skew_ppb, 4);
        provenance(source);
        put(rf.has_value(), 1);
        const auto prior = rf.value_or(RfPrior{0, 0, 0, 0, {std::string(32, '0'), 0, 0, 0, 0}});
        put(std::uint32_t(prior.utc_rate_ppb), 4);
        put(prior.uncertainty_ppb, 4);
        put(prior.samples, 1);
        put(prior.span_ns, 8);
        provenance(prior.source);
        if (data.size() != 192 || !journal_.append(data)) {
            healthy_ = false;
            return false;
        }
        record_ = pending_;
        pending_.reset();
        saved_at_ = now_ns;
        return true;
    }
    bool erase() {
        record_.reset();
        pending_.reset();
        if (erase_observer_)
            erase_observer_(erase_context_);
        saved_at_.reset();
        healthy_ = false;
        return flash_.erase(0) && flash_.erase(4096) && erased() && load();
    }
    bool erased() const {
        std::array<std::uint8_t, 256> page;
        for (unsigned offset = 0; offset < 8192; offset += page.size())
            if (!flash_.read(offset, page) ||
                !std::all_of(page.begin(), page.end(), [](auto b) { return b == 255; }))
                return false;
        return true;
    }
    void on_erase(void (*observer)(void*), void* context) {
        erase_observer_ = observer;
        erase_context_ = context;
    }
    bool healthy() const {
        return healthy_;
    }
    const std::optional<Record>& record() const {
        return record_;
    }
    std::uint64_t sequence() const {
        return journal_.sequence();
    }
    static bool valid(const Provenance& p) {
        return hex(p.boot) && p.endpoint && p.epoch && p.generation &&
               p.reference_utc_ns >= 1'735'689'600'000'000'000ULL &&
               p.reference_utc_ns < 4'102'444'800'000'000'000ULL;
    }
    static bool valid(const RfPrior& r) {
        time::RateEstimate candidate;
        candidate.qualified = true;
        candidate.utc_rate_ppb = r.utc_rate_ppb;
        return bool(time::oscillator_correction(candidate)) &&
               std::abs(std::int64_t(r.utc_rate_ppb)) <= 100'000 && r.uncertainty_ppb <= 5000 &&
               r.samples >= 3 && r.samples <= microchrony::sample_capacity && r.span_ns > 0 &&
               r.span_ns <= 604'800'000'000'000ULL && valid(r.source);
    }

  private:
    static std::int32_t signed_rate(std::uint64_t value) {
        return value <= INT32_MAX ? std::int32_t(value)
                                  : std::int32_t(std::int64_t(value) - 0x100000000LL);
    }
    static bool hex(std::string_view s) {
        return s.size() == 32 && std::all_of(s.begin(), s.end(), [](char c) {
                   return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
               });
    }
    Flash& flash_;
    Journal journal_;
    std::string device_;
    std::uint64_t topology_;
    std::optional<Record> record_, pending_;
    std::optional<std::uint64_t> saved_at_;
    bool healthy_ = false;
    void (*erase_observer_)(void*) = nullptr;
    void* erase_context_ = nullptr;
};
} // namespace wsprrypico::standalone
