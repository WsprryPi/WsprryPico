"""Prospective single-flight INFO scheduling; no hardware or legacy rescoring."""
from phase11_5_inventory import require

STRICT='request-cadence-and-roundtrip-v1'
SINGLE_FLIGHT='single-flight-info-v1'


def next_offer(start, published, period=1.0):
    require(published>=start and period>0,'Invalid observer interval')
    return max(start+period,published)


def validate_intervals(starts,published,begin,end,period=1_000_000_000):
    """Keep one-Hz offers, one-second offer tolerance and five-second replies.

    Only measured in-flight time delays the next eligible offer. Publication is
    included in the reply bound; idle host gaps, missing end coverage and overlap
    remain failures. Raw start gaps remain reported, never rewritten.
    """
    require(len(starts)==len(published)>0,'Missing observer intervals')
    require(0<=starts[0]-begin<=period+1_000_000_000,'Initial observer offer')
    for n,(s,p) in enumerate(zip(starts,published)):
        require(0<=p-s<=5_000_000_000,'Observer five-second reply/publication bound')
        if n:
            eligible=max(starts[n-1]+period,published[n-1])
            require(0<=s-eligible<=1_000_000_000,'Observer single-flight offer or overlap')
    require(published[-1]<=end<=max(starts[-1]+period,published[-1])+1_000_000_000,
        'Observer end coverage')
    return dict(samples=len(starts),max_start_gap_ns=max((b-a for a,b in zip(starts,starts[1:])),default=0),
        max_roundtrip_ns=max(p-s for s,p in zip(starts,published)),policy=SINGLE_FLIGHT)
