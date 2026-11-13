"""Test de bout en bout de YONT Caisse : deux appareils synchronisés par un faux serveur Supabase.
Vérifie ce qui touche l'argent et les données partagées :
 - total d'une vente et stock après ventes sur deux appareils ;
 - numéros de facture et de bon de cuisine jamais en double, même hors ligne ;
 - prix « à partir de » : impossible d'encaisser sans le prix ;
 - photos du catalogue jamais envoyées au serveur.
Lancer depuis le dossier source :  python3 build.py && python3 tests/test_caisse.py
Sort avec le code 1 au premier contrôle raté."""
import asyncio, json, os, sys, copy
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'out', 'YONT_Caisse.html')
TEST = os.path.join(ROOT, 'out', '_test.html')
URL = 'https://test.supabase.co'

# ---------- faux serveur (même logique que public.yont_sync) ----------
SRV = {'ver': 0, 'depart': 0, 'data': {}, 'journal': {}}
OFF = {'A': False, 'B': False}
def key(e): return str(e['id']) if isinstance(e, dict) and e.get('id') is not None else json.dumps(e, sort_keys=True)
def apply_ops(st, ops):
    st = copy.deepcopy(st)
    for op in ops or []:
        k = op['k']
        if 'u' in op or 'd' in op:
            arr = st.get(k) if isinstance(st.get(k), list) else []
            upd = {key(e): e for e in op.get('u', [])}
            dels = set(op.get('d', []))
            out = [upd.pop(key(e), e) for e in arr]
            out += [e for e in op.get('u', []) if key(e) in upd and upd.pop(key(e), None) is not None]
            st[k] = [e for e in out if key(e) not in dels]
        elif op.get('del'): st.pop(k, None)
        else: st[k] = op.get('v')
    return st
KEYS = {'test-cle': True, 'cle-caisse': False}   # clé de l'espace (gérant) et clé d'un appareil du personnel
PROT = ['sales', 'audit', 'log', 'closures', 'salonTk', 'salonClo', 'logins', 'staff']
def ops_refus(st, ops):
    """Même règle que yont.ops_refus sur le serveur."""
    for op in ops or []:
        k = op['k']
        if k in ('emp', 'payroll', 'payCfg'): return f'« {k} » réservé au gérant'
        if k not in PROT: continue
        if 'v' in op or op.get('del') or op.get('d'): return f'suppression ou remplacement dans « {k} » réservé au gérant'
        old = {x.get('id'): x for x in (st.get(k) or []) if isinstance(x, dict)}
        for e in op.get('u', []):
            o = old.get(e.get('id'))
            if o is None: continue
            if k in ('audit', 'log', 'closures', 'salonClo', 'logins') and o != e: return f'modification dans « {k} » refusée'
            if k == 'sales' and (o.get('items') != e.get('items') or o.get('total') != e.get('total')): return 'articles ou total d\'une facture existante (« sales »)'
    return None
def rpc(fn, p):
    if p.get('cle') not in KEYS: return {'ok': False, 'erreur': 'Clé incorrecte'}
    adm = KEYS[p.get('cle')]
    op = p.get('op')
    if fn == 'yont_sync':
        if op == 'ver': return {'ok': True, 'ver': SRV['ver'], 'admin': adm}
        if op == 'init':
            SRV['ver'] += 1; SRV['depart'] = SRV['ver']; SRV['data'] = json.loads(p['data']); return {'ok': True, 'ver': SRV['ver']}
        if op == 'pull':
            if SRV['ver'] == 0: return {'ok': False, 'erreur': 'Aucun espace partagé'}
            since = int(p.get('since') or 0)
            if since == SRV['ver']: return {'ok': True, 'ver': since, 'batches': []}
            if since >= SRV['depart'] and (since + 1) in SRV['journal']:
                return {'ok': True, 'ver': SRV['ver'], 'batches': [SRV['journal'][v] for v in range(since + 1, SRV['ver'] + 1)]}
            return {'ok': True, 'ver': SRV['ver'], 'full': json.dumps(SRV['data'])}
        if op == 'push':
            if int(p.get('base', -1)) != SRV['ver']: return {'ok': False, 'stale': True, 'ver': SRV['ver']}
            if not adm:
                r = ops_refus(SRV['data'], p.get('ops'))
                if r: return {'ok': False, 'interdit': True, 'ver': SRV['ver'], 'erreur': 'Refusé par le serveur : ' + r}
            SRV['ver'] += 1; SRV['data'] = apply_ops(SRV['data'], p.get('ops')); SRV['journal'][SRV['ver']] = p.get('ops') or []
            return {'ok': True, 'ver': SRV['ver']}
    if fn == 'yont_err':
        SRV.setdefault('errors', []).extend(p.get('items') or []); return {'ok': True, 'n': len(p.get('items') or [])}
    if fn == 'yont_backup': return {'ok': True, 'fichier': 'test.json', 'fichiers': [], 'mois': [], 'annees': []}
    if fn == 'yont_qr_staff': return {'ok': True, 'commandes': []}
    return {'ok': True}
