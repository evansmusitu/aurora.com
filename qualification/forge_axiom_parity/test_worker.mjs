import assert from 'node:assert/strict';
import worker from './worker.mjs';

const PROTOCOL='c9fe2c0dcbc51ed7329aeea8b8d9985c0ccfc70123ac181c755285f1a0fbf3de';

class FakeStatement {
  constructor(db,sql){this.db=db;this.sql=sql;this.args=[];}
  bind(...args){this.args=args;return this;}
  async run(){
    if(this.sql.includes('INSERT INTO edge_rate_buckets')){
      const key=`${this.args[0]}:${this.args[1]}`;
      this.db.counts.set(key,(this.db.counts.get(key)||0)+1);
    }
    return {success:true};
  }
  async first(){
    const key=`${this.args[0]}:${this.args[1]}`;
    return {request_count:this.db.counts.get(key)||0};
  }
}
class FakeDB {
  constructor(){this.counts=new Map();}
  prepare(sql){return new FakeStatement(this,sql);}
}

function env(extra={}){
  return {
    FORGE_DB:new FakeDB(),
    FORGE_PROTOCOL_DIGEST:PROTOCOL,
    FORGE_EDGE_RPM_LIMIT:'600',
    MODAL_ORIGIN:'https://private.modal.run',
    MODAL_KEY:'wk-private',
    MODAL_SECRET:'ws-private',
    ...extra,
  };
}

let upstreamCalls=[];
globalThis.fetch=async (url,init={})=>{
  upstreamCalls.push({url:String(url),method:init.method,headers:new Headers(init.headers)});
  return new Response(JSON.stringify({schema:'musitu.forge.health.v1',canonical_service_origin:'https://forge.mftintelligence.com',protocol_digest:PROTOCOL,production_authorized:false})+'\n',{status:200,headers:{'content-type':'application/json','server':'hidden-upstream'}});
};

async function body(response){return JSON.parse(await response.text());}

{
  upstreamCalls=[];
  const r=await worker.fetch(new Request('https://forge.mftintelligence.com/v1/health',{method:'DELETE'}),env());
  assert.equal(r.status,405); assert.equal((await body(r)).error,'method_not_allowed'); assert.equal(upstreamCalls.length,0);
}
{
  const r=await worker.fetch(new Request('https://forge.mftintelligence.com/not-v1'),env());
  assert.equal(r.status,404); assert.equal((await body(r)).error,'route_not_found');
}
{
  upstreamCalls=[];
  const r=await worker.fetch(new Request('https://forge.mftintelligence.com/v1/field/assignments'),env());
  assert.equal(r.status,401); assert.equal((await body(r)).error,'protocol_digest_mismatch'); assert.equal(upstreamCalls.length,0);
}
{
  const r=await worker.fetch(new Request('https://forge.mftintelligence.com/v1/health'),env({MODAL_ORIGIN:''}));
  assert.equal(r.status,503); assert.equal((await body(r)).error,'private_runtime_not_configured');
}
{
  upstreamCalls=[];
  const req=new Request('https://forge.mftintelligence.com/v1/health',{headers:{'Modal-Key':'attacker','Modal-Secret':'attacker'}});
  const r=await worker.fetch(req,env());
  assert.equal(r.status,200); assert.equal(upstreamCalls.length,1);
  assert.equal(upstreamCalls[0].headers.get('modal-key'),'wk-private');
  assert.equal(upstreamCalls[0].headers.get('modal-secret'),'ws-private');
  assert.equal(upstreamCalls[0].headers.get('x-musitu-edge'),'forge-cloudflare-modal-v1');
  assert.equal(r.headers.get('server'),null);
  assert.equal(r.headers.get('x-musitu-edge'),'forge-cloudflare-modal-v1');
}
{
  upstreamCalls=[];
  const e=env({FORGE_EDGE_RPM_LIMIT:'1'});
  const headers={'X-MUSITU-Client-Protocol':PROTOCOL,'Authorization':'Bearer test-token'};
  const r1=await worker.fetch(new Request('https://forge.mftintelligence.com/v1/field/assignments',{headers}),e);
  assert.equal(r1.status,200);
  const r2=await worker.fetch(new Request('https://forge.mftintelligence.com/v1/field/assignments',{headers}),e);
  assert.equal(r2.status,429); assert.equal((await body(r2)).error,'edge_rate_limit_exceeded');
  assert.equal(upstreamCalls.length,1);
}
{
  const prior=globalThis.fetch;
  globalThis.fetch=async()=>{throw new Error('offline');};
  const r=await worker.fetch(new Request('https://forge.mftintelligence.com/v1/health'),env());
  assert.equal(r.status,503); assert.equal((await body(r)).error,'private_runtime_unavailable');
  globalThis.fetch=prior;
}

console.log('FORGE_AXIOM_PARITY_EDGE_PREFLIGHT_PASS tests=7 worker_blob=918ec9ba828e367022c231f80344abf50a6210a1');
