#!/usr/bin/env python3
"""Station observation stays within the original finite save request budget."""
import ast, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import phase12_populated_dispatch as dispatch
import phase12_populated_tests as original


class Tests(unittest.TestCase):
    def exercise(self, restart, fail=False):
        now = [0.]
        attempts = [3]  # The initial public status, START and single SUBMIT.
        old, fresh, digest = 'a' * 32, 'b' * 32, 'c' * 64

        def observe():
            changed = now[0] >= restart
            return dict(provisioning_generation=6 if changed else 5,
                        status={'boot_id': fresh if changed else old})

        def slot():
            attempts[0] += 1
            self.assertLessEqual(attempts[0], 100)
            if fail:
                raise OSError('response missing')
            return dict(device_id=dispatch.DEVICE, generation=5, boot_id=old,
                        request_id_digest=digest, slot_state='trial')

        try:
            result = dispatch.wait_saved_boot(
                observe, slot, 'station', 5, old, digest, 125,
                clock=lambda: now[0], sleeper=lambda x: now.__setitem__(0, now[0] + x))
            return now[0], attempts[0], result
        except ValueError:
            self.assertEqual(now[0], 125)
            self.assertLessEqual(attempts[0], 66)
            raise

    def test_sixty_second_delayed_restart_stays_inside_original_budget(self):
        elapsed, attempts, _ = self.exercise(60)
        self.assertEqual(elapsed, 60)
        self.assertLessEqual(attempts, 33)

    def test_late_restart_and_lost_slot_responses_no_budget_increase(self):
        elapsed, attempts, _ = self.exercise(124, True)
        self.assertEqual(elapsed, 124)
        self.assertLessEqual(attempts, 65)

    def test_missing_restart_refused_at_original_deadline(self):
        for fail in (False, True):
            with self.subTest(fail=fail), self.assertRaisesRegex(ValueError, 'single save reboot deadline'):
                self.exercise(float('inf'), fail)

    def test_original_transient_and_cross_observer_binding_cases(self):
        tests = original.Tests()
        tests.test_transient_attempt_old_generation_then_commit_then_reboot()
        tests.test_old_info_then_new_http_then_independent_new_info()

    def test_late_info_and_slot_cannot_accept_a_fresh_boot(self):
        for late in ('info', 'slot'):
            with self.subTest(late=late):
                now = [124.]
                calls = []

                def observe():
                    calls.append('info')
                    if late == 'info':
                        now[0] = 125.1
                    return dict(provisioning_generation=6 if late == 'info' else 5,
                                status={'boot_id': 'b' * 32 if late == 'info' else 'a' * 32})

                def slot():
                    calls.append('slot')
                    now[0] = 125.1
                    return dict(device_id=dispatch.DEVICE, generation=6,
                                boot_id='b' * 32, request_id_digest='c' * 64)

                with self.assertRaisesRegex(ValueError, 'late single save'):
                    dispatch.wait_saved_boot(observe, slot, 'station', 5, 'a' * 32,
                                             'c' * 64, 125, clock=lambda: now[0])
                self.assertEqual(calls, ['info'] if late == 'info' else ['info', 'slot'])

    def post_save_join(self, ready_at):
        # Execute the real receive-proof block with an injected clock/carrier.
        tree = ast.parse(Path(dispatch.__file__).read_text())
        block = next(n for n in ast.walk(tree)
                     if isinstance(n, ast.If) and ast.unparse(n.test) == 'trial_ap')
        now, calls = [141.], []
        observed = dict(network={'link_status': -3}, status={'boot_id': 'b' * 32},
                        provisioning_generation=7)

        class Clock:
            @staticmethod
            def monotonic():
                return now[0]

            @staticmethod
            def sleep(value):
                now[0] += value

        class Evidence:
            def record(self, *args, **kwargs):
                pass

        def info():
            return dict(observed, network={'link_status': 3 if now[0] >= ready_at else -3})

        def fixture(request):
            calls.append(request)
            return {'status': 'TARGET_ASSOCIATION_VERIFIED'}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'fixture-ap-proof.json').write_text('{}')
            namespace = dict(trial_ap=True, root=root, time=Clock, deadline=300,
                             end=196, observed=observed, generation=6, info=info,
                             counter=dispatch.counter, require=dispatch.require,
                             fixture_action=fixture, kind='station', evidence=Evidence(),
                             request={'authority': 'test', 'source_commit': 'c' * 40})
            exec(compile(ast.fix_missing_locations(ast.Module(body=[block], type_ignores=[])),
                         str(dispatch.__file__), 'exec'), namespace)
        return now[0], calls

    def test_post_save_join_uses_remaining_case_budget(self):
        elapsed, calls = self.post_save_join(249)
        self.assertEqual(elapsed, 249)
        self.assertEqual([x['action'] for x in calls], ['prove_target', 'stop'])
        self.assertEqual(calls[0]['remaining_s'], 51)

    def test_post_save_join_never_extends_the_original_case_deadline(self):
        with self.assertRaisesRegex(ValueError, 'trial association deadline'):
            self.post_save_join(float('inf'))


if __name__ == '__main__':
    unittest.main()
