#!/usr/bin/env python3
"""Actualizador horario. Fuentes: ESPN (sin clave) y API-Football (clave en el secreto API_FOOTBALL_KEY). Solo librería estándar."""
import json,os,math,re,time,difflib,unicodedata,datetime as dt,urllib.request as U,urllib.parse as P
from concurrent.futures import ThreadPoolExecutor
NOW=dt.datetime.now(dt.timezone.utc);TODAY=NOW.date();D=dt.timedelta
KEY=os.environ.get('API_FOOTBALL_KEY','').strip()
AF={'ok':bool(KEY),'err':'' if KEY else 'sin clave (falta el secreto API_FOOTBALL_KEY)','rem':None,'n':0}
LOG=[];K0=4
def log(*a):
    s=' '.join(map(str,a));print(s);LOG.append(s[:170])
def rd(f,d):
    try:return json.load(open(f,encoding='utf8'))
    except Exception:return d
def wr(f,o):json.dump(o,open(f,'w',encoding='utf8'),ensure_ascii=False,separators=(',',':'))
def get(u,h=None):
    err=None
    for _ in range(2):
        try:
            r=U.urlopen(U.Request(u,headers={'User-Agent':'Mozilla/5.0',**(h or {})}),timeout=45);return json.loads(r.read()),r.headers
        except Exception as e:err=e;time.sleep(1.5)
    raise err
def pdt(s):return dt.datetime.fromisoformat(s.replace('Z','+00:00'))
def nm(s):return re.sub(r'\b(fc|cf|sc|cd|club|deportivo|atletico|atl)\b','',re.sub(r'[^a-z0-9 ]','',unicodedata.normalize('NFKD',s.lower()).encode('ascii','ignore').decode())).strip()
def sim(a,b):return difflib.SequenceMatcher(None,nm(a),nm(b)).ratio()

