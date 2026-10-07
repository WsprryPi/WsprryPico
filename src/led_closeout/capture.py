"""Finite managed captures; independent media never become a telemetry pass."""
import os
import math
from pathlib import Path
import signal
import subprocess
import time

from led_closeout.runner import require, save_json, sha256
from led_closeout.plan import make_plan


def storage_reserve(setup):
    """Reserve the whole retained matrix, not one case, before device changes."""
    seconds = sum(260 if case['action'] == 'standalone' else
                  math.ceil(int(case['job']['total_duration_ns']) / 1e9 + 90)
                  for case in make_plan()['cases'])
    cam = setup['camera']
    # Explicit 8-bit bgr0 recording has four bytes/pixel before FFV1 coding.
    # Add 10% plus 256 MiB for container/ledger/flash-readback overhead.
    per_second = 250000 * 8 + cam['width'] * cam['height'] * cam['fps'] * 4
    return math.ceil(seconds * per_second * 1.1) + 256 * 1024 * 1024


class Captures:
    def __init__(self, setup, evidence, *, now=time.monotonic, sleep=time.sleep):
        self.setup, self.e, self.now, self.sleep = setup, evidence, now, sleep
        self.processes, self.logs = [], []
        self.root, self.deadline = None, 0
        self.progress, self.changed = None, 0

    def start(self, root, seconds):
        require(not self.processes and 1 <= seconds <= 300, 'capture duration/ownership')
        self.root = Path(root)
        cfg = self.setup
        duration = int(seconds + .999)
        sdr = [cfg['capture_helper']['path'], '--enable-physical-sdr', 'sdrplay', cfg['receiver_serial'],
               '3550000', str(duration * 250000), '20', '250000', '200000', '0', 'false', 'false',
               '100000', str(duration + 8), str(self.root/'capture.cf32'),
               str(self.root/'capture.json'), self.root.name]
        cam = cfg['camera']
        video = [cfg['ffmpeg']['path'], '-nostdin', '-hide_banner', '-loglevel', 'info',
                 '-f', 'v4l2', '-framerate', str(cam['fps']), '-video_size',
                 str(cam['width']) + 'x' + str(cam['height']), '-i', cam['device'],
                 '-t', str(duration), '-an', '-pix_fmt', 'bgr0', '-c:v', 'ffv1', '-f', 'matroska',
                 '-progress', str(self.root/'video.progress'), '-n', str(self.root/'led.mkv')]
        save_json(self.root/'capture-binding.json', dict(setup=cfg, duration_s=duration,
            receiver=sdr, camera=video, optical_assessment='PENDING',
            edge_timing='UNQUALIFIED_WITHOUT_INDEPENDENT_SYNCHRONIZATION', optical_pixel_format='bgr0',
            host_monotonic_start_ns=time.monotonic_ns(), host_utc_start_ns=time.time_ns()))
        self.deadline = self.now() + duration + 12
        self.progress, self.changed = None, self.now()
        try:
            for name, argv in (('receiver', sdr), ('camera', video)):
                log = (self.root/(name + '.log')).open('xb')
                self.logs.append(log)
                self.processes.append(subprocess.Popen(argv, stdin=subprocess.DEVNULL,
                    stdout=log, stderr=subprocess.STDOUT, start_new_session=True))
            ready_until = self.now() + 8
            while True:
                self.healthy()
                iq = self.root/'capture.cf32.incomplete'
                progress = self.root/'video.progress'
                if iq.exists() and iq.stat().st_size >= 65536 and progress.exists():
                    frames = [int(line.split('=')[1]) for line in progress.read_text().splitlines()
                              if line.startswith('frame=')]
                    if frames and frames[-1] > 0:
                        break
                require(self.now() < ready_until, 'capture readiness timeout')
                self.sleep(.05)
            self.e.event('captures_ready', dict(case=self.root.name))
        except BaseException:
            self.stop()
            raise

    def healthy(self):
        require(len(self.processes) == 2 and all(p.poll() is None for p in self.processes),
                'capture exited before transmitter stopped')
        require(self.now() < self.deadline, 'capture deadline')
        iq = self.root/'capture.cf32.incomplete'
        video = self.root/'video.progress'
        frames = [line for line in video.read_text().splitlines() if line.startswith('frame=')] if video.exists() else []
        observed = (iq.stat().st_size if iq.exists() else 0, frames[-1] if frames else '')
        if self.progress is None or all(a != b for a,b in zip(observed,self.progress)):
            self.progress, self.changed = observed, self.now()
        require(self.now()-self.changed < 5, 'capture stream stopped progressing')

    def finish(self):
        require(len(self.processes) == 2, 'captures absent')
        # RF has already stopped and the owner has been released here.
        for p in self.processes:
            require(p.wait(timeout=max(.01, self.deadline - self.now())) == 0, 'capture failed')
        iq, meta, video = (self.root/n for n in ('capture.cf32', 'capture.json', 'led.mkv'))
        require(iq.is_file() and meta.is_file() and video.is_file() and video.stat().st_size > 4096,
                'capture artifacts missing')
        import json
        from phase11_5_inventory import loads_console
        from validate_wtp_contract import unique_object, reject_constant
        value = json.loads(meta.read_text(), object_pairs_hook=unique_object, parse_constant=reject_constant)
        binding = loads_console((self.root/'capture-binding.json').read_text())
        count = binding['duration_s'] * 250000
        progress = (self.root/'video.progress').read_text().splitlines()
        frame_counts = [int(v.split('=')[1]) for v in progress if v.startswith('frame=')]
        times = [int(v.split('=')[1]) for v in progress if v.startswith('out_time_us=')]
        require(frame_counts and times and frame_counts[-1] >= (binding['duration_s']-1)*self.setup['camera']['fps']*.85 and
                times[-1] >= (binding['duration_s']-1)*1000000, 'video duration/frame coverage')
        require(value['resolved_device'] == dict(driver='sdrplay', serial=self.setup['receiver_serial']) and
                value['actual_settings'] == dict(format='CF32', sample_rate_hz=250000,
                    bandwidth_hz=200000, center_frequency_hz=3550000, gain_db=20,
                    channel=0, agc=False, bias_tee=False), 'capture receiver/settings mismatch')
        require(value['primary_outcome'] == 'success' and value['cleanup']['outcome'] == 'verified' and
                value['retained_sample_count'] == count and value['output']['complete'] is True and
                value['output']['size_bytes'] == count*8 == iq.stat().st_size and
                value['output']['sha256'] == sha256(iq), 'capture sample/hash/cleanup mismatch')
        save_json(self.root/'artifacts.json', {p.name: dict(bytes=p.stat().st_size, sha256=sha256(p))
                                             for p in (iq, meta, video)})
        self.e.event('captures_finished', dict(case=self.root.name, metadata=value))

    def stop(self):
        errors = []
        for p in self.processes:
            try:
                if p.poll() is None:
                    os.killpg(p.pid, signal.SIGTERM)
                    try:
                        p.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        os.killpg(p.pid, signal.SIGKILL)
                        p.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired) as error:
                errors.append(error)
        for log in self.logs:
            log.close()
        if errors and self.e:
            self.e.event('capture_teardown_uncertain', dict(pids=[p.pid for p in self.processes], errors=[str(e) for e in errors]))
        self.processes, self.logs = [], []
        require(not errors, 'capture teardown uncertain')
