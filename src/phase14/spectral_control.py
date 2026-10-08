"""Keep the owned spectral job alive through its natural terminal result."""
import time


def wait_complete(peer, owner, boot_id, job_id, deadline, statuses,
                  now=time.monotonic, sleep=time.sleep):
    while now() < deadline:
        # STATUS is read-only. A lease expiring during RF is released at the
        # terminal state, so an unrenewed long tail cannot then RELEASE.
        peer.request('RENEW', dict(owner_id=owner, lease_ms=60000))
        status = peer.request('STATUS', {})
        statuses.append(status)
        if status['boot_id'] != boot_id or status['job_id'] != job_id:
            raise ValueError('spectral terminal identity changed')
        if status['state'] == 'complete' and status['output_active'] is False:
            return status
        if status['state'] != 'running' or status['output_active'] is not True:
            raise ValueError('spectral unexpected terminal')
        sleep(.5)
    raise TimeoutError('spectral natural completion deadline')
