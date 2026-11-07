// SPDX-License-Identifier: MIT
// Presentation only. Native disabled controls and application guards own access.
(function(root) {
  'use strict';
  function create({document:doc=root.document,eligible,lock}) {
    // DOM-free behavioral fixtures still exercise the underlying access guards.
    if(!doc?.elementFromPoint)return {update(){},destroy(){}};
    const selector='input,select,textarea,button';
    const marker='data-auth-locked-control';
    const tip=doc.createElement('div');
    tip.id='locked-control-tooltip';tip.className='locked-control-tooltip';tip.role='tooltip';tip.hidden=true;
    tip.textContent='Controls are locked';
    const live=doc.createElement('div');
    live.id='locked-control-announcement';live.className='visually-hidden';live.setAttribute('role','status');live.setAttribute('aria-live','polite');live.setAttribute('aria-atomic','true');
    doc.body.append(tip,live);
    let target=null,timer=null,frame=null,focusFrame=null,gesture=null,destroyed=false;
    const listeners=[];
    function listen(node,type,fn,options=true) {node.addEventListener(type,fn,options);listeners.push(()=>node.removeEventListener(type,fn,options));}
    function described(node,add) {
      const ids=new Set((node.getAttribute('aria-describedby')||'').split(/\s+/).filter(Boolean));
      if(add)ids.add(tip.id);else ids.delete(tip.id);
      if(ids.size)node.setAttribute('aria-describedby',[...ids].join(' '));else node.removeAttribute('aria-describedby');
    }
    function hide() {
      if(focusFrame!==null)root.cancelAnimationFrame(focusFrame);focusFrame=null;
      if(target)described(target,false);
      target=null;tip.hidden=true;live.textContent='';
      if(timer!==null)root.clearTimeout(timer);timer=null;
    }
    function valid(node) {
      const modal=doc.querySelector('dialog:modal');
      return !!node?.isConnected && (!modal||modal.contains(node)) && !node.closest('[hidden],[inert],dialog:not([open])') && node.getClientRects().length>0 && eligible(node);
    }
    function show(node) {
      if(!valid(node))return;
      if(target!==node){hide();target=node;described(node,true);live.textContent=tip.textContent;}
      tip.hidden=false;
      const r=node.getBoundingClientRect(),v=root.visualViewport;
      const left=v?.offsetLeft||0,top=v?.offsetTop||0,width=v?.width||root.innerWidth,height=v?.height||root.innerHeight;
      const scale=tip.getBoundingClientRect().width/tip.offsetWidth||1;
      tip.style.maxWidth=Math.max(0,(width-32)/scale)+'px';
      const t=tip.getBoundingClientRect();
      tip.style.left=Math.max(left+16,Math.min(r.left,left+width-t.width-16))/scale+'px';
      tip.style.top=Math.max(top+8,Math.min(r.top-t.height-8>=top+8?r.top-t.height-8:r.bottom+8,top+height-t.height-8))/scale+'px';
      if(timer!==null)root.clearTimeout(timer);
      // Focused keyboard feedback stays until focus moves or Escape is pressed.
      timer=doc.activeElement===node?null:root.setTimeout(hide,6000);
    }
    function update() {
      if(destroyed)return;
      for(const node of doc.querySelectorAll(selector)) {
        const marked=node.matches(':disabled') && eligible(node);
        if(node.hasAttribute(marker)!==marked)node.toggleAttribute(marker,marked);
      }
      if(target&&!valid(target))hide();
    }
    function schedule() {if(frame===null)frame=root.requestAnimationFrame(()=>{frame=null;update();});}
    function hit(event) {
      const label=event.target.closest?.('label');
      if(label?.control?.hasAttribute(marker)&&valid(label.control))return label.control;
      // Marked native controls are hit-transparent, so disabled-event differences
      // cannot swallow the attempt. No wrapper, overlay or extra field tab stop.
      let found=null,area=Infinity;
      for(const node of doc.querySelectorAll('['+marker+']')) {
        if(!valid(node)||!event.target.contains(node)&&!node.contains(event.target))continue;
        const r=node.getBoundingClientRect();
        if(event.clientX>=r.left&&event.clientX<=r.right&&event.clientY>=r.top&&event.clientY<=r.bottom&&r.width*r.height<area){found=node;area=r.width*r.height;}
      }
      return found;
    }
    listen(doc,'pointerdown',event=>{
      gesture=null;
      const node=hit(event);
      if(node){gesture={id:event.pointerId,x:event.clientX,y:event.clientY};show(node);}else hide();
      // Preserve native touch scrolling; the eventual click is suppressed below.
    });
    listen(doc,'pointerup',event=>{if(gesture?.id===event.pointerId)gesture.released=true;});
    listen(doc,'pointermove',event=>{if(gesture&&!gesture.released&&Math.hypot(event.clientX-gesture.x,event.clientY-gesture.y)>10)hide();});
    listen(doc,'pointercancel',()=>{gesture=null;hide();});
    listen(doc,'click',event=>{
      // Even an unlock between down/up must not turn the locked attempt into a
      // checkbox change, form submission or queued action.
      if(gesture&&(event.pointerId===gesture.id||event.detail>0)) {
        gesture=null;event.preventDefault();event.stopImmediatePropagation();
      }
    });
    listen(doc,'focusin',event=>{
      if(gesture&&!gesture.released&&event.target!==lock)return;
      hide();
      // Native keyboard focus may scroll the lock into view. Present after that
      // scroll settles, while still refusing a stale focus continuation.
      if(event.target===lock)focusFrame=root.requestAnimationFrame(()=>{
        focusFrame=root.requestAnimationFrame(()=>{focusFrame=null;if(doc.activeElement===lock)show(lock);});
      });
    });
    listen(doc,'keydown',event=>{if(event.key==='Escape'||event.key==='Tab')hide();});
    listen(doc,'scroll',()=>{if(target)hide();});
    listen(root,'resize',()=>{if(target)hide();});listen(root,'hashchange',hide);listen(root,'popstate',hide);
    if(root.visualViewport){listen(root.visualViewport,'resize',()=>{if(target)hide();});listen(root.visualViewport,'scroll',()=>{if(target)hide();});}
    const observer=new root.MutationObserver(schedule);
    observer.observe(doc.body,{subtree:true,childList:true,attributes:true,attributeFilter:['disabled','hidden','readonly','open','inert']});
    function destroy() {
      destroyed=true;hide();observer.disconnect();listeners.forEach(remove=>remove());
      if(frame!==null)root.cancelAnimationFrame(frame);
      doc.querySelectorAll('['+marker+']').forEach(node=>node.removeAttribute(marker));
      tip.remove();live.remove();
    }
    listen(root,'pagehide',event=>{if(event.persisted)hide();else destroy();});
    update();return {update,destroy};
  }
  root.WsprryLockedControls=Object.freeze({create});
})(globalThis);
