import json,re,statistics,sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from rf_analysis.pps_windows import analyze_windows
if sys.flags.optimize:
 raise RuntimeError('Optimized Python cannot validate assertion-based capture checks')
p=Path(sys.argv[1]);s=p.read_text()
info=re.findall(r'INFO serial=([0-9A-Fa-f]{16}) clock_hz=(\d+) ram_only=1 pps_gp=(\d+) input_gp=(\d+) seconds=300 source=(si5351|known_ratio)',s)
assert len(info)==1 and int(info[0][1])==138000000
source=info[0][4]
assert tuple(map(int,info[0][2:4]))==((3,7) if source=='si5351' else (11,9))
load=re.search(r'END .* loaded=([01]) load_writes=(\d+)',s)
assert load and ((int(load[2])>0) if load[1]=='1' else int(load[2])==0)
assert len(re.findall(r'^LOAD ',s,re.M))==int(load[2])
pulses=[tuple(map(int,m)) for m in re.findall(r'PULSE i=(\d+) raw_low=(\d+) raw_high=(\d+) count_low=(\d+) count_high=(\d+)',s)]
end=re.search(r'END pulses=(\d+) coherent=(\d+) max_gap_us=(\d+) uart_errors=(\d+) nmea_bytes=(\d+) restored=(\d+)',s)
assert end and tuple(map(int,end.groups()))[0:2]==(301,1),end
assert len(pulses)==301 and int(end[4])==0 and int(end[6])==1
assert int(end[3])<400
assert all(i==index and 0<=b-a<=100 and 0<=d-c<=100
           for index,(i,a,b,c,d) in enumerate(pulses))
assert all(b[1]>a[2] and b[3]>a[4] and 999000<=b[1]-a[2]<1001000
           for a,b in zip(pulses,pulses[1:]))
nmea=s.split('NMEA_BEGIN\n')[1].split('NMEA_END')[0]
rmc=[];gga=[];bad=0
for line in nmea.splitlines():
 if not line.startswith('$') or '*' not in line:continue
 payload,check=line[1:].split('*',1)
 crc=0
 for c in payload:crc^=ord(c)
 if len(check)<2 or crc!=int(check[:2],16):bad+=1;continue
 fields=payload.split(',')
 if fields[0].endswith('RMC'):rmc.append(fields)
 if fields[0].endswith('GGA'):gga.append(fields)
assert bad==0 and len(rmc)>=295 and all(x[2]=='A' for x in rmc)
assert len(gga)>=295 and all(int(x[6])>0 for x in gga)
# Conditional engineering PPS endpoint allowance. The vendor's 30 ns typical
# timing figure is NOT a hard maximum. Include 10 us per endpoint explicitly.
pps_endpoint_s=10e-6 if source=="si5351" else 0
rows=[]
for start,stop in [(0,300)]+[(i,i+60) for i in range(0,241,60)]:
 a,b=pulses[start],pulses[stop];n=stop-start
 count_min=b[3]-a[4]-1;count_max=b[4]-a[3]+1
 raw_min=(b[1]-a[2])/1e6;raw_max=(b[2]-a[1])/1e6
 ref_low=(count_min/(n+2*pps_endpoint_s)/1e6-1)*1e9
 ref_high=(count_max/(n-2*pps_endpoint_s)/1e6-1)*1e9
 timer_low=(raw_min/(n+2*pps_endpoint_s)-1)*1e9
 timer_high=(raw_max/(n-2*pps_endpoint_s)-1)*1e9
 rows.append(dict(first_pps=start,last_pps=stop,reference_offset_ppb=[ref_low,ref_high],raw_timer_error_ppb=[timer_low,timer_high]))
result=dict(pulses=len(pulses),max_gap_us=int(end[3]),max_endpoint_width_us=max(b-a for _,a,b,_,_ in pulses),rmc_count=len(rmc),gga_count=len(gga),nmea_checksum_errors=bad,latest_fix=dict(quality=gga[-1][6],satellites=gga[-1][7],hdop=gga[-1][8]),pps_endpoint_allowance_us=pps_endpoint_s*1e6,source=source,loaded=load[1]=="1",load_writes=int(load[2]),window_analysis=analyze_windows(pulses,pps_endpoint_us=pps_endpoint_s*1e6),results=rows,scope='Finite warmed board C bench observation only; conditional PPS allowance; not a full temperature/supply/warmup/aging specification or a production GPS integration result.')
print(json.dumps(result,indent=2))
