# USB UTC uncertainty

A USB Management controller can supply a qualified UTC observation. Native jobs run from the Pico's admitted clock and report UTC uncertainty for operator judgment. Source age, symbol timing, lead time, missed-start handling, and cleanup retain their independent limits.

## Interval accounting

WsprryPi observes host UTC immediately before the sample request and after the validated sample response, before sending ACK. The ACK remains mandatory; an unconfirmed ACK never permits a submit. A separate observation after ACK retains host qualification, regression, and clock-step checks across that wait. It does not recenter the old sample or charge ACK latency as transfer error.

If capture lies in `[t0, t1]`, the midpoint estimate has worst-case transfer error `ceil((t1 - t0) / 2)`. This interval argument allows either direction to consume all measured delay; it does not assume symmetric USB delivery. The submitted uncertainty is:

```text
max(qualified host error before sample, after response, after ACK)
+ ceil(sample monotonic interval / 2)
+ absolute wall/monotonic discrepancy across sample and ACK
+ unchanged 100000 ns processing/drift margin
```

Clock-step, total exchange-age, overflow, leap, qualification, identity, deadline, and one-use sample checks remain. Pico still ages error from its actual monotonic capture at the existing 50 ppm rate, including ACK/submission time and time before job admission. RF workspace, foreground service budgets, source-age expiry and local execution remain independent of the informational UTC uncertainty policy.

Runtime observations expose host uncertainty, sample round trip, midpoint radius, total and post-ACK clock discrepancy, processing margin, and ACK duration. This separates the causes without claiming stronger clock quality.

## Precision limits and validation

The cooperative USB Management exchange has no 1 ms physical UTC qualification. Sample admission includes controller clock error, measured transfer time, and local aging. An internally valid first observation cannot prove its own absolute accuracy. RF accuracy requires an independent measurement.

Existing interval tests cover one-sided delay, odd rounding, delayed/missing ACK, pre/post-ACK clock steps, regression, unqualified observations, overflow, cancellation, and strict framing/binding. They verify accounting and failure behavior; they do not measure physical UTC offset, launch timing, or RF error.
