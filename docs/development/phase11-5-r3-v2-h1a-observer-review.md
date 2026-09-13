# H1a observer publication failure and prospective correction

H1a retains its frozen packet, runner and raw evidence. Its WTP worker failed
at sequence 80244, host monotonic 270355611017663 ns, 1,945.418011881 seconds
after the first journal record. The reported guard was `Fresh INFO required`.
The independent Console, host health and native TLS/HTTP readers continued
under the original finite deadline. No new RF launch or mutation is added to
this consumed packet. No completed-hour credit is assigned before raw audit.

The failure is consistent with a reproduced observer race. `emit` holds the
journal lock, timestamps and writes the INFO record, flushes and fsyncs it, then
publishes `samples['info']`. The WTP action previously read that tuple without
the lock and sampled its age separately. It could select an old tuple while the
new INFO publication was in progress, then reject the old tuple after the new
record appeared. Sequence 80242 records INFO at 270355603894292 ns, only
7,123,371 ns before the failure, while the prior published record was
2,232,579,720 ns before it. The intervening INFO request took about 1.386 seconds,
within the unchanged five-second response allowance. The trace does not record
the tuple selected by the failing guard, so it cannot prove its precise thread
interleaving. It does identify a source race that the deterministic regression
reproduces; there is no recorded target allocator, stack or RF fault at that
point.

The prospective runner reads publication and age while holding the same lock.
It keeps the two-second freshness limit and reports the actual age if the guard
fails. A separate action guard stops future mutations after a failure while
keeping the WTP read loop alive; previously the action exception also terminated
that reader. Neither change alters DUT firmware, submitted events, RF budget,
observation cadence or response limits. Four hardware-free regressions cover
blocked publication, exact freshness boundaries, continued reading with no
further mutation, and normal successful actions.

H2a was staged but has not executed. Retire it with zero RF debit and prepare a
fresh H2b packet with the corrected runner before the next DFCW hour. Do not
replace staged or consumed bytes. A distinct component audit may credit H1a's
actual complete finite mode duration if its surviving raw Console and
certificate-bound native WTP observations, DMA/refill/tail counts, exact job
identity and authoritative final state prove it. Such credit must retain the
failed full-run USB observation gate and actual source/image/boot identity.
