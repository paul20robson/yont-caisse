import re,shutil,zipfile,os,hashlib,json
src=open('out/YONT_Caisse.html',encoding='utf8').read()
v=open('out/version.txt').read().strip()
head='<link rel="manifest" href="manifest.webmanifest"><meta name="theme-color" content="#0F3323"><link rel="apple-touch-icon" href="apple-touch-icon.png"><link rel="icon" type="image/png" href="icon-192.png"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="YONT Caisse"><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"><meta name="application-name" content="YONT Caisse">'
src=src.replace('<title>',head+'<title>',1)
reg='<script>if("serviceWorker" in navigator&&/^https?:/.test(location.protocol))addEventListener("load",()=>navigator.serviceWorker.register("sw.js").catch(()=>{}));</script>'
i=src.rfind('</body>');src=src[:i]+reg+src[i:]
# --- version légère : outils lourds dans des fichiers séparés, chargés après l'ouverture ---
def cut(s,start_marker):
    i=s.find(start_marker);assert i>=0,start_marker
    j=s.find('</script>',i);body=s[i+len('<script>'):j];return s[:i]+s[j+len('</script>'):],body
src,xl=cut(src,'<script>/*! xlsx.js');open('pwa/xlsx.js','w',encoding='utf8').write(xl.replace('<\\/script','</script'))
src,jp=cut(src,'<script>/** @license');assert 'jsPDF' in jp[:300];open('pwa/jspdf.js','w',encoding='utf8').write(jp.replace('<\\/script','</script'))
i=src.find('const BP={');j=src.find('};\nconst LOGO_DEF',i);assert i>0 and j>i
lit=src[i+len('const BP='):j+1]
open('pwa/bp.js','w',encoding='utf8').write('(function(){var o='+lit+';var B=window.__BP||(window.__BP={});for(var k in o)B[k]=o[k];if(window.__bpLoaded)window.__bpLoaded()})();')
src=src[:i]+'const BP=window.__BP||(window.__BP={});'+src[j+2:]
k=src.rfind('<script>\nconst APP_VERSION');assert k>0
# chaque fichier lourd est repéré par l'empreinte de son contenu : il n'est retéléchargé que s'il change
H={f:hashlib.md5(open('pwa/'+f,'rb').read()).hexdigest()[:10] for f in ['bp.js','jspdf.js','xlsx.js']}
LZ=['%s?h=%s'%(f,H[f]) for f in ['bp.js','jspdf.js','xlsx.js']]
src=src[:k]+'<script>window.__LAZY='+json.dumps(LZ)+'</script>'+src[k:]
open('pwa/index.html','w',encoding='utf8').write(src)
sw=r'''const C="resto-caisse-%s";const CL="resto-caisse-libs";const CORE=["./","./manifest.webmanifest","./icon-192.png","./icon-512.png","./icon-maskable-512.png","./apple-touch-icon.png"];const LZ=%s;
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
'''%(v,json.dumps(['./'+u for u in LZ]))
open('pwa/sw.js','w').write(sw)
import json as _j,datetime as _d
open('pwa/version.json','w').write(_j.dumps({"v":v,"date":_d.date.today().isoformat(),"notes":open('notes.txt',encoding='utf8').read().strip()},ensure_ascii=False))
open('pwa/_headers','w').write("/sw.js\n  Cache-Control: no-cache\n/version.json\n  Cache-Control: no-store\n/index.html\n  Cache-Control: no-cache\n/\n  Cache-Control: no-cache\n/manifest.webmanifest\n  Cache-Control: no-cache\n/bp.js\n  Cache-Control: public, max-age=31536000, immutable\n/jspdf.js\n  Cache-Control: public, max-age=31536000, immutable\n/xlsx.js\n  Cache-Control: public, max-age=31536000, immutable\n")
man=_j.load(open('pwa/manifest.webmanifest'))
man.pop("shortcuts",None);man.update({"id":"./index.html","start_url":"./","display":"standalone","display_override":["fullscreen","standalone"],"theme_color":"#0F3323","background_color":"#0F3323","orientation":"any"})
open('pwa/manifest.webmanifest','w').write(_j.dumps(man,ensure_ascii=False,indent=2))
open('pwa/LISEZMOI.txt','w',encoding='utf8').write("""YONT CAISSE - Application installable
==========================================
Ce dossier contient l'application prête à être mise en ligne.
Mettez TOUS les fichiers du dossier en ligne ensemble (Netlify ou GitHub Pages),
puis ouvrez l'adresse obtenue dans Chrome et choisissez « Installer l'application ».
Les données restent sur chaque appareil : activez la sauvegarde automatique (Paramètres > Sauvegarde en ligne).
Pour mettre à jour : remplacez les fichiers en ligne par la nouvelle version ;
l'application se met à jour à la prochaine ouverture avec internet.
""")
os.makedirs('out',exist_ok=True)
z='out/YONT_Caisse_application.zip'
with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf:
    for f in ['index.html','manifest.webmanifest','sw.js','version.json','_headers','bp.js','jspdf.js','xlsx.js','icon-192.png','icon-512.png','icon-maskable-512.png','apple-touch-icon.png','LISEZMOI.txt']:
        zf.write('pwa/'+f,'resto-caisse/'+f)
print('zip',os.path.getsize(z),'v',v)
