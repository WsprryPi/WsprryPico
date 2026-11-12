# Feature to-do list

Status: ▧ not started, ⏳ in progress, ✅ complete.

1. ✅ **Gray-line scheduling.** Pico standalone WSPR and keyed-message recurrence support independent morning/evening periods, solar-elevation windows, and frequency overrides. Both periods default disabled, with −6° to +6° bounds. Existing engine and frequency permissions apply. See the [operator controls](docs/configure.md#gray-line-scheduling), [engineering contract](engineering/development/standalone.md#gray-line-selection), and [retained research](engineering/development/gray-line-scheduling-plan.md).
2. ▧ **I²C LPF control.** Add I²C low-pass filter selection following the
   WsprryPi approach, supporting simple filter assignments or an explicit
   8-bit binary output word.
   See the [8574-based LPF output implementation plan](engineering/development/8574-lpf-output-plan.md)
   for the proposed hardware scope, control model, sequencing, and validation.
   Planning only; implementation has not started.
