// SPDX-License-Identifier: MIT
#pragma once
#include "hardware/gps_settings.hpp"
#include "time/gps_calibration.hpp"

#include <atomic>

namespace wsprrypico::time {
// One core-0 owner; IRQs only enqueue bytes and pulse timestamps. Reading status
// never consumes an observation or extends a fix, pulse, or calibration age.
class PicoGpsInput {
  public:
    bool open(const hardware::PinPlan&, const std::optional<hardware::Si5351Settings>&,
              const hardware::GpsSettings&, const hardware::FilterSettings& = {});
    void close();
    using Observer = void (*)(const gps::Observation&, void*);
    void poll(std::uint64_t raw_ns, Observer, void*);
    std::string status(std::uint64_t raw_ns) const;
    std::optional<gps::Position> position(std::uint64_t raw_ns) const;
    const std::optional<gps::Observation>& last_observation() const {
        return observation_;
    }
    using CycleCapture = gps::CycleSnapshot (*)();
    void cycle_capture(CycleCapture capture) {
        cycle_capture_ = capture;
    }
    const std::optional<gps::CycleSnapshot>& cycle() const {
        return cycle_;
    }
    void uart_interrupt();
    void pps_interrupt();
    void capture_gap(bool entering);
    bool capture_clock_bound() const {
        return open_ && clock_bound();
    }

  private:
    template <class T, unsigned N> struct Queue {
        std::array<T, N> data{};
        std::atomic<unsigned> head{0}, tail{0};
        std::atomic<std::uint32_t> dropped{0};
        bool push(T value) {
            const auto h = head.load(std::memory_order_relaxed);
            if (h - tail.load(std::memory_order_acquire) == N) {
                dropped.fetch_add(1, std::memory_order_relaxed);
                return false;
            }
            data[h % N] = value;
            head.store(h + 1, std::memory_order_release);
            return true;
        }
        const T* peek() const {
            const auto t = tail.load(std::memory_order_relaxed);
            return t == head.load(std::memory_order_acquire) ? nullptr : &data[t % N];
        }
        void pop() {
            tail.fetch_add(1, std::memory_order_release);
        }
        unsigned discard() {
            const auto h = head.load(std::memory_order_acquire);
            const auto count = h - tail.load(std::memory_order_relaxed);
            tail.store(h, std::memory_order_release);
            return count;
        }
    };
    struct Byte {
        std::uint32_t raw_us;
        std::uint16_t data;
    };
    Queue<Byte, 256> bytes_;
    struct CapturedPulse {
        gps::Pulse pulse;
        gps::CycleSnapshot cycle;
    };
    Queue<CapturedPulse, 8> pulses_;
    std::optional<CapturedPulse> latest_capture_, preceding_capture_;
    CycleCapture cycle_capture_ = nullptr;
    std::optional<gps::CycleSnapshot> cycle_;
    hardware::GpsSettings settings_;
    gps::Parser parser_;
    gps::Pairer pairer_{{}};
    std::optional<gps::Position> position_;
    std::optional<gps::Observation> observation_;
    unsigned uart_index_ = 0;
    bool open_ = false, failed_ = false;
    std::atomic<bool> capture_blocked_{false};
    unsigned capture_gap_depth_ = 0; // Core 0 only, never modified by an IRQ.
    bool clock_gap_ = false;
    unsigned pps_slice_ = 0;
    std::uint32_t system_hz_ = 0, reference_hz_ = 0;
    bool pps_counter_armed_ = false;
    std::atomic<std::uint32_t> irq_latency_ns_{0}, maximum_irq_latency_ns_{0},
        capture_error_bound_ns_{0}, capture_rejections_{0}, capture_error_{0};
    void reset_pps_counter();
    bool clock_bound() const;
    std::uint64_t pulse_sequence_ = 0, last_serial_ns_ = 0, last_pps_ns_ = 0;
    std::uint32_t observed_drops_ = 0, uart_errors_ = 0, observations_ = 0;
    unsigned satellites_ = 0;
    std::uint64_t candidate_utc_ns_ = 0, candidate_raw_ns_ = 0, candidate_pps_ns_ = 0;
};
} // namespace wsprrypico::time
