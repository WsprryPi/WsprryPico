#pragma once
#include "rf/worker.hpp"
namespace wsprrypico::rf {
// Launch once on core 0, before any engine/JobService call. Never hot-reset core 1.
WorkerEngine& start_worker(time::UtcDiscipline& clock);
} // namespace wsprrypico::rf
