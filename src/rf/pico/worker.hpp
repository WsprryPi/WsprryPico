#pragma once
#include "hardware/pins.hpp"
#include "hardware/si5351_settings.hpp"
#include "rf/amplifier_enable.hpp"
#include "rf/indicator_gate.hpp"
#include "rf/worker.hpp"
#include "time/gps_calibration.hpp"
namespace wsprrypico::rf {
class FilterSelector;
// Launch once on core 0, before any engine/JobService call. Never hot-reset core 1.
WorkerEngine& start_worker(time::UtcDiscipline& clock, const hardware::PinPlan& pins,
                           bool storage_healthy, IndicatorGate& indicator, unsigned drive_ma = 4,
                           AmplifierEnable* amplifier = nullptr, FilterSelector* filters = nullptr,
                           const std::optional<hardware::Si5351Settings>& si5351 = {},
                           bool gps_pps_calibration = false);
int gpio_drive_observation();
time::gps::CycleSnapshot reference_count_at_pps();
} // namespace wsprrypico::rf