# Región, slug de ESPN, nombre. Si un slug no existe, simplemente se ignora.
L='''IN uefa.champions Champions League
IN uefa.europa Europa League
IN uefa.europa.conf Conference League
IN conmebol.libertadores Copa Libertadores
IN conmebol.sudamericana Copa Sudamericana
IN concacaf.champions Concacaf Champions Cup
IN afc.champions AFC Champions League
IN fifa.world Mundial
IN fifa.friendly Amistosos de selecciones
IN fifa.worldq.uefa Eliminatorias UEFA
IN fifa.worldq.conmebol Eliminatorias CONMEBOL
IN fifa.worldq.concacaf Eliminatorias Concacaf
IN fifa.worldq.afc Eliminatorias AFC
IN fifa.worldq.caf Eliminatorias CAF
IN fifa.worldq.ofc Eliminatorias OFC
IN uefa.nations Nations League UEFA
IN concacaf.nations.league Nations League Concacaf
IN conmebol.america Copa América
IN uefa.euro Eurocopa
IN concacaf.gold Copa Oro
IN afc.asian.cup Copa Asiática
IN fifa.cwc Mundial de Clubes
EU eng.1 Premier League
EU eng.2 Championship
EU eng.fa FA Cup
EU eng.league_cup Carabao Cup
EU esp.1 LaLiga
EU esp.2 LaLiga 2
EU esp.copa_del_rey Copa del Rey
EU ita.1 Serie A
EU ita.2 Serie B
EU ita.coppa_italia Coppa Italia
EU ger.1 Bundesliga
EU ger.2 2. Bundesliga
EU ger.dfb_pokal DFB-Pokal
EU fra.1 Ligue 1
EU fra.2 Ligue 2
EU fra.coupe_de_france Copa de Francia
EU ned.1 Eredivisie
EU por.1 Primeira Liga
EU tur.1 Süper Lig
EU bel.1 Pro League Bélgica
EU sco.1 Premiership Escocia
EU rus.1 Liga Rusia
EU ukr.1 Liga Ucrania
EU sui.1 Super League Suiza
EU aut.1 Bundesliga Austria
EU gre.1 Super League Grecia
EU den.1 Superliga Dinamarca
EU swe.1 Allsvenskan
EU nor.1 Eliteserien
EU pol.1 Ekstraklasa
EU cze.1 Liga Checa
EU cro.1 Liga Croacia
EU srb.1 Liga Serbia
EU rou.1 Liga Rumania
EU bul.1 Liga Bulgaria
EU hun.1 Liga Hungría
EU isr.1 Liga Israel
EU cyp.1 Liga Chipre
EU irl.1 Liga Irlanda
EU fin.1 Veikkausliiga
AM usa.1 MLS
AM mex.1 Liga MX
AM can.1 Liga Canadiense
AM arg.1 Liga Argentina
AM bra.1 Brasileirão
AM bra.2 Brasileirão B
AM bra.copa_do_brazil Copa do Brasil
AM col.1 Liga BetPlay
AM chi.1 Liga Chile
AM uru.1 Liga Uruguay
AM par.1 Liga Paraguay
AM per.1 Liga Perú
AM ecu.1 Liga Ecuador
AM bol.1 Liga Bolivia
AM ven.1 Liga Venezuela
AM crc.1 Liga Costa Rica
AM gua.1 Liga Guatemala
AM hon.1 Liga Honduras
AM slv.1 Liga El Salvador
AM pan.1 Liga Panamá
AM jam.1 Liga Jamaica
AS ksa.1 Saudi Pro League
AS jpn.1 J1 League Japón
AS kor.1 K League Corea
AS chn.1 Superliga China
AS qat.1 Liga Qatar
AS uae.1 Liga Emiratos
AS irn.1 Liga Irán
AS ind.1 Liga India
AS tha.1 Liga Tailandia
AS idn.1 Liga Indonesia
AS mys.1 Liga Malasia
AS vie.1 Liga Vietnam
OC aus.1 A-League Australia
OC nzl.1 Liga Nueva Zelanda'''
LG=[x.split(' ',2) for x in L.split('\n')]
AFID={'eng.1':39,'esp.1':140,'ita.1':135,'ger.1':78,'fra.1':61,'ned.1':88,'por.1':94,'tur.1':203,'bel.1':144,'sco.1':179,'usa.1':253,'mex.1':262,'arg.1':128,'bra.1':71,'col.1':239,'chi.1':265,'uru.1':268,'par.1':250,'per.1':281,'ecu.1':242,'ksa.1':307,'jpn.1':98,'kor.1':292,'aus.1':188,'uefa.champions':2,'uefa.europa':3,'uefa.europa.conf':848,'conmebol.libertadores':13,'conmebol.sudamericana':11}
def season(rg,s):return (TODAY.year if TODAY.month>=7 else TODAY.year-1) if rg=='EU' or s.startswith('uefa') else TODAY.year

# ---------- ESPN ----------
def stat(c,n):
    for s in c.get('statistics',[]):
        if s.get('name')==n:
            try:return float(s.get('displayValue',s.get('value')))
            except Exception:return None
def ml(x):
    try:x=float(x);return 1+x/100 if x>0 else 1+100/-x if x<0 else None
    except Exception:return None
def mk3(o):
    try:
        g=lambda a,b:ml((o.get(a) or {}).get('moneyLine') or (((o.get('moneyline') or {}).get(b) or {}).get('close') or {}).get('odds'))
        r=[g('homeTeamOdds','home'),g('drawOdds','draw'),g('awayTeamOdds','away')];return r if all(r) else None
    except Exception:return None
def parse(e,slug):
    try:
        c=e['competitions'][0];H=[x for x in c['competitors'] if x['homeAway']=='home'][0];A=[x for x in c['competitors'] if x['homeAway']=='away'][0]
    except Exception:return None
    def side(x):
        r=next((r.get('summary') for r in x.get('records',[]) if r.get('type')=='total'),'0-0-0')
        try:w,d,l=[int(v) for v in r.split('-')]
        except Exception:w=d=l=0
        sc=int(x['score']) if str(x.get('score','')).isdigit() else 0
        sh,so,co=stat(x,'totalShots'),stat(x,'shotsOnTarget'),stat(x,'wonCorners');tg=stat(x,'totalGoals')
        if (tg is not None and int(tg)!=sc) or (sh or 0)>45 or (so or 0)>25 or (co or 0)>25:sh=so=co=None  # no parece estadística de un solo partido
        return dict(n=x['team'].get('displayName','?'),sc=sc,form=x.get('form','') or '',rec=[w,d,l],sh=sh,sot=so,co=co)
    o=next((x for x in (c.get('odds') or []) if x),None)
    return dict(id=slug.replace('.','_')+'_'+str(e['id']),slug=slug,dt=e['date'],st=c['status']['type']['state'],clk=c['status'].get('displayClock',''),v=(c.get('venue') or {}).get('fullName',''),h=side(H),a=side(A),mk3=mk3(o) if o else None)
