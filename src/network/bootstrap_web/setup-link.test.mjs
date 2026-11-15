import assert from 'node:assert/strict';
import {test} from 'node:test';
import {createSetupLink} from './setup-link.js';

test('setup copy handles native fallback, refusal, focus, state, and asynchronous races', async () => {
    const elements = new Map();
    const doc = {getElementById:id=>elements.get(id)};
    for (const id of ['setup-link-panel','setup-url','setup-hostname','copy-setup-link',
        'setup-copy-status','setup-link-state','setup-link-help','setup-link-edit','setup-link-result']) {
        elements.set(id, {value:'',textContent:'',hidden:false,disabled:false,events:{},
            selectionStart:0,selectionEnd:0,selectionDirection:'none',
            addEventListener(event,fn) { this.events[event]=fn; },
            focus() { doc.activeElement=this; }, select() { this.selectionStart=0;this.selectionEnd=this.value.length; },
            setSelectionRange(start,end,direction) { this.selectionStart=start;this.selectionEnd=end;this.selectionDirection=direction; },
            append(child) { child.parentElement=this; }, removeAttribute(name) { delete this[name]; }});
    }
    const $=id=>elements.get(id), url=$('setup-url'), button=$('copy-setup-link'), status=$('setup-copy-status');
    let allowed=true;
    const link=createSetupLink(doc,{allowed:()=>allowed});
    const update=(hostname='pico-a.local',screen='credentials',phase='intended')=>link.update({hostname,screen,phase});
    const click=()=>button.events.click();
    let writes=[];
    globalThis.isSecureContext=false;
    doc.execCommand=command=>{assert.equal(command,'copy');writes.push(url.value);return true;};
    update();button.focus();
    await click();
    assert.deepEqual(writes,['http://pico-a.local/']);
    assert.equal(status.textContent,'Link copied');assert.equal(doc.activeElement,button);
    update();assert.equal(status.textContent,'Link copied','polling preserves feedback');
    assert.equal($('setup-link-panel').parentElement,$('setup-link-edit'));
    update('pico-b.local');assert.equal(status.textContent,'');
    for (const result of [false,'throw',undefined]) {
        doc.execCommand=result===undefined ? undefined : ()=>{if(result==='throw')throw Error('denied');return result;};
        await click();
        assert.match(status.textContent,/Could not copy/);
        assert.equal(doc.activeElement,url);assert.equal(url.selectionEnd,url.value.length);
    }
    link.update({hostname:undefined,screen:'credentials',phase:'intended'});
    assert.equal(button.disabled,true);assert.equal(url.value,'');assert.equal($('setup-hostname').href,undefined);
    const before=writes.length;await click();assert.equal(writes.length,before);

    globalThis.isSecureContext=true;
    let resolve,reject;
    Object.defineProperty(globalThis,'navigator',{configurable:true,value:{clipboard:{writeText(value){
        writes.push(value);return new Promise((yes,no)=>{resolve=yes;reject=no;});
    }}}});
    update();button.focus();
    const pending=click();assert.equal(button.disabled,true);
    await click();assert.equal(writes.length,before+1,'only one clipboard write');
    update('pico-new.local');assert.equal(button.disabled,true);
    assert.equal(url.value,'http://pico-new.local/','manual target remains usable');
    resolve();await pending;assert.equal(status.textContent,'');assert.equal(button.disabled,false);
    const failed=click();reject(Error('permission'));await failed;
    assert.match(status.textContent,/Could not copy/);assert.equal(url.selectionEnd,url.value.length);
    const staleFailure=click();update('pico-next.local');button.focus();reject(Error('denied'));await staleFailure;
    assert.equal(status.textContent,'');assert.equal(doc.activeElement,button,'stale failure never steals focus');
    const movedFocus=click(), elsewhere={};
    doc.activeElement=elsewhere;url.setSelectionRange(0,0,'none');
    reject(Error('denied'));await movedFocus;
    assert.equal(doc.activeElement,elsewhere);assert.equal(url.selectionEnd,0,'delayed failure preserves a subsequent focus/selection');
    const suspended=click();link.suspend();link.resume();resolve();await suspended;
    assert.equal(status.textContent,'');
    button.focus();
    const modal=click();allowed=false;
    reject(Error('delayed refusal'));await modal;
    assert.equal(status.textContent,'');assert.equal(doc.activeElement,button);
    const beforeModal=writes.length;await click();assert.equal(writes.length,beforeModal);
    allowed=true;
    const successful=click();resolve();await successful;assert.equal(status.textContent,'Link copied');
    update('pico-next.local','connected','saved');assert.match($('setup-link-state').textContent,/^Saved/);
    assert.equal($('setup-link-panel').parentElement,$('setup-link-result'));
    update('pico-next.local','unknown');assert.match($('setup-link-state').textContent,/^Intended/);
    update('pico-next.local','retry');assert.equal($('setup-link-panel').hidden,true);assert.equal(button.disabled,true);
});
