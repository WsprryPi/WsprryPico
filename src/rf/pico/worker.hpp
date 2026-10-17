#pragma once
#include "hardware/pins.hpp"
#include "rf/amplifier_enable.hpp"
#include "rf/indicator_gate.hpp"
#include "rf/worker.hpp"
namespace wsprrypico::rf {
// Launch once on core 0, before any engine/JobService call. Never hot-reset core 1.
WorkerEngine& start_worker(time::UtcDiscipline& clock, const hardware::PinPlan& pins,
                           bool storage_healthy, IndicatorGate& indicator, unsigned drive_ma = 4,
                           AmplifierEnable* amplifier = nullptr);
int gpio_drive_observation();
} // namespace wsprrypico::rf