def espn(slug,a,b):
    return get(f'https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard?dates={a:%Y%m%d}-{b:%Y%m%d}&limit=1000')[0].get('events',[])
def fetch(a,b):
    def one(x):
        try:return x[1],[p for p in (parse(e,x[1]) for e in espn(x[1],a,b)) if p]
        except Exception:return x[1],None
    with ThreadPoolExecutor(10) as ex:return dict(ex.map(one,LG))

# ---------- Historial y ratings ----------
def acc(evs):
    T={};hg=ag=wm=0
    for m in evs:
        if m['st']!='post':continue
        w=0.5**(max((NOW-pdt(m['dt'])).days,0)/30);hg+=w*m['h']['sc'];ag+=w*m['a']['sc'];wm+=w
        for me,op in((m['h'],m['a']),(m['a'],m['h'])):
            t=T.setdefault(me['n'],[0]*11);t[0]+=1;t[1]+=w;t[2]+=w*me['sc'];t[3]+=w*op['sc']
            if None not in(me['sh'],op['sh'],me['sot'],op['sot'],me['co'],op['co']):
                t[4]+=w;t[5]+=w*me['sh'];t[6]+=w*op['sh'];t[7]+=w*me['sot'];t[8]+=w*op['sot'];t[9]+=w*me['co'];t[10]+=w*op['co']
    def av(i,j,d):
        n=sum(t[i] for t in T.values());m=sum(t[j] for t in T.values());return n/m if m>0 else d
    return {'mu':{'g':av(2,1,1.3),'s':av(5,4,12),'t':av(7,4,4.2),'c':av(9,4,5),'h':hg/wm if wm else 1.45,'a':ag/wm if wm else 1.15},'T':{k:[round(x,3) for x in v] for k,v in T.items()}}
def rate(hl,team):
    t=hl['T'].get(team) if hl else None
    if not t:return None
    n,w,gf,ga,ws,sf,sa,tf,ta,cf,ca=t;mu=hl['mu'];f=lambda x,wt,m:((x+K0*m)/(wt+K0))/m
    r={'n':n,'att':f(gf,w,mu['g']),'def':f(ga,w,mu['g'])}
    if ws>0:r.update(sa=f(sf,ws,mu['s']),sd=f(sa,ws,mu['s']),ta=f(tf,ws,mu['t']),td=f(ta,ws,mu['t']),ca=f(cf,ws,mu['c']),cd=f(ca,ws,mu['c']))
    return r
def best(HL,team):
    r=None
    for hl in HL.values():
        x=rate(hl,team)
        if x and(r is None or x['n']>r['n']):r=x
    return r
def ppg(r):w,d,l=r;return(3*w+d+8.4)/(w+d+l+6)

# ---------- Modelo (Poisson + Dixon-Coles, negativa binomial para conteos) ----------
def pp(l,N=10):
    a=[math.exp(-l)]
    for k in range(1,N):a.append(a[-1]*l/k)
    return a
def grid(lh,la,rho=-.1):
    A,B=pp(lh),pp(la);g={}
    for i in range(10):
        for j in range(10):
            v=A[i]*B[j]
            if i<2 and j<2:v*=(1-lh*la*rho,1+lh*rho,1+la*rho,1-rho)[i*2+j]
            g[(i,j)]=v
    s=sum(g.values());return{k:v/s for k,v in g.items()}
def pw(g):
    ph=sum(v for(i,j),v in g.items() if i>j);pd=sum(v for(i,j),v in g.items() if i==j);return ph,pd,1-ph-pd