def route_for(name):
    async def rt(route):
        if OFF[name]: return await route.abort()
        fn = route.request.url.rsplit('/', 1)[-1]
        body = json.loads(route.request.post_data or '{}').get('p', {})
        await route.fulfill(status=200, body=json.dumps(rpc(fn, body)), headers={'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'})
    return rt

FAIL = []
def check(label, cond, detail=''):
    print(('OK   ' if cond else 'ÉCHEC') + ' ' + label + (f'  ({detail})' if detail else ''))
    if not cond: FAIL.append(label)

async def main():
    s = open(SRC, encoding='utf8').read(); i = s.index('\nmigrate();\n') + len('\nmigrate();\n')
    open(TEST, 'w', encoding='utf8').write(s[:i] + 'window.__ev=x=>eval(x);' + s[i:])
    async with async_playwright() as p:
        b = await p.chromium.launch(); errs = []
        async def phone(name, pw):
            ctx = await b.new_context(viewport={'width': 400, 'height': 800}); pg = await ctx.new_page()
            await pg.route('https://test.supabase.co/**', route_for(name))
            pg.on('pageerror', lambda e: None if 'erreur de test volontaire' in str(e) else errs.append(name + ': ' + str(e))); pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
            await pg.goto('file://' + TEST); await pg.wait_for_timeout(1200)
            await pg.fill('#lgU', 'olivier'); await pg.fill('#lgP', '0000'); await pg.click('#loginForm button:not(.eye):not([data-forgot])'); await pg.wait_for_timeout(300)
            await pg.fill('#np1', pw); await pg.fill('#np2', pw); await pg.click('#pwForm button'); await pg.wait_for_timeout(400)
            E = lambda x: pg.evaluate('x=>__ev(x)', x); await E('$("#modal").hidden=true')
            await E(f'S.settings.cloud={{url:"{URL}",cle:"test-cle",last:0,lastOk:true,msg:""}};saveLocal();go("profil")')
            return pg, E
        A, EA = await phone('A', 'Yont2026')
        await A.click('[data-sync-create]'); await A.wait_for_timeout(1500)
        check('création de l\'espace partagé', SRV['ver'] > 0)
        check('photos du catalogue jamais envoyées', not any(k in (SRV['data'].get('photos') or {}) for k in ['castel', 'heineken', 'guinness']),
              f"{len(SRV['data'].get('photos') or {})} photo(s) sur le serveur")
        B, EB = await phone('B', 'Autre2026')
        await B.click('[data-sync-join]'); await B.wait_for_timeout(2000)
        await B.fill('#lgU', 'olivier'); await B.fill('#lgP', 'Yont2026'); await B.click('#loginForm button:not(.eye):not([data-forgot])'); await B.wait_for_timeout(600)
        await EB('$("#modal").hidden=true')
        check('le 2e appareil a rejoint et se connecte', await EB('ui.session'))
        check('le 2e appareil voit les photos du catalogue', await EB('!!S.photos.castel'))
        pid = await EA('S.products.find(p=>p.type==="boisson"&&p.stock>20).id'); price = await EA(f'priceOf(prod("{pid}"))'); s0 = await EA(f'prod("{pid}").stock')
        sell = '(pid,q)=>{ui.table="Table 2";S.orders["Table 2"]=[{pid,qty:q}];ui.pay="Espèces";ui.recv="";checkout()}'
        async def sale(E, q): await E(f'({sell})("{pid}",{q})')
        async def sync_all():
            for E in (EA, EB, EA): await E('syncNow("t")'); await asyncio.sleep(1.2)
        await sale(EA, 2); await sale(EB, 3); await sync_all()
        check('total d\'une vente = quantité × prix', await EA('S.sales[S.sales.length-1].total') in (2 * price, 3 * price))
        check('stock identique sur les deux appareils', await EA(f'prod("{pid}").stock') == await EB(f'prod("{pid}").stock') == s0 - 5,
              f"A {await EA(f'prod(\"{pid}\").stock')} B {await EB(f'prod(\"{pid}\").stock')} attendu {s0-5}")
        # hors ligne en même temps : factures et bons de cuisine en double, corrigés à la synchronisation
        OFF['A'] = OFF['B'] = True
        meal = await EA('S.products.find(p=>p.type==="repas"&&p.stock>5&&!p.from)?.id||""')
        for E in (EA, EB):
            await sale(E, 1)
            if meal: await E(f'(()=>{{ui.table="Table 3";S.orders["Table 3"]=[{{pid:"{meal}",qty:1}}];kitchenPush("Table 3",S.orders["Table 3"]);save()}})()')
        OFF['A'] = OFF['B'] = False; await sync_all(); await sync_all()
        na = json.loads(await EA('JSON.stringify(S.sales.map(s=>s.no))')); nb = json.loads(await EB('JSON.stringify(S.sales.map(s=>s.no))'))
        check('aucune facture en double', len(na) == len(set(na)) and sorted(na) == sorted(nb), f'{na[-4:]} / {nb[-4:]}')
        if meal:
            ka = json.loads(await EA('JSON.stringify(S.kitchen.map(k=>k.no))'))
            check('aucun bon de cuisine en double', len(ka) == len(set(ka)) and len(ka) >= 2, str(ka[-4:]))
        # prix « à partir de » : l'encaissement est bloqué tant que le prix n'est pas saisi
        await EA('S.products.push({id:"fx",name:"Bar braisé",cat:"Poisson braisé",type:"repas",price:2500,cost:0,stock:5,alert:0,from:true});ui.table="Table 4";S.orders["Table 4"]=[{pid:"fx",qty:1}];ui.view="vente";render();checkout()')
        await A.wait_for_timeout(300)
        check('prix « à partir de » demandé avant d\'encaisser', await EA('!$("#modal").hidden&&!!$("#pxV")') and await EA('S.sales.every(s=>!s.items.some(i=>i.pid==="fx"))'))
        await A.fill('#pxV', '4000'); await A.click('#pxForm .btn.primary'); await A.wait_for_timeout(200); await EA('ui.table="Table 4";checkout();$("#modal").hidden=true')
        check('vente au prix saisi', await EA('S.sales[S.sales.length-1].total') == 4000)
        await sync_all()
        check('le serveur garde les photos hors des données', not any(k in (SRV['data'].get('photos') or {}) for k in ['castel', 'heineken']))
        # appareil du personnel (clé propre) : il ne peut ni supprimer une facture ni en baisser le total ; ses nouvelles ventes passent
        await EB('S.settings.cloud.cle="cle-caisse";saveLocal()')
        n0 = len(SRV['data']['sales']); first = SRV['data']['sales'][0]['id']
        await EB(f'S.sales=S.sales.filter(x=>x.id!=="{first}");save()'); await sale(EB, 1)
        for E in (EB, EA, EB): await E('syncNow("t")'); await asyncio.sleep(1.2)
        ids = [x['id'] for x in SRV['data']['sales']]
        check('facture supprimée par un appareil du personnel : refusée et remise', first in ids and await EB(f'S.sales.some(x=>x.id==="{first}")'), f'{n0} → {len(ids)}')
        check('nouvelle vente du même appareil : acceptée', len(ids) == n0 + 1)
        await EB('S.audit=[];save()'); await EB('syncNow("t")'); await asyncio.sleep(1.5)
        check('audit vidé par un appareil du personnel : refusé', len(SRV['data'].get('audit') or []) > 0 and await EB('S.audit.length>0'))
        await EB('S.settings.cloud.cle="test-cle";saveLocal()')
        check('aucune erreur JavaScript', not errs, '; '.join(errs[:3]))
        # suivi des erreurs : une erreur volontaire doit arriver au serveur avec l'écran et la version
        await EA('setTimeout(()=>{throw new Error("erreur de test volontaire")},0)'); await A.wait_for_timeout(300); await EA('errFlush()'); await A.wait_for_timeout(800)
        got = [e for e in SRV.get('errors', []) if 'erreur de test volontaire' in e.get('msg', '')]
        check('les erreurs des appareils remontent au serveur', bool(got) and bool(got[0].get('ver')) and bool(got[0].get('vue')), json.dumps(got[:1], ensure_ascii=False)[:160])
        await b.close()
    print('\n' + ('TOUT EST BON' if not FAIL else f'{len(FAIL)} contrôle(s) raté(s)'))
    sys.exit(1 if FAIL else 0)

asyncio.run(main())
