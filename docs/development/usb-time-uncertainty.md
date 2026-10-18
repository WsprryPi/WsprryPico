# USB UTC uncertainty

WsprryPi defaults new/missing WTP settings to 100000000 ns (100 ms). Explicit
saved values, including 1 ms, remain unchanged. The default is an engineering
admission policy, not a measured accuracy claim or a WTP/1 requirement.
Uncertainty is checked at ARM and again before local launch; symbol timing,
lead time, missed-start, cleanup and holdover rules remain independent.

## Interval accounting

WsprryPi now observes host UTC immediately before the sample request and after
the validated sample response, before sending ACK. The ACK remains mandatory;
an unconfirmed ACK never permits a submit. A separate observation after ACK
retains host qualification, regression and clock-step checks across that wait.
It does not recenter the old sample or charge ACK latency as transfer error.

If capture lies in `[t0, t1]`, the midpoint estimate has worst-case transfer
error `ceil((t1 - t0) / 2)`. This interval argument allows either direction to
consume all measured delay; it does not assume symmetric USB delivery. The
submitted uncertainty is:

```text
max(qualified host error before sample, after response, after ACK)
+ ceil(sample monotonic interval / 2)
+ absolute wall/monotonic discrepancy across sample and ACK
+ unchanged 100000 ns processing/drift margin
```

Clock-step, total exchange-age, overflow, leap, qualification, identity,
deadline and one-use sample checks remain. Pico still ages error from its
actual monotonic capture at the existing 50 ppm rate, including ACK/submission
time and time before job admission. No RF workspace, foreground service
budget, holdover, launch or uncertainty limit is weakened.

Runtime observations expose host uncertainty, sample round trip, midpoint
radius, total and post-ACK clock discrepancy, processing margin and ACK
duration. This separates the causes without claiming stronger clock quality.

## Precision limits and validation

The cooperative JSON USB exchange is not qualified for 1 ms physical UTC
transfer. A stricter request retains its limit and refuses when the complete
host/transfer/aging bound exceeds it. Do not assume symmetric delay, omit host
clock error, clamp uncertainty or treat a connected reference as calibrated
RF/UTC evidence. A first internally valid host sample cannot prove its own
absolute correctness.

Existing interval tests cover one-sided delay, odd rounding, delayed/missing
ACK, pre/post-ACK clock steps, regression, unqualified observations, overflow,
cancellation and strict framing/binding. They verify accounting and failure
behavior; they do not measure physical UTC offset, launch timing or RF error.