def fit(ph,pa,T):
    lo,hi=-T/2+.05,T/2-.05
    for _ in range(30):
        k=(lo+hi)/2;a,_,b=pw(grid(T/2+k,T/2-k))
        if a-b<ph-pa:lo=k
        else:hi=k
    k=(lo+hi)/2;return T/2+k,T/2-k
def nbc(k,mu,r):
    p=r/(r+mu);return sum(math.exp(math.lgamma(i+r)-math.lgamma(r)-math.lgamma(i+1)+r*math.log(p)+i*math.log(1-p)) for i in range(int(k)+1))
FM=lambda f:f.replace('D','E').replace('L','D').replace('W','V')

def build(m,HL,ex):
    h,a=m['h'],m['a'];hn,an=h['n'],a['n'];hl=HL.get(m['slug'])
    ra=rate(hl,hn) if hl else None;rb=rate(hl,an) if hl else None;src='liga'
    if ra and rb and ra['n']>=3 and rb['n']>=3:
        mu=hl['mu'];lh=mu['h']*ra['att']*rb['def'];la=mu['a']*rb['att']*ra['def'];n=min(ra['n'],rb['n'])
    else:
        mu=None;ra,rb=best(HL,hn),best(HL,an)
        if ra and rb and ra['n']>=3 and rb['n']>=3:src='cruce';lh=1.45*ra['att']*rb['def'];la=1.15*rb['att']*ra['def'];n=min(ra['n'],rb['n'])
        else:src='récord';s=(ppg(h['rec'])-ppg(a['rec']))*.35+.25;lh,la,n=max(.3,1.3+s/2),max(.3,1.3-s/2),0
    lh=min(max(lh,.2),4);la=min(max(la,.2),4);tot=lh+la
    p=list(pw(grid(lh,la)));o=ex.get('mk') or m.get('mk3')
    if o:q=[1/x for x in o];s=sum(q);p=[(x+y/s)/2 for x,y in zip(p,q)]
    ap=ex.get('pred')
    if ap:p=[.8*x+.2*y for x,y in zip(p,ap)];s=sum(p);p=[x/s for x in p]
    lh,la=fit(p[0],p[2],tot);g=grid(lh,la);fav=0 if p[0]>=p[2] else 1
    K=[]
    def add(i,gr,n_,pr,od=None):
        pr=min(max(pr,.02),.98);K.append({'i':i,'g':gr,'n':n_,'p':round(pr,3),'o':round(od if od else 1/pr,2),'m':1 if od else 0})
    def bl(pr,od):
        if not od:return pr
        q=[1/x for x in od];return(pr+q[0]/sum(q))/2
    add('h','Resultado','Gana '+hn,p[0],o and o[0]);add('x','Resultado','Empate',p[1],o and o[1]);add('a','Resultado','Gana '+an,p[2],o and o[2])
    add('1x','Doble oportunidad',hn+' o empate',p[0]+p[1]);add('12','Doble oportunidad',hn+' o '+an,p[0]+p[2]);add('x2','Doble oportunidad','Empate o '+an,p[1]+p[2])
    ov=lambda k:sum(v for(i,j),v in g.items() if i+j>k)
    for k in(1.5,2.5,3.5):
        od=ex.get('ou') if k==2.5 else None;po=bl(ov(k),od)
        add(f'o{k}','Goles',f'Más de {k} goles',po,od and od[0]);add(f'u{k}','Goles',f'Menos de {k} goles',1-po,od and od[1])
    by=sum(v for(i,j),v in g.items() if i>0 and j>0);bt=ex.get('bt');pb=bl(by,bt)
    add('by','Ambos anotan','Sí',pb,bt and bt[0]);add('bn','Ambos anotan','No',1-pb,bt and bt[1])
    exd=None
    if src=='liga' and 'sa' in ra and 'sa' in rb:
        sh=[mu['s']*1.08*ra['sa']*rb['sd'],mu['s']*.92*rb['sa']*ra['sd']];so=[mu['t']*1.06*ra['ta']*rb['td'],mu['t']*.94*rb['ta']*ra['td']];co=[mu['c']*1.08*ra['ca']*rb['cd'],mu['c']*.92*rb['ca']*ra['cd']]
        exd={'sh':[round(x,1) for x in sh],'sot':[round(x,1) for x in so],'co':[round(x,1) for x in co],'fav':fav}
        def ln(mv,r,gr,name,tag):
            L0=math.floor(mv)+.5
            for L in([L0-1,L0] if L0>1.5 else[L0]):
                q=1-nbc(math.floor(L),mv,r);add(f'{tag}o{L}',gr,f'{name}: más de {L}',q);add(f'{tag}u{L}',gr,f'{name}: menos de {L}',1-q)
        ln(sum(co),25,'Córners','Córners del partido','c');ln(sum(sh),30,'Remates','Remates del partido','s')
        ln(so[0],14,'Tiros al arco',hn+(' (favorito)' if fav==0 else '')+' tiros al arco','th');ln(so[1],14,'Tiros al arco',an+(' (favorito)' if fav==1 else '')+' tiros al arco','ta')
    pl=[]
    for side,team,opp in((0,hn,rb),(1,an,ra)):
        for x in sorted([x for x in ex.get('pl',[]) if sim(x[1],team)>=.75],key=lambda x:-x[2])[:2]:
            f=min(max((opp or {}).get('td',1),.8),1.25);mv=x[2]*.85*f;p1=1-math.exp(-mv)
            add(f'p{len(pl)}a','Jugadores',f'{x[0]}: 1+ tiro al arco',p1);pl.append([x[0],team,round(mv,2),round(p1,2)])
            if mv>=.75:add(f'p{len(pl)-1}b','Jugadores',f'{x[0]}: 2+ tiros al arco',1-math.exp(-mv)*(1+mv))
    cf=1+(n>=5)+(n>=9)+(1 if o else 0)+(1 if ap and ap.index(max(ap))==p.index(max(p)) else 0)-(1 if src!='liga' else 0);cf=max(1,min(5,cf))
    cx=[]
    if h['form'] or a['form']:cx.append(f"Forma reciente (últimos 5, V=victoria E=empate D=derrota): {hn} {FM(h['form']) or 's/d'} · {an} {FM(a['form']) or 's/d'}")
    cx.append(f"Récord de la temporada: {hn} {h['rec'][0]}V-{h['rec'][1]}E-{h['rec'][2]}D · {an} {a['rec'][0]}V-{a['rec'][1]}E-{a['rec'][2]}D")
    if ra and rb:cx.append(f"Ataque/defensa relativos al promedio (1.00 = promedio; defensa baja = mejor): {hn} {ra['att']:.2f}/{ra['def']:.2f} · {an} {rb['att']:.2f}/{rb['def']:.2f} (muestra: {ra['n']} y {rb['n']} partidos, más peso a los recientes)")
    cx.append(f'Goles esperados del modelo: {lh:.2f} – {la:.2f}')
    if o:cx.append(f"Cuotas de mercado 1X2: {o[0]:.2f} / {o[1]:.2f} / {o[2]:.2f} (se mezclan 50% con el modelo)")
    if ex.get('adv'):cx.append('API-Football, consejo: '+ex['adv'])
    if ex.get('h2h'):cx.append(ex['h2h'])
    if src!='liga':cx.append('Aviso: equipos de ligas distintas o poca muestra; confianza reducida.' if src=='cruce' else 'Aviso: casi sin historial de goles; se usa el récord de temporada. Confianza baja.')
    if not exd:cx.append('Sin estadísticas suficientes de remates/córners para esta competición.')
    sc=sorted(g.items(),key=lambda x:-x[1])[:3]
    best_k,bs=None,0
    for k in K:
        if k['g'] in('Resultado','Doble oportunidad','Goles','Ambos anotan') and .6<=k['p']<=.85 and k['o']>=1.2:
            s=k['p']*(.5+.1*cf)+(max(0,k['p']*k['o']-1)*.5 if k['m'] else 0)
            if s>bs:best_k,bs=k['i'],s
    return {'sc':bs if cf>=2 else 0,'out':{'fh':FM(h['form']),'fa':FM(a['form']),'p':[round(x,3) for x in p],'k':K,'s3':[[f'{i}-{j}',round(v,3)] for(i,j),v in sc],'ex':exd,'pl':pl,'cx':cx,'cf':cf,'pk':best_k}}

