#!/usr/bin/env python3
"""Offline timing bounds for a new released gesture around a flash callback.

The caller must establish one new gesture from healthy, same-boot real-input
INFO records, released before and after the callback. This does not establish
that a pad edge occurred during the shorter erase/program pulse.
"""


def bound_overlap(samples_before, before_us, begin_us, end_us, after_us, duration_us):
    values = (samples_before, before_us, begin_us, end_us, after_us, duration_us)
    if any(type(value) is not int or value < 0 for value in values):
        raise ValueError('Nonnegative integer observations required')
    if samples_before == 0 or duration_us == 0:
        raise ValueError('Sample and gesture evidence required')
    # Samples have a nonnegative boot-time origin. The last consumed sample is
    # index count-1 at 1 kHz. Released stable input allows up to 10 ms of a new
    # raw low before debounce reports held. Using origin zero only widens the
    # possible pre-callback interval; it cannot manufacture overlap evidence.
    last_sample_lower = (samples_before - 1) * 1000
    earliest_start = max(0, last_sample_lower - 10_000)
    if not last_sample_lower <= before_us <= begin_us < end_us <= after_us:
        raise ValueError('Inconsistent sample/callback/INFO ordering')
    if duration_us > after_us - earliest_start:
        raise ValueError('Gesture cannot fit inside the observation interval')
    before_gap = begin_us - earliest_start
    after_gap = after_us - end_us
    callback_duration = end_us - begin_us
    # A gesture longer than either outside gap cannot fit wholly outside. If
    # shorter than the callback, it also cannot surround the entire callback.
    # Thus at least one edge is strictly inside. Equality is not sufficient.
    edge_proven = max(before_gap, after_gap) < duration_us < callback_duration
    return {
        'earliest_start_us': earliest_start,
        'pre_callback_gap_upper_us': before_gap,
        'post_callback_gap_upper_us': after_gap,
        'callback_duration_us': callback_duration,
        'gesture_duration_us': duration_us,
        'minimum_gesture_overlap_us': max(0, duration_us - before_gap - after_gap),
        'at_least_one_edge_inside_callback': edge_proven,
    }
