import { chromium, devices, expect } from '/Users/doyeonkim/Documents/programming/lawcast/frontend/node_modules/@playwright/test/index.mjs';
import { writeFile } from 'node:fs/promises';
const output='/tmp/lawcast-postdeploy-vitals/browser-check.json';
const results=[];
const browser=await chromium.launch({channel:'chrome',headless:true});
try {
 for(const mobile of [false,true]) for(const path of ['/','/status','/notices']) for(let run=1;run<=2;run++) {
  const context=await browser.newContext(mobile?devices['Pixel 7']:{viewport:{width:1365,height:900}});
  await context.addInitScript(()=>{
   window.__probe={lcp:[],shifts:[],longTasks:[],events:[]};
   new PerformanceObserver(list=>{for(const e of list.getEntries()) window.__probe.lcp.push({at:e.startTime,size:e.size,tag:e.element?.tagName,text:e.element?.textContent?.trim().slice(0,90)});}).observe({type:'largest-contentful-paint',buffered:true});
   new PerformanceObserver(list=>{for(const e of list.getEntries()) if(!e.hadRecentInput) window.__probe.shifts.push({at:e.startTime,value:e.value});}).observe({type:'layout-shift',buffered:true});
   new PerformanceObserver(list=>{for(const e of list.getEntries()) window.__probe.longTasks.push({at:e.startTime,duration:e.duration});}).observe({type:'longtask',buffered:true});
   new PerformanceObserver(list=>{for(const e of list.getEntries()) if(e.interactionId) window.__probe.events.push({name:e.name,at:e.startTime,duration:e.duration,interactionId:e.interactionId});}).observe({type:'event',buffered:true,durationThreshold:16});
  });
  const page=await context.newPage();const errors=[];const requests=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push({url:r.url(),type:r.resourceType()}));
  const response=await page.goto('https://law.viento.me'+path+'?__vitals_probe='+crypto.randomUUID(),{waitUntil:'domcontentloaded',timeout:20000});
  expect(response.status()).toBe(200);
  await expect(page.locator('main h1').first()).toBeVisible();
  await expect(page.locator('footer')).toContainText('v1.25.3');
  if(path==='/') await expect(page.getByTestId('home-status-card-archive').locator('.lc-home-signal-value')).not.toHaveText('0');
  if(path==='/status') {const html=await response.text();expect(html).toMatch(/isInitialized[:"\s]+true/);expect(html).not.toContain('상태 정보를 불러오지 못했습니다');}
  await page.waitForFunction(()=>window.__probe.lcp.length>0);
  await page.waitForTimeout(1200);
  const before=await page.evaluate(()=>({nav:performance.getEntriesByType('navigation')[0].toJSON(),probe:structuredClone(window.__probe),resources:performance.getEntriesByType('resource').map(e=>({url:e.name,type:e.initiatorType,start:e.startTime,end:e.responseEnd,size:e.transferSize}))}));
  if(mobile)await page.getByRole('button',{name:'메뉴 열기'}).click();
  await page.getByRole('switch',{name:'다크 테마로 전환'}).filter({visible:true}).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  await page.waitForTimeout(250);
  const events=await page.evaluate(()=>window.__probe.events);
  expect(errors).toEqual([]);
  const row={device:mobile?'mobile':'desktop',path,run,status:response.status(),cache:(await response.allHeaders())['cf-cache-status'],serverTiming:(await response.allHeaders())['server-timing'],before,events,errors,browserApiRequests:requests.filter(r=>new URL(r.url).pathname.startsWith('/api/')),rocketLoader:requests.filter(r=>r.url.includes('rocket-loader'))};
  results.push(row);await writeFile(output,JSON.stringify(results,null,2));
  console.log(row.device,path,run,'LCP',before.probe.lcp.at(-1)?.at,'cache',row.cache,'events',events.map(x=>x.duration));
  await context.close();
 }
 for(const path of ['/','/status']) {
  const context=await browser.newContext({viewport:{width:1365,height:900}});const page=await context.newPage();
  let release;const gate=new Promise(r=>release=r);const pending=[];
  await page.route(/\/_app\/immutable\/.*\.js|www\.googletagmanager\.com\//,async route=>{pending.push(route.request().url());await gate;await route.abort();});
  await page.addInitScript(()=>{window.__ssrLcp=0;new PerformanceObserver(l=>{window.__ssrLcp=l.getEntries().at(-1)?.startTime||0;}).observe({type:'largest-contentful-paint',buffered:true});});
  try {
   const response=await page.goto('https://law.viento.me'+path+'?__vitals_probe='+crypto.randomUUID(),{waitUntil:'commit',timeout:20000});
   await expect(page.locator('main h1').first()).toBeVisible();
   await expect.poll(()=>pending.filter(x=>x.includes('/_app/')).length).toBeGreaterThan(0);
   await expect.poll(()=>page.evaluate(()=>window.__ssrLcp)).toBeGreaterThan(0);
   const v=await page.evaluate(()=>({lcp:window.__ssrLcp,load:performance.getEntriesByType('navigation')[0].loadEventEnd,heading:document.querySelector('main h1')?.textContent}));
   expect(v.load).toBe(0);results.push({kind:'SSR-with-pending-hydration',path,status:response.status(),pending:pending.length,...v});await writeFile(output,JSON.stringify(results,null,2));
  } finally {release();await context.close();}
 }
} finally {await browser.close();}
