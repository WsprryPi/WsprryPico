#!/usr/bin/env python3
"""Phase 14 offline matrix, source-bound Linux bench operations and IQ analysis."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from phase14.plan import BOARDS,BANDS,CLOCKS,MODES,matrix


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='op',required=True)
    sub.add_parser('matrix')
    analyze=sub.add_parser('analyze');analyze.add_argument('directory',type=Path)
    analyze.add_argument('--analysis-name',default='analysis')
    for name in ('inventory','deploy','run'):
        p=sub.add_parser(name);p.add_argument('--output',type=Path,required=True)
        if name!='inventory':
            p.add_argument('--board',choices=BOARDS,required=True)
            p.add_argument('--clock',type=int,choices=CLOCKS,required=True)
            p.add_argument('--manifest',type=Path,required=True)
            p.add_argument('--artifact-dir',type=Path,required=True)
        if name=='run':
            p.add_argument('--bands',nargs='+',choices=BANDS,default=['80m'])
            p.add_argument('--modes',nargs='+',choices=MODES,default=['TONE','WSPR'])
            p.add_argument('--repetitions',type=int,choices=range(1,25),default=1)
            p.add_argument('--duration',type=int)
            p.add_argument('--reference',action='store_true')
            p.add_argument('--workload',choices=('normal','max-events'),default='normal')
            p.add_argument('--browser-credentials',type=Path)
            p.add_argument('--clock-loss',action='store_true')
            p.add_argument('--action',choices=('complete','abort','disconnect'),default='complete')
    args=parser.parse_args()
    if args.op=='matrix':print(json.dumps(matrix(),indent=2));return
    if args.op=='analyze':
        from phase14.analysis import analyze
        print(json.dumps(analyze(args.directory,args.analysis_name)));return
    if not sys.platform.startswith('linux') or os.geteuid()!=0:
        parser.error('physical operations require exclusive Linux/wspr5 access')
    os.umask(0o077)
    if not args.output.resolve().is_relative_to((ROOT/'build').resolve()):
        parser.error('private evidence must stay under build/')
    if args.op!='inventory':
        manifest=json.loads(args.manifest.read_text())
        if (manifest['schema']!='phase14-candidates/1' or manifest['engine']!='pio-dma-gp2' or
            manifest['gp14_enabled'] or manifest['fixtures_enabled'] or manifest['release_qualified']):
            raise ValueError('ordinary unqualified RF candidate required')
        image=manifest['images'][str(args.clock)]['uf2']
        uf2=args.artifact_dir/Path(image['path']).name
        from led_closeout.runner import sha256
        from check_standalone_image import validate_uf2
        if sha256(uf2)!=image['sha256']:raise ValueError('candidate hash mismatch')
        validate_uf2(uf2.read_bytes())
    if args.op=='run':
        # Validate the entire finite batch before opening devices or acquiring RF.
        from phase14.plan import job
        for band in args.bands:
            for mode in args.modes:job(mode,band,args.clock,'preflight',args.duration,args.workload)
    from phase14.live import Rig
    def interrupted(signum,frame):
        signal.signal(signum,signal.SIG_IGN)
        raise InterruptedError('signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    rig=Rig(args.output,ROOT,board=getattr(args,'board',None),receiver=args.op=='run',reference=getattr(args,'reference',False))
    try:
        if args.op=='inventory':print(json.dumps(rig.inventory()))
        elif args.op=='deploy':
            rig.image_hash=image['sha256'];rig.deploy(args.board,uf2,manifest['source_commit'])
            print(json.dumps(rig.inventory([args.board])))
        else:
            sequence=0
            for band in args.bands:
                for mode in args.modes:
                    for repeat in range(args.repetitions):
                        sequence+=1
                        before=rig.idle(args.board)
                        if before['revision']!=manifest['source_commit'][:12]:raise ValueError('installed candidate source mismatch')
                        rig.execute(args.board,args.clock,band,mode,sequence,duration=args.duration,
                                    action=args.action,image_hash=image['sha256'],workload=args.workload,browser_credentials=args.browser_credentials,clock_loss=args.clock_loss)
            if args.clock_loss:
                import time
                end=time.monotonic()+120
                while time.monotonic()<end:
                    recovered=rig.info(args.board)
                    if recovered['status']['clock_state']=='synchronized':
                        rig.e.event('ntp_clock_recovered',recovered);break
                    time.sleep(1)
                else:raise TimeoutError('NTP recovery after owned suppression')
            print(json.dumps(rig.inventory([args.board])))
    finally:rig.close()


if __name__=='__main__':main()
