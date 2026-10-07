#!/usr/bin/env python3
"""Offline-default LED packet validation; explicit unattended execution on wspr5."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from led_closeout.plan import BOARDS, make_plan, validate_plan
from led_closeout.runner import Evidence, Runner, require
from phase11_5_inventory import loads_console


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inventory', action='store_true', help='Read-only named-board transport/clock inventory')
    p.add_argument('--run', action='store_true', help='Execute prepared autonomous steps; no approval token')
    p.add_argument('--recover', type=Path, help='Restore an interrupted run; never retry its RF jobs')
    p.add_argument('--plan', type=Path)
    p.add_argument('--manifest', type=Path)
    p.add_argument('--setup', type=Path)
    p.add_argument('--board', choices=BOARDS, default='A')
    p.add_argument('--fixture', choices=BOARDS)
    p.add_argument('--steps', nargs='+', type=int, choices=(3,4,5), default=(3,4,5))
    p.add_argument('--cases', nargs='+', help='Canonical case IDs; omit unavailable external/stop fixtures')
    p.add_argument('--budget-from', type=Path, help='Carry spent budget from a restored, definitively terminal run')
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    require(args.budget_from is None or args.run and not args.recover and not args.inventory,
            'budget continuation requires a new live run')
    for target in filter(None, (args.output, args.recover)):
        require(target.resolve().is_relative_to((ROOT/'build').resolve()), 'private evidence must stay under build/')
    plan = validate_plan(loads_console(args.plan.read_text()) if args.plan else make_plan())
    if args.inventory:
        require(not args.run and args.recover is None and args.fixture != args.board and args.output and sys.platform.startswith('linux') and
                os.geteuid() == 0, 'inventory needs Linux exclusive ownership and a private output')
        from led_closeout.device import Device, inventory
        os.umask(0o077)
        e=Evidence(args.output,plan,args.board,args.fixture)
        backend=Device({},e,ROOT)
        complete=inventory(backend,e,args.board,args.fixture)
        print(json.dumps(e.state,sort_keys=True))
        if not complete:
            raise SystemExit(2)
        return
    if not args.run:
        require(args.recover is None, 'recovery requires --run')
        print(json.dumps(plan, sort_keys=True, indent=2))
        return
    require(sys.platform.startswith('linux') and os.geteuid() == 0,
            'live runner uses Linux exclusive USB inventory on wspr5')
    require(args.manifest and args.setup and (args.output or args.recover),
            'live manifest, prepared setup and private output required')
    from led_closeout.device import Device
    from led_closeout.runner import save_json
    manifest, setup = (loads_console(path.read_text()) for path in (args.manifest, args.setup))
    os.umask(0o077)
    def interrupted(signum, frame):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        raise InterruptedError('signal ' + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    if args.recover:
        # Recovery never opens a new budget or replays an ambiguous admission.
        state = loads_console((args.recover/'state.json').read_text())
        e = Evidence.__new__(Evidence)
        e.root, e.state = args.recover, state
        backend = Device(setup, e, ROOT)
        backend.snapshots = loads_console((e.root/'snapshots.json').read_text())
        errors = []
        try:
            from led_closeout.device import validate_manifest, validate_setup
            require(manifest == loads_console((e.root/'manifest.json').read_text()),
                    'recovery must use the frozen run manifest')
            validate_setup(setup, recovery=True)
            from led_closeout.runner import sha256
            from led_closeout.device import validate_uf2, FLASH_SIZE
            restore = manifest['images']['restore']
            require(sha256(restore['uf2']) == restore['uf2_sha256'] and
                    restore['engine'] == 'inhibited-standalone-simulator' and
                    restore['acceptance'] is False, 'recovery inhibited image binding')
            validate_uf2(Path(restore['uf2']).read_bytes())
            for b, snapshot in backend.snapshots.items():
                require(b in (state['board'], state['fixture']) and
                        snapshot['serial'] == BOARDS[b]['serial'] and
                        (Path(snapshot['path']).resolve().is_relative_to(e.root.resolve()) or
                         isinstance(setup.get('retained_snapshots'), dict) and
                         snapshot['path'] == setup['retained_snapshots'][b]['path'] and
                         snapshot['sha256'] == setup['retained_snapshots'][b]['sha256']) and
                        Path(snapshot['path']).stat().st_size == FLASH_SIZE and
                        sha256(snapshot['path']) == snapshot['sha256'], 'recovery backup identity/hash')
            # Reacquire named locks without entering the normal snapshot path.
            backend.lock_boards(state['board'], state['fixture'])
            for board in (state['board'], state['fixture']):
                if board:
                    try:
                        backend.abort(board)
                        backend.restore(board, manifest['images']['restore'])
                    except BaseException as error:
                        errors.append(dict(board=board, error=str(error)))
            e.state['result'] = 'STOP_RECOVERED' if not errors else 'STOP'
            e.state['cleanup'] = 'VERIFIED_INHIBITED' if not errors else 'STOP_UNCERTAIN'
            e.event('recovery', errors)
            e.save()
        finally:
            backend.close()
        require(not errors, 'recovery uncertain')
    else:
        e = Evidence(args.output, plan, args.board, args.fixture)
        if args.budget_from:
            from led_closeout.runner import carry_budget
            carry_budget(e, args.budget_from)
        backend = Device(setup, e, ROOT)
        try:
            Runner(plan, manifest, args.board, backend, e, fixture=args.fixture, steps=args.steps,
                   cases=args.cases).run()
        finally:
            backend.close()
    print(json.dumps(e.state, sort_keys=True))


if __name__ == '__main__':
    main()
