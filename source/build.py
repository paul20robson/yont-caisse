pre=open('head.html',encoding='utf8').read()
s=open('resto/index.html',encoding='utf8').read()
import hashlib,json,os
h=hashlib.md5(s.encode()).hexdigest()
vf='ver_state.json';st=json.load(open(vf)) if os.path.exists(vf) else {"base":"4.1","n":0,"h":""}
if st["h"]!=h:st["n"]+=1;st["h"]=h;json.dump(st,open(vf,'w'))
VER=f'{st["base"]}.{st["n"]}';open('out/version.txt','w').write(VER)
s=s.replace('const APP_VERSION="__APPVER__";',f'const APP_VERSION="{VER}";')
x=open('node_modules/xlsx/dist/xlsx.full.min.js',encoding='utf8').read()
j=open('node_modules/jspdf/dist/jspdf.umd.min.js',encoding='utf8').read()
s=s.replace('<script defer src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>','<script>'+x.replace('</script','<\\/script')+'</script>')
s=s.replace('<script defer src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>','<script>'+j.replace('</script','<\\/script')+'</script>')
i=s.find('<div class="top">')
out=pre+s[:i]+'</head><body>\n'+s[i:]+'\n</body></html>\n'
assert 'cdnjs.cloudflare.com/ajax/libs/xlsx' not in out
open('out/YONT_Caisse.html','w',encoding='utf8').write(out);print(len(out))
