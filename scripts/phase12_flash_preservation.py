"""Strict same-bank flash preservation with pinned BTstack CCC bookkeeping only."""
import struct

BLE_START=0x3f5000
BLE_END=0x3f7000
CONFIG_START=0x3fb000
CONFIG_END=0x3fd000

def require(ok, message):
    if not ok: raise ValueError(message)

def records(bank):
    require(len(bank)==4096 and bank[:7]==b'BTstack' and bank[7]<4,'BLE bank header')
    result=[];at=8
    while at+8<=4096:
        tag,size=struct.unpack_from('>II',bank,at)
        if tag==0xffffffff:
            require(bank[at:]==b'\xff'*(4096-at),'BLE erased tail')
            return result
        require(size in (8,16,60) and at+8+size<=4096,'BLE record framing')
        result.append((tag,bank[at+8:at+8+size]));at+=8+size
    raise ValueError('BLE missing tail')

def ccc(tag,payload,peers):
    require(tag==0 or 0x42544300<=tag<=0x42544313,'CCC tag')
    require(len(payload)==8,'CCC size')
    seq,handle,value,device=struct.unpack('<IHBB',payload)
    require(seq>0 and handle>0 and value in (1,2,3) and device in peers,'CCC encoding/bond reference')

def preserve(before,after):
    require(len(before)==len(after)==0x400000,'exact flash size')
    require(before[:BLE_START]==after[:BLE_START] and before[BLE_END:CONFIG_START]==after[BLE_END:CONFIG_START]
            and before[CONFIG_END:]==after[CONFIG_END:],'nonconfiguration/nonBLE byte preservation')
    old=before[BLE_START:BLE_END];new=after[BLE_START:BLE_END]
    if old==new:return
    # A finite append/delete transaction does not permit bank migration or
    # replacement of deleted root/bond history. All old payloads remain exact.
    changed=0
    for index in range(2):
        a=old[index*4096:(index+1)*4096];b=new[index*4096:(index+1)*4096]
        if a==b:continue
        changed+=1
        require(a[:8]==b[:8],'same bank epoch/header')
        ar=records(a);br=records(b)
        require(len(br)>=len(ar) and len(br)-len(ar)<=20,'finite CCC appends')
        peers={tag-0x42544400 for tag,p in ar if 0x42544400<=tag<=0x42544403 and len(p)==60}
        require(len(peers)==1,'one original active bond')
        require({tag for tag,p in ar if tag in (0x534d4552,0x534d4952)}=={0x534d4552,0x534d4952},'both roots present')
        for tag,p in ar:
            if tag in (0x534d4552,0x534d4952,0x42544442):require(len(p)==16,'root/database size')
            if 0x42544400<=tag<=0x42544403:require(len(p)==60,'peer size')
        tags=[tag for tag,p in ar if tag]
        require(len(tags)==len(set(tags)),'unique original tags')
        for tag,p in ar:
            require(tag==0 or tag in (0x534d4552,0x534d4952,0x42544442) or 0x42544400<=tag<=0x42544403 or 0x42544300<=tag<=0x42544313,'known original tag')
            if 0x42544300<=tag<=0x42544313:ccc(tag,p,peers)
        for (tag,p),(next_tag,q) in zip(ar,br):
            require(p==q,'original BLE payload exact')
            if tag!=next_tag:
                require(next_tag==0 and 0x42544300<=tag<=0x42544313,'only existing CCC deletion')
        for tag,p in br[len(ar):]:ccc(tag,p,peers)
        active=[tag for tag,p in br if tag]
        require(len(active)==len(set(active)),'unique resulting active tags')
    require(changed==1,'one bounded BLE bank transaction')
