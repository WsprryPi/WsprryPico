"""Reversible host USB deauthorization of the exact Pico, retaining USB power."""
from pathlib import Path
from phase14.plan import BOARDS


class UsbUnavailable:
    def __init__(self,board,evidence,*,sysroot=Path('/sys/bus/usb/devices')):
        self.e=evidence;self.active=False;self.serial=BOARDS[board][0]
        matches=[]
        for path in Path(sysroot).glob('*'):
            try:serial=(path/'serial').read_text().strip()
            except FileNotFoundError:continue
            if serial==self.serial:matches.append(path.resolve())
        if len(matches)!=1:raise ValueError('exact named USB device required')
        self.path=matches[0]
        if (self.path/'authorized').read_text().strip()!='1':raise ValueError('USB entry must already be authorized')
    def set(self,value):
        if (self.path/'serial').read_text().strip()!=self.serial:raise ValueError('USB port identity changed')
        (self.path/'authorized').write_text(str(value)+'\n')
        if (self.path/'authorized').read_text().strip()!=str(value):raise ValueError('USB authorization readback mismatch')
    def start(self):
        self.active=True;self.set(0)
        self.e.event('usb_host_deauthorized',dict(path=str(self.path),serial=self.serial,usb_power_unchanged=True))
    def close(self):
        if self.active:
            self.set(1);self.active=False
            self.e.event('usb_host_reauthorized',dict(path=str(self.path),serial=self.serial))
