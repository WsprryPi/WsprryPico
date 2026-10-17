"""Regression: reject a mislabeled or incompletely wired linked application."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_application_image import validate

RF = '\n'.join(('wsprrypico::rf::start_worker(', 'wsprrypico::rf::WorkerEngine::',
                'wsprrypico::rf::PicoPioDma', 'wsprrypico::rf::Waveform::render('))
SIM = 'wsprrypico::standalone::DryRunEngine::'


class ApplicationImageTests(unittest.TestCase):
    def test_wrong_variant_and_mixed_linkage_are_refused(self):
        validate(RF, 'rf')
        validate(SIM, 'inhibited')
        for symbols, expected in ((RF, 'inhibited'), (SIM, 'rf'),
                                  (RF + SIM, 'rf'), (RF + SIM, 'inhibited'), ('', 'rf'),
                                  ('', 'inhibited')):
            with self.assertRaises(ValueError):
                validate(symbols, expected)

    def test_partial_rf_application_is_refused(self):
        for missing in RF.splitlines():
            with self.assertRaises(ValueError):
                validate(RF.replace(missing, ''), 'rf')


if __name__ == '__main__':
    unittest.main()
