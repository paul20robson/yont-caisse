const C="resto-caisse-4.1.81";const CL="resto-caisse-libs";const CORE=["./","./manifest.webmanifest","./icon-192.png","./icon-512.png","./icon-maskable-512.png","./apple-touch-icon.png"];const LZ=["./bp.js?h=5c22941842", "./jspdf.js?h=4b39c897d8", "./xlsx.js?h=31e9848e80"];
const LIBS=["https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js","https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js"];
/* les fichiers lourds (photos, PDF, Excel) vont dans un cache à part, gardé d'une version à l'autre : seuls ceux qui ont changé sont téléchargés */
self.addEventListener("install",e=>{e.waitUntil(caches.open(C).then(c=>c.addAll(CORE.map(u=>new Request(u,{cache:"reload"}))).then(()=>Promise.all(LIBS.map(u=>c.add(new Request(u,{mode:"cors"})).catch(()=>{})))))
  .then(()=>caches.open(CL)).then(c=>Promise.all(LZ.map(u=>c.match(u).then(m=>m||c.add(new Request(u,{cache:"reload"})))))).then(()=>self.skipWaiting()))});
self.addEventListener("message",e=>{if(e.data==="skip")self.skipWaiting()});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==C&&k!==CL&&k.startsWith("resto-caisse-")).map(k=>caches.delete(k))))
  .then(()=>caches.open(CL)).then(c=>c.keys().then(rs=>Promise.all(rs.filter(r=>!LZ.some(u=>r.url.endsWith(u.slice(1)))).map(r=>c.delete(r))))).then(()=>self.clients.claim()))});
self.addEventListener("fetch",e=>{const r=e.request;if(r.method!=="GET")return;const u=new URL(r.url);
  if(r.mode==="navigate"||u.pathname.endsWith("/index.html")){e.respondWith(fetch(r).then(res=>{const cp=res.clone();caches.open(C).then(c=>c.put("./",cp));return res}).catch(()=>caches.match("./")));return}
  if(u.origin===location.origin){e.respondWith(caches.match(r).then(m=>m||fetch(r).then(res=>{const cp=res.clone();caches.open(C).then(c=>c.put(r,cp));return res})));return}
  if(u.hostname==="cdnjs.cloudflare.com"){e.respondWith(caches.match(r).then(m=>m||fetch(r).then(res=>{if(res.ok){const cp=res.clone();caches.open(C).then(c=>c.put(r,cp))}return res})));return}
  if(/fonts\.(googleapis|gstatic)\.com$/.test(u.hostname)){e.respondWith(caches.open(C+"-fonts").then(c=>c.match(r).then(m=>{const f=fetch(r).then(res=>{c.put(r,res.clone());return res}).catch(()=>m);return m||f})))}});
