// SPDX-License-Identifier: MIT
#pragma once
#include "application/test_tone_review.hpp"
#include "standalone/scheduler.hpp"

namespace wsprrypico::application {
// Trusted adapter identity, never populated from a request document/header.
struct TestToneAuthority {
    enum class Scope { None, Engineering, Field, Consumer, Usb };
    Scope scope = Scope::None;
    std::string principal;
    std::uint64_t profile_generation = 0, credential_epoch = 0;
    bool operator==(const TestToneAuthority&) const = default;
    bool valid() const {
        return scope != Scope::None && !principal.empty() && principal.size() <= 128;
    }
};
struct TestToneRecord {
    TestToneAuthority authority;
    std::string request_id, job_id, admission_revision, control_revision;
    TestToneProposal proposal;
    TestToneReview assessment;
    execution::PadObservation pad;
    std::optional<unsigned> rf_pin;
    std::optional<rf::si5351::Configuration> synthesis_configuration;
    execution::SynthesisObservation synthesis;
    std::string execution_engine;
    bool matched_profile = false;
    execution::State state = execution::State::Loaded;
    execution::ErrorCode error = execution::ErrorCode::None;
    std::uint64_t accepted_ns = 0, ended_ns = 0, sequence = 0;
    std::optional<std::uint64_t> launch_ns;
    bool terminal = false, output_inactive_confirmed = false, recovery_required = false;
};
class TestTone {
  public:
    static constexpr std::size_t terminal_capacity = 8;
    static constexpr std::uint64_t retention_ns = 3'600'000'000'000ULL;
    TestTone(execution::JobService&, standalone::Store&, standalone::Scheduler&);
    ~TestTone();
    TestTone(const TestTone&) = delete;
    TestTone& operator=(const TestTone&) = delete;
    void policy(const standalone::FrequencyPolicyEngine& value) {
        policy_ = &value;
    }
    bool supported() const {
        return policy_ != nullptr;
    }
    std::uint64_t admission_sequence() const {
        return admission_sequence_;
    }
    TestToneReview review(const TestToneProposal&, bool mutation_pending) const;
    struct Result {
        TestToneRecord* record = nullptr;
        std::string_view error;
        execution::ErrorCode native_error = execution::ErrorCode::None;
    };
    Result start(const TestToneAuthority&, std::string_view request, const TestToneProposal&,
                 std::string_view match, std::string_view current_revision, bool pending);
    Result status(const TestToneAuthority&, std::string_view selector, bool by_job);
    Result stop(const TestToneAuthority&, std::string_view job, std::string_view match);
    // Application owner, including disconnected operation. Does not drive RF timing.
    void poll();

  private:
    TestToneContext context(bool mutation_pending) const;
    unsigned boot_drive() const;
    static void terminal(const execution::TerminalRecord&, void*);
    execution::Response command(std::string_view, execution::RequestBody = {});
    void settle(TestToneRecord&, execution::State, execution::ErrorCode, bool inactive, std::uint64_t);
    void prune();
    TestToneRecord* find(std::string_view, bool job);
    execution::JobService& service_;
    standalone::Store& store_;
    standalone::Scheduler& scheduler_;
    const standalone::FrequencyPolicyEngine* policy_ = nullptr;
    std::array<std::optional<TestToneRecord>, terminal_capacity + 1> records_;
    std::string boot_;
    std::uint64_t admission_sequence_ = 0, native_sequence_ = 0;
};
} // namespace wsprrypico::application