# ---------- API-Football (opcional, con presupuesto) ----------
def af(path,**q):
    if not AF['ok']:return None
    try:j,h=get('https://v3.football.api-sports.io/'+path+'?'+P.urlencode(q),{'x-apisports-key':KEY})
    except Exception as e:AF['err']=str(e)[:120];AF['ok']=False;return None
    AF['n']+=1;AF['rem']=h.get('x-ratelimit-requests-remaining')
    if j.get('errors'):AF['err']=json.dumps(j['errors'],ensure_ascii=False)[:170];AF['ok']=False;return None
    try:
        if AF['rem'] is not None and int(AF['rem'])<8:AF['ok']=False;AF['err']='cuota diaria casi agotada'
    except Exception:pass
    return j.get('response')
def find_fx(m,fxs):
    b=None
    for f in fxs:
        try:s=min(sim(m['h']['n'],f['teams']['home']['name']),sim(m['a']['n'],f['teams']['away']['name']))
        except Exception:continue
        if s>=.72 and(not b or s>b[0]):b=(s,f)
    return b and b[1]
def parse_odds(r):
    out={}
    try:bms=r[0]['bookmakers']
    except Exception:return out
    bm=next((b for b in bms if 'bet365' in b['name'].lower()),None) or(bms[0] if bms else None)
    for bet in(bm or{}).get('bets',[]):
        n=bet['name'].lower();v={x['value']:float(x['odd']) for x in bet['values']}
        if n=='match winner' and all(k in v for k in('Home','Draw','Away')):out['mk']=[v['Home'],v['Draw'],v['Away']]
        elif n=='goals over/under' and 'Over 2.5' in v and 'Under 2.5' in v:out['ou']=[v['Over 2.5'],v['Under 2.5']]
        elif n=='both teams score' and 'Yes' in v and 'No' in v:out['bt']=[v['Yes'],v['No']]
    return out
