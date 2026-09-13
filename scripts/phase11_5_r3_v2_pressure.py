#!/usr/bin/env python3
"""Opt-in bounded existing TLS/transport mechanisms on the identified v2 image."""
import argparse
import json
from pathlib import Path
from phase11_5_inventory import require
from phase11_5_r3_v2_pressure_plan import validate
from phase11_5_r3_tls_pressure import main as pressure_main,Pressure
from phase11_5_r3_transport_pressure import TransportPressure

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True);parser.add_argument('--run',action='store_true')
    args=parser.parse_args()
    if not args.run:print('Plan only; no sockets or device access.')
    else:
        root=args.root.resolve(strict=True);packet=validate(json.loads((root/'packet.json').read_text()))
        require((root/'packet.json').read_bytes()==(root/'jobs.json').read_bytes(),'Pressure packet copy differs')
        pressure_main(Pressure if packet['pressure_family']=='tls' else TransportPressure)
