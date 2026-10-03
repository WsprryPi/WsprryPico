"""Bounded injected observer: one excess handshake, original INFO and peer proof."""
import concurrent.futures,time,ssl
REFUSALS=(ConnectionResetError,ConnectionRefusedError,BrokenPipeError,ssl.SSLEOFError)
def require(value,message):
 if not value:raise ValueError(message)
def assess(before,observations,outcome,elapsed):
 require(elapsed<=15,'capacity observation deadline')
 require(outcome in ('reset','eof','refused','tls_alert'),'actual peer refusal required; timeout is inconclusive')
 require(observations,'original capacity INFO required')
 pending=False
 for value in observations:
  require(value['boot']==before['boot'] and value['source']==before['source'],'capacity identity changed')
  require(value['active']==2 and value['pending'] in (0,1),'two occupied TLS slots must remain active')
  pending=pending or value['pending']==1
 final=observations[-1]
 require(final['pending']==0 and final['pool']==before['pool'],'pending resources not reclaimed')
 require(pending or final['rejected']>before['rejected'],'actual pending transition or rejection counter missing')
 return {'status':'OBSERVED_EXCESS_REFUSAL_AND_RECLAMATION','target_exact_10s_qualified':False,'observer_elapsed_s':elapsed,'actual_peer_outcome':outcome,'boot':final['boot'],'source':final['source'],'final_pool':final['pool'],'final_pending':final['pending'],'active':final['active']}
def run(connector,observe,owner_status,held_progress,emit,deadline,*,clock=time.monotonic,sleeper=time.sleep):
 start=clock();require(deadline-start>=15,'remaining wave budget');end=start+15
 before=observe();emit('capacity_before',before);require(before['active']==2 and before['pending']==0,'two occupied slots')
 observations=[];outcome=None;peer=None
 pool=concurrent.futures.ThreadPoolExecutor(max_workers=1)
 def attempt():
  try:return connector(end)
  except REFUSALS as error:return ('reset' if isinstance(error,ConnectionResetError) else 'eof' if isinstance(error,ssl.SSLEOFError) else 'refused',None)
  except ssl.SSLError as error:
   if getattr(error,'reason',None) in ('TLSV1_ALERT_ACCESS_DENIED','SSLV3_ALERT_HANDSHAKE_FAILURE'):return ('tls_alert',None)
   raise
 try:
  future=pool.submit(attempt)
  while True:
   require(clock()<end,'capacity observer timeout is inconclusive')
   owner_status(end);held_progress(end)
   value=observe();observations.append(value);emit('capacity_info',value)
   if future.done() and outcome is None:
    result=future.result()
    if isinstance(result,tuple):outcome,peer=result
    else:peer=result;raise ValueError('third handshake succeeded; occupied-slot evidence not qualified')
   if outcome is not None and value['pending']==0 and value['pool']==before['pool']:
    break
   sleeper(min(.1,max(0,end-clock())))
  return assess(before,observations,outcome,clock()-start)
 finally:
  if peer is not None:peer.close()
  pool.shutdown(wait=True,cancel_futures=True)
