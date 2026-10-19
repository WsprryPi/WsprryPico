"""Evidence tests for immutable offered/rejected packet visibility."""
import copy
from pathlib import Path
import sys
import json
import subprocess
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from rf_analysis.ntp_packets import PacketHistory
ENGINE = sys.argv.pop(1) if len(sys.argv) == 2 else None


def page(first=1,last=4):
    return dict(ok=True,schema='microchrony-packet-page/1',device_id='device',boot_id='boot',
        firmware='image',revision='rev',observed_raw_ns=str(last*10+1),
        oldest_id=str(max(1,last-31)),last_id=str(last),
        lost_before=str(max(1,last-31)-1),overwritten=str(max(1,last-31)-1),
        next_cursor=str(min(last,first+3)),more=first+3<last,
        records=[dict(id=str(i),slot=0,endpoint='4294967295',clock_epoch='2',
            request_raw_ns=str(i*10),receive_raw_ns=str(i*10+1),request_token=str(i),
            length=48,prefix_hex='24'+'00'*47,truncated=False,accepted=True,reason='accepted')
            for i in range(first,min(first+4,last+1))])


class Evidence(unittest.TestCase):
    def history(self):return PacketHistory('device','boot','image','rev')

    def test_prefix_corruption_and_identity_are_transactional(self):
        for change in [lambda p:p.update(boot_id='other'),
                       lambda p:p['records'][-1].update(prefix_hex='00'),
                       lambda p:p['records'][-1].update(accepted=False),
                       lambda p:p.update(next_cursor='3')]:
            p=page();change(p);h=self.history()
            with self.assertRaises(ValueError):h.ingest(p)
            self.assertEqual((h.cursor,h.pages,h.accepted,h.rejected),(0,0,0,0))
            self.assertEqual(len(h.ingest(page())),4)

    def test_initial_and_new_overwrite_are_distinct(self):
        h=self.history();p=page(9,40)
        with self.assertRaisesRegex(ValueError,'gap'):h.ingest(p)
        h.ingest(p,allow_initial_gap=True)
        self.assertEqual((h.cursor,h.first_gap),(12,8))
        p=page(13,40);p['lost_before']='0'
        h.ingest(p)
        p=page(49,80);p['lost_before']='32'
        with self.assertRaisesRegex(ValueError,'gap'):h.ingest(p,allow_initial_gap=True)
        self.assertEqual(h.cursor,16)

    def test_rejected_truncated_packet_preserved_but_never_accepted(self):
        p=page();r=p['records'][1]
        r.update(length=300,truncated=True,accepted=False,reason='correlation')
        h=self.history();out=h.ingest(p)
        self.assertEqual(out[1],r)
        self.assertEqual((h.accepted,h.rejected),(3,1))
        p=copy.deepcopy(p);p['records'][1]['accepted']=True
        with self.assertRaises(ValueError):self.history().ingest(p)

    def test_empty_and_exhausted_frontiers(self):
        p=page(1,0);h=self.history()
        self.assertEqual(h.ingest(p),[])
        h.ingest(page())
        p=page(5,4);p['lost_before']='0'
        self.assertEqual(h.ingest(p),[])
        self.assertEqual(h.cursor,4)

    def test_observation_frontier_bounds_record_time_and_never_regresses(self):
        h=self.history();p=page();p['observed_raw_ns']='40'
        with self.assertRaisesRegex(ValueError,'raw time'):h.ingest(p)
        self.assertEqual((h.cursor,h.last_observed),(0,0))
        h.ingest(page())
        p=page(5,4);p['lost_before']='0';p['observed_raw_ns']='40'
        with self.assertRaisesRegex(ValueError,'regressed'):h.ingest(p)
        self.assertEqual((h.cursor,h.last_observed),(4,41))

    @unittest.skipUnless(ENGINE,'Pass the built ntp_work_tests for the producer/consumer check')
    def test_actual_producer_pages_including_overwrite_and_rejection(self):
        run=subprocess.run([ENGINE,'packet-evidence'],capture_output=True,text=True,check=True,timeout=10)
        h=PacketHistory('device','boot','image','revision')
        pages=[json.loads(line) for line in run.stdout.splitlines()]
        for p in pages:h.ingest(p,allow_initial_gap=not h.pages)
        self.assertEqual((h.cursor,h.first_gap,h.accepted,h.rejected),(81,49,31,1))


if __name__=='__main__':unittest.main()
