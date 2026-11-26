const fs = require('node:fs');
const vm = require('node:vm');
const ts = require(process.cwd() + '/backend/node_modules/typescript');
const root = process.cwd();
function load(file, dependencies) {
  const exports = {};
  const code = ts.transpileModule(fs.readFileSync(root + '/' + file, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, experimentalDecorators: true }
  }).outputText;
  vm.runInNewContext(code, { exports, require: n => {
    if (!(n in dependencies)) throw new Error('Unexpected import: ' + n);
    return dependencies[n];
  }, Request, Response, Headers, AbortSignal, console: {error() {}}, Date, Map, Set, Number, Promise });
  return exports;
}
class HttpException extends Error {constructor(body,status) {super(body.message);this.status=status;}}
const {ApiReadRateLimitService} = load('backend/src/modules/shared/api-read-rate-limit.service.ts', {
  '@nestjs/common': { Injectable: () => target => target, HttpException, HttpStatus: {TOO_MANY_REQUESTS:429} },
  '../cache/cache.service': {}, '../discussions/utils/ip-masking.util': { IpMaskingUtil: {
    requireClientIp: r => r.headers['x-lawcast-client-ip'], hashIp: x => x
  }}, '../../utils/logger.utils': { LoggerUtils:{getContextLogger:()=>({})} }
});
const forwarding = load('frontend/src/lib/server/client-ip.ts', {});
function newSitemap() {return load('frontend/src/lib/server/sitemap.ts', {
  '$app/env/private': {API_BASE_URL:'http://fixture/api'},
  '@sveltejs/kit': {error:(status,message)=>{throw Object.assign(new Error(message),{status});}},
  '#lib/server/client-ip.ts': forwarding
});}
(async()=>{
 for(const throttled of [false,true]) {
  let now=0, calls=0, rejected=0;
  const counts=new Map();
  const limiter=new ApiReadRateLimitService({
    getNumber:async k=>{const v=counts.get(k);return v&&v.expires>now?v.count:null;},
    setNumber:async(k,count,ttl)=>counts.set(k,{count,expires:now+ttl})
  });
  const fakeFetch=async (url,options)=>{
    calls++;
    if(throttled) try {await limiter.assertAllowed({headers:Object.fromEntries(options.headers)},'expensive');}
    catch(e){rejected++;return new Response('{}',{status:e.status});}
    const p=Number(new URL(url).searchParams.get('page'));
    const total=22740, limit=100;
    const items=Array.from({length:Math.max(0,Math.min(limit,total-(p-1)*limit))},(_,i)=>({num:2200001+(p-1)*limit+i}));
    return Response.json({data:{items,total,page:p,limit,totalPages:Math.ceil(total/limit)}});
  };
  const s=newSitemap(), req=new Request('http://fixture/sitemap.xml');
  const index=await s.cachedSitemap('index',async()=>s.sitemapIndex('http://fixture',(await s.fetchArchivePage(fakeFetch,req,1)).total));
  const statuses=[];
  for(let c=0;c<46;c++) statuses.push((await s.cachedSitemap('chunk'+c,()=>s.noticeSitemap('http://fixture',c,fakeFetch,req))).status);
  console.log(JSON.stringify({mode:throttled?'REAL_30_PER_60_LIMIT':'NO_LIMIT_FIXTURE',index:index.status,chunks200:statuses.filter(x=>x===200).length,chunks503:statuses.filter(x=>x===503).length,firstFailedChunk:statuses.indexOf(503),backendCalls:calls,backend429:rejected}));
  if(throttled){now=61000;const c=statuses.indexOf(503);const retry=await s.cachedSitemap('chunk'+c,()=>s.noticeSitemap('http://fixture',c,fakeFetch,req));console.log('AFTER_61_SECONDS chunk='+c+' status='+retry.status);}
 }
})().catch(e=>{console.error(e);process.exitCode=1;});