def parse_pred(r,m):
    try:
        r=r[0];pc=r['predictions']['percent'];out={'pred':[float(pc[k].strip('%'))/100 for k in('home','draw','away')],'adv':r['predictions'].get('advice','')}
        w=[0,0,0]
        for f in r.get('h2h') or[]:
            a,b=f['goals']['home'],f['goals']['away']
            if a is None or b is None:continue
            hm=sim(f['teams']['home']['name'],m['h']['n'])>=.7
            if a==b:w[1]+=1
            elif(a>b)==hm:w[0]+=1
            else:w[2]+=1
        if sum(w):out['h2h']=f"Historial directo (últimos {sum(w)}): {m['h']['n']} {w[0]} · empates {w[1]} · {m['a']['n']} {w[2]}"
        return out
    except Exception:return{'pred':None}
def players(lid,sea,st):
    k=f'{lid}:{TODAY}'
    if k in st['pl']:return st['pl'][k]
    r=af('players/topscorers',league=lid,season=sea);Lp=[]
    for x in r or[]:
        try:
            s=x['statistics'][0];mn=s['games']['minutes'] or 0;on=s['shots']['on'] or 0
            if mn>=270:Lp.append([x['player']['name'],s['team']['name'],round(on/mn*90,2)])
        except Exception:pass
    if r is not None:st['pl'][k]=Lp
    return Lp
def enrich(cand,st,HL,B):
    fx={}
    for m in cand:
        if not AF['ok']:break
        c=st['af'].setdefault(m['id'],{});d=str(pdt(m['dt']).date())
        if 'fx' not in c:
            if d not in fx:fx[d]=af('fixtures',date=d) or[]
            f=find_fx(m,fx[d])
            if not f:c['fx']=0;continue
            c['fx']=f['fixture']['id'];c['lid']=f['league']['id']
        if not c['fx']:continue
        if 'pred' not in c and AF['ok']:
            r=af('predictions',fixture=c['fx']);c.update(parse_pred(r,m) if r else{'pred':None})
        if AF['ok'] and(not c.get('ots') or(NOW-pdt(c['ots'])).total_seconds()>6*3600):
            r=af('odds',fixture=c['fx'])
            if r is not None:c.update(parse_odds(r));c['ots']=NOW.isoformat(timespec='minutes')
        rg=next((x[0] for x in LG if x[1]==m['slug']),'IN');lid=AFID.get(m['slug']) or c.get('lid');pl=[]
        if AF['ok'] and lid:pl=players(lid,season(rg,m['slug']),st)
        elif lid and f'{lid}:{TODAY}' in st['pl']:pl=st['pl'][f'{lid}:{TODAY}']
        b=build(m,HL,{'mk':c.get('mk'),'ou':c.get('ou'),'bt':c.get('bt'),'pred':c.get('pred'),'adv':c.get('adv'),'h2h':c.get('h2h'),'pl':pl})
        if b:B[m['id']]=b

def main():
    st=rd('state.json',{});[st.setdefault(k,{}) for k in('af','pl')]
    hist=rd('hist.json',{})
    if not hist.get('ts') or(NOW-pdt(hist['ts'])).total_seconds()>20*3600:
        Hh=fetch(TODAY-D(100),TODAY-D(1));hist={'ts':NOW.isoformat(timespec='minutes'),'L':{s:acc(v) for s,v in Hh.items() if v}}
        log('Historial reconstruido:',len(hist['L']),'competiciones con resultados');wr('hist.json',hist)
    HL=hist.get('L',{});Ue=fetch(TODAY-D(1),TODAY+D(4))
    bad=[s for s,v in Ue.items() if v is None];log('ESPN:',len(Ue)-len(bad),'competiciones respondieron,',len(bad),'sin respuesta')
    ms=[]
    for r,s,n in LG:
        for m in Ue.get(s) or[]:m['rg'],m['lg']=r,n;ms.append(m)
    B={}
    for m in ms:
        if m['st']!='post':
            try:
                b=build(m,HL,{})
                if b:B[m['id']]=b
            except Exception as e:log('error modelo',m['h']['n'],e)
    soon=lambda m:m['st']=='pre' and 0<(pdt(m['dt'])-NOW).total_seconds()<36*3600
    cand=sorted([m for m in ms if m['id'] in B and soon(m)],key=lambda m:-B[m['id']]['sc'])[:8]
    if KEY:
        try:enrich(cand,st,HL,B)
        except Exception as e:log('error API-Football',e)
    log('API-Football:', 'OK' if AF['ok'] else 'no disponible: '+AF['err'],'| llamadas',AF['n'],'| restantes hoy',AF['rem'])
    picks=[m['id'] for m in sorted([m for m in ms if m['id'] in B and B[m['id']]['out']['pk'] and m['st']=='pre' and 0<(pdt(m['dt'])-NOW).total_seconds()<48*3600],key=lambda m:-B[m['id']]['sc'])[:12]]
    out=[]
    for m in ms:
        e={'id':m['id'],'lg':m['lg'],'rg':m['rg'],'dt':m['dt'],'st':m['st'],'clk':m['clk'],'h':m['h']['n'],'a':m['a']['n'],'hg':m['h']['sc'],'ag':m['a']['sc'],'v':m['v']}
        if m['id'] in B:e.update(B[m['id']]['out'])
        out.append(e)
    ids={m['id'] for m in ms};st['af']={k:v for k,v in st['af'].items() if k in ids};st['pl']={k:v for k,v in st['pl'].items() if k.endswith(str(TODAY))}
    wr('state.json',st)
    wr('data.json',{'updated':NOW.isoformat(timespec='minutes'),'meta':{'espn_ok':len(Ue)-len(bad),'espn_fail':len(bad),'af':{'ok':AF['ok'],'err':AF['err'],'rem':AF['rem'],'n':AF['n']},'log':LOG[-10:]},'picks':picks,'matches':out})
    log('Listo:',len(out),'partidos,',len(picks),'picks')
if __name__=='__main__':main()
