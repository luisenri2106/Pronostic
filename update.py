#!/usr/bin/env python3
"""Actualizador horario. Fuente única: API-Football (clave en el secreto API_FOOTBALL_KEY).
ESPN se retiró: bloquea las peticiones desde los servidores de GitHub (403 confirmado). Solo librería estándar."""
import json,os,math,re,time,difflib,unicodedata,datetime as dt,urllib.request as U,urllib.parse as P
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
    err=None;hdr={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36','Accept':'application/json',**(h or {})}
    for _ in range(2):
        try:
            r=U.urlopen(U.Request(u,headers=hdr),timeout=20);return json.loads(r.read()),r.headers
        except Exception as e:err=e;time.sleep(1.2)
    raise err
def pdt(s):return dt.datetime.fromisoformat(s.replace('Z','+00:00'))
def nm(s):return re.sub(r'\b(fc|cf|sc|cd|club|deportivo|atletico|atl)\b','',re.sub(r'[^a-z0-9 ]','',unicodedata.normalize('NFKD',s.lower()).encode('ascii','ignore').decode())).strip()
def sim(a,b):return difflib.SequenceMatcher(None,nm(a),nm(b)).ratio()

# Competiciones cubiertas: id de API-Football -> (nombre, región). Lista curada para caber en 100 peticiones/día.
LEAGUES={2:('Champions League','IN'),3:('Europa League','IN'),848:('Conference League','IN'),
 13:('Copa Libertadores','IN'),11:('Copa Sudamericana','IN'),1:('Mundial','IN'),
 5:('Nations League UEFA','IN'),9:('Copa América','IN'),4:('Eurocopa','IN'),
 32:('Eliminatorias UEFA','IN'),34:('Eliminatorias CONMEBOL','IN'),10:('Amistosos de selecciones','IN'),
 39:('Premier League','EU'),140:('LaLiga','EU'),135:('Serie A','EU'),78:('Bundesliga','EU'),
 61:('Ligue 1','EU'),88:('Eredivisie','EU'),94:('Primeira Liga','EU'),203:('Süper Lig','EU'),144:('Pro League Bélgica','EU'),
 253:('MLS','AM'),262:('Liga MX','AM'),71:('Brasileirão','AM'),128:('Liga Argentina','AM'),
 239:('Liga BetPlay','AM'),265:('Liga Chile','AM'),268:('Liga Uruguay','AM'),281:('Liga Perú','AM'),
 307:('Saudi Pro League','AS'),98:('J1 League','AS'),292:('K League 1','AS'),188:('A-League','OC')}
EUY={39,140,135,78,61,88,94,203,144,2,3,848}  # temporada jul-jun; el resto se trata como año calendario
def seasonf(lid):return (TODAY.year if TODAY.month>=7 else TODAY.year-1) if lid in EUY else TODAY.year
LGAVG={'sh':12.5,'sot':4.3,'co':5.0}  # promedios de liga (estimación) para remates/tiros al arco/córners

# ---------- API-Football ----------
_last=[0.0]
def af(path,**q):
    if not AF['ok']:return None
    wait=6.5-(time.time()-_last[0])
    if wait>0:time.sleep(wait)
    _last[0]=time.time()
    try:j,h=get('https://v3.football.api-sports.io/'+path+'?'+P.urlencode(q),{'x-apisports-key':KEY})
    except Exception as e:
        AF['err']=f'{type(e).__name__} {str(e)[:130]}';AF['fail']=AF.get('fail',0)+1
        if AF['fail']>=4:AF['ok']=False;AF['err']+=' (4 fallos seguidos: probable bloqueo, se detiene por hoy)'
        return None
    AF['fail']=0;AF['n']+=1;AF['rem']=h.get('x-ratelimit-requests-remaining')
    if isinstance(j,dict) and j.get('errors'):
        er=j['errors'];AF['err']=('; '.join(map(str,er)) if isinstance(er,list) else json.dumps(er,ensure_ascii=False))[:170]
        if er:return None
    try:
        if AF['rem'] is not None and int(AF['rem'])<10:AF['ok']=False;AF['err']='cuota diaria casi agotada'
    except Exception:pass
    return (j or {}).get('response')
def parse_af(fx):
    try:
        f=fx['fixture'];t=fx['teams'];g=fx['goals'];sc=(f['status']['short'] or '').upper()
        st='post' if sc in('FT','AET','PEN') else 'pre' if sc in('NS','TBD','PST') else 'in'
        return dict(fid=f['id'],dt=f['date'],st=st,clk=f['status'].get('elapsed'),v=(f.get('venue') or {}).get('name','') or '',
                    h=dict(n=t['home']['name'],sc=g['home'] if g['home'] is not None else 0),
                    a=dict(n=t['away']['name'],sc=g['away'] if g['away'] is not None else 0))
    except Exception:return None
def discover(lid):
    err=[]
    r=af('fixtures',league=lid,season=seasonf(lid),**{'from':str(TODAY-D(27)),'to':str(TODAY+D(6))})
    if r is None:
        if AF['err']:err.append(f'liga {lid}: {AF["err"]}')
        return None,err
    out=[]
    for fx in r:
        p=parse_af(fx)
        if p:out.append(p)
    return out,err
def live_poll():
    r=af('fixtures',live='all')
    if r is None:return None,([f'live: {AF["err"]}'] if AF['err'] else [])
    return [p for p in (parse_af(fx) for fx in r) if p],[]

# ---------- Historial y ratings (a partir de los mismos partidos ya jugados que trae discover()) ----------
def acc(evs):
    T={}
    for m in evs:
        if m['st']!='post':continue
        w=0.5**(max((NOW-pdt(m['dt'])).days,0)/30)
        for me,op in((m['h'],m['a']),(m['a'],m['h'])):
            t=T.setdefault(me['n'],{'n':0,'w':0.0,'gf':0.0,'ga':0.0,'wl':0,'dl':0,'ll':0,'form':[]})
            t['n']+=1;t['w']+=w;t['gf']+=w*me['sc'];t['ga']+=w*op['sc']
            r='W' if me['sc']>op['sc'] else 'D' if me['sc']==op['sc'] else 'L'
            t['wl' if r=='W' else 'dl' if r=='D' else 'll']+=1;t['form'].append((pdt(m['dt']),r))
    hg=sum(w*m['h']['sc'] for w,m in ((0.5**(max((NOW-pdt(m['dt'])).days,0)/30),m) for m in evs if m['st']=='post'))
    wm=sum(0.5**(max((NOW-pdt(m['dt'])).days,0)/30) for m in evs if m['st']=='post')
    ag=sum(w*m['a']['sc'] for w,m in ((0.5**(max((NOW-pdt(m['dt'])).days,0)/30),m) for m in evs if m['st']=='post'))
    for t in T.values():t['form'].sort(key=lambda x:x[0]);t['form']=''.join(r for _,r in t['form'][-5:])
    n=sum(t['gf'] for t in T.values());mden=sum(t['w'] for t in T.values())
    return {'mu':{'g':n/mden if mden else 1.3,'h':hg/wm if wm else 1.45,'a':ag/wm if wm else 1.15},
            'T':{k:{'n':v['n'],'w':v['w'],'gf':round(v['gf'],3),'ga':round(v['ga'],3),'rec':[v['wl'],v['dl'],v['ll']],'form':v['form']} for k,v in T.items()}}
def rate(hl,team):
    t=hl['T'].get(team) if hl else None
    if not t:return None
    mu=hl['mu'];f=lambda x,wt,m:((x+K0*m)/(wt+K0))/m
    return {'n':t['n'],'att':f(t['gf'],t['w'],mu['g']),'def':f(t['ga'],t['w'],mu['g']),'rec':t['rec'],'form':t['form']}
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
    h,a=m['h'],m['a'];hn,an=h['n'],a['n'];hl=HL.get(m['lg_id'])
    ra=rate(hl,hn) if hl else None;rb=rate(hl,an) if hl else None;src='liga'
    if ra and rb and ra['n']>=3 and rb['n']>=3:
        mu=hl['mu'];lh=mu['h']*ra['att']*rb['def'];la=mu['a']*rb['att']*ra['def'];n=min(ra['n'],rb['n'])
    else:
        ra2,rb2=best(HL,hn),best(HL,an)
        if ra2 and rb2 and ra2['n']>=3 and rb2['n']>=3:
            src='cruce';ra,rb=ra2,rb2;lh=1.45*ra['att']*rb['def'];la=1.15*rb['att']*ra['def'];n=min(ra['n'],rb['n'])
        else:
            src='récord';ra,rb=ra2,rb2;rh=ra['rec'] if ra else[0,0,0];rw=rb['rec'] if rb else[0,0,0]
            s=(ppg(rh)-ppg(rw))*.35+.28;lh,la,n=max(.3,1.3+s/2),max(.3,1.3-s/2),0
    lh=min(max(lh,.2),4);la=min(max(la,.2),4);tot=lh+la
    p=list(pw(grid(lh,la)));o=ex.get('mk')
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
    fnm,dnm=(hn,an) if fav==0 else(an,hn)
    for line in(0.5,1.5,2.5):
        win=sum(v for(i,j),v in g.items() if((i-j) if fav==0 else(j-i))-line>0)
        add(f'ahf{line}','Hándicap asiático',f'{fnm} -{line} (hándicap)',win);add(f'ahd{line}','Hándicap asiático',f'{dnm} +{line} (hándicap)',1-win)
    exd=None
    if ra and rb:
        hb,ab=1.08,.92
        sh=[LGAVG['sh']*hb*ra['att']*rb['def'],LGAVG['sh']*ab*rb['att']*ra['def']]
        so=[LGAVG['sot']*hb*ra['att']*rb['def'],LGAVG['sot']*ab*rb['att']*ra['def']]
        co=[LGAVG['co']*hb*ra['att']*rb['def'],LGAVG['co']*ab*rb['att']*ra['def']]
        exd={'sh':[round(x,1) for x in sh],'sot':[round(x,1) for x in so],'co':[round(x,1) for x in co],'fav':fav,'est':True}
        def ln(mv,r,gr,name,tag):
            L0=math.floor(mv)+.5
            for L in([L0-1,L0] if L0>1.5 else[L0]):
                q=1-nbc(math.floor(L),mv,r);add(f'{tag}o{L}',gr,f'{name}: más de {L}',q);add(f'{tag}u{L}',gr,f'{name}: menos de {L}',1-q)
        ln(sum(co),25,'Córners','Córners del partido','c');ln(sum(sh),30,'Remates','Remates del partido','s')
        ln(so[0],14,'Tiros al arco',hn+(' (favorito)' if fav==0 else '')+' tiros al arco','th');ln(so[1],14,'Tiros al arco',an+(' (favorito)' if fav==1 else '')+' tiros al arco','ta')
    pl=[]
    for side,team,opp in((0,hn,rb),(1,an,ra)):
        for x in sorted([x for x in ex.get('pl',[]) if sim(x[1],team)>=.75],key=lambda x:-x[2])[:2]:
            f=min(max((opp or{}).get('def',1),.8),1.25);mv=x[2]*.85*f;p1=1-math.exp(-mv)
            add(f'p{len(pl)}a','Jugadores',f'{x[0]}: 1+ tiro al arco',p1);pl.append([x[0],team,round(mv,2),round(p1,2)])
            if mv>=.75:add(f'p{len(pl)-1}b','Jugadores',f'{x[0]}: 2+ tiros al arco',1-math.exp(-mv)*(1+mv))
    cf=1+(n>=5)+(n>=9)+(1 if o else 0)+(1 if ap and ap.index(max(ap))==p.index(max(p)) else 0)-(1 if src!='liga' else 0);cf=max(1,min(5,cf))
    cx=[]
    fh=ra['form'] if ra else '';fa=rb['form'] if rb else ''
    if fh or fa:cx.append(f"Forma reciente (últimos 5, V/E/D): {hn} {FM(fh) or 's/d'} · {an} {FM(fa) or 's/d'}")
    rh2=ra['rec'] if ra else None;rw2=rb['rec'] if rb else None
    if rh2 or rw2:
        rs=lambda r:f"{r[0]}V-{r[1]}E-{r[2]}D" if r else 's/d'
        cx.append(f"Récord reciente (~1 mes): {hn} {rs(rh2)} · {an} {rs(rw2)}")
    if ra and rb:cx.append(f"Ataque/defensa relativos al promedio (1.00=promedio; defensa baja=mejor): {hn} {ra['att']:.2f}/{ra['def']:.2f} · {an} {rb['att']:.2f}/{rb['def']:.2f} (muestra: {ra['n']} y {rb['n']} partidos)")
    cx.append(f'Goles esperados del modelo: {lh:.2f} – {la:.2f}')
    if o:cx.append(f"Cuotas de mercado 1X2: {o[0]:.2f} / {o[1]:.2f} / {o[2]:.2f} (se mezclan con el modelo)")
    cx.append(f"Hándicap asiático: {fnm} tiene que ganar por más goles que la línea para cubrirla; con líneas de medio gol no hay empate posible. Cuotas justas del modelo, no de una casa.")
    if ex.get('adv'):cx.append('API-Football, consejo: '+ex['adv'])
    if ex.get('h2h'):cx.append(ex['h2h'])
    if src!='liga':cx.append('Aviso: poco historial cruzado; confianza reducida.' if src=='cruce' else 'Aviso: sin historial de goles suficiente; estimación a partir del récord reciente. Confianza baja.')
    if exd:cx.append('Remates/córners/tiros al arco: estimados a partir de la fuerza de ataque y defensa de cada equipo (no de un conteo histórico real, que la clave gratis no puede consultar sin gastar toda la cuota).')
    sc=sorted(g.items(),key=lambda x:-x[1])[:3]
    best_k,bs=None,0
    for k in K:
        if k['g'] in('Resultado','Doble oportunidad','Goles','Ambos anotan') and .6<=k['p']<=.85 and k['o']>=1.2:
            s=k['p']*(.5+.1*cf)+(max(0,k['p']*k['o']-1)*.5 if k['m'] else 0)
            if s>bs:best_k,bs=k['i'],s
    return {'sc':bs if cf>=2 else 0,'out':{'fh':FM(fh),'fa':FM(fa),'p':[round(x,3) for x in p],'k':K,'s3':[[f'{i}-{j}',round(v,3)] for(i,j),v in sc],'ex':exd,'pl':pl,'cx':cx,'cf':cf,'pk':best_k}}

# ---------- Enriquecimiento (predicciones, cuotas, goleadores) ----------
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
        r=r[0];pc=r['predictions']['percent'];out={'pred':[float(pc[k].strip('%'))/100 for k in('home','draw','away')],'adv':r['predictions'].get('advice','') or ''}
        w=[0,0,0]
        for f in r.get('h2h') or[]:
            a,b=f['goals']['home'],f['goals']['away']
            if a is None or b is None:continue
            hm=sim(f['teams']['home']['name'],m['h']['n'])>=.7
            w[1 if a==b else(0 if(a>b)==hm else 2)]+=1
        if sum(w):out['h2h']=f"Historial directo (últimos {sum(w)}): {m['h']['n']} {w[0]} · empates {w[1]} · {m['a']['n']} {w[2]}"
        return out
    except Exception:return{'pred':None}
def get_players(lid,st):
    key=f'{lid}:{TODAY}'
    if key in st['pl']:return st['pl'][key]
    r=af('players/topscorers',league=lid,season=seasonf(lid));out=[]
    for x in r or[]:
        try:
            s=x['statistics'][0];mn=s['games']['minutes'] or 0;on=(s.get('shots') or{}).get('on') or 0
            if mn>=270:out.append([x['player']['name'],s['team']['name'],round(on/mn*90,2)])
        except Exception:pass
    if r is not None:st['pl'][key]=out
    return out
def maybe_enrich(cand,M,st):
    n=0
    for fid in cand:
        if not AF['ok'] or n>=6:break
        key=str(fid);e=st['enr'].get(key,{})
        if e.get('ts') and(NOW-pdt(e['ts'])).total_seconds()<10*3600:continue
        pr=af('predictions',fixture=fid);ex={}
        if pr:ex.update(parse_pred(pr,M[fid]))
        od=af('odds',fixture=fid)
        if od:ex.update(parse_odds(od))
        if ex:st['enr'][key]={'ts':NOW.isoformat(timespec='minutes'),'ex':ex};n+=1

def main():
    st=rd('state.json',{});[st.setdefault(k,{}) for k in('enr','pl')]
    hist=rd('hist.json',{});HL=hist.get('L',{})
    M={}
    for e in (rd('data.json',{}) or{}).get('matches',[]):
        fid=e.get('fid')
        if fid:M[fid]=e
    stale=not hist.get('ts') or(NOW-pdt(hist['ts'])).total_seconds()>20*3600
    errs=[]
    if stale:
        newHL={};ok_n=0
        for lid in LEAGUES:
            evs,err=discover(lid);errs+=err
            if evs is not None:
                ok_n+=1;newHL[lid]=acc(evs)
                for fx in evs:M[fx['fid']]={**fx,'lg':LEAGUES[lid][0],'rg':LEAGUES[lid][1],'lg_id':lid}
            if not AF['ok']:break
        log('Descubrimiento:',ok_n,'/',len(LEAGUES),'competiciones con datos')
        if newHL:hist={'ts':NOW.isoformat(timespec='minutes'),'L':newHL};wr('hist.json',hist);HL=newHL
    if errs:log('Ejemplo de error (descubrimiento):',' | '.join(errs[:5]))
    live,lerr=live_poll()
    if live is not None:
        for fx in live:
            old=M.get(fx['fid'])
            if old and 'lg_id' in old:M[fx['fid']]={**old,**fx,'lg':old['lg'],'rg':old['rg'],'lg_id':old['lg_id']}
        log('En vivo ahora (global):',len(live),'partidos')
    elif lerr:log('Ejemplo de error (en vivo):',' | '.join(lerr))
    B={}
    for fid,m in M.items():
        if m.get('st')=='post' or 'lg_id' not in m:continue
        try:
            b=build(m,HL,{})
            if b:B[fid]=b
        except Exception as e:log('error modelo',m.get('h',{}).get('n','?'),type(e).__name__,str(e)[:100])
    soon=lambda m:m.get('st')=='pre' and m.get('dt') and 0<(pdt(m['dt'])-NOW).total_seconds()<48*3600
    cand=sorted([fid for fid in B if soon(M[fid])],key=lambda fid:-B[fid]['sc'])[:10]
    if KEY and AF['ok']:maybe_enrich(cand,M,st)
    for fid in cand:
        e=st['enr'].get(str(fid))
        if not e:continue
        m=M[fid];ex=dict(e['ex']);ex['pl']=get_players(m['lg_id'],st) if AF['ok'] else st['pl'].get(f"{m['lg_id']}:{TODAY}",[])
        try:
            b=build(m,HL,ex)
            if b:B[fid]=b
        except Exception as ex2:log('error enriquecido',m.get('h',{}).get('n','?'),type(ex2).__name__,str(ex2)[:100])
    log('API-Football:','OK' if AF['ok'] else 'no disponible: '+AF['err'],'| llamadas',AF['n'],'| restantes hoy',AF['rem'])
    picks=[fid for fid in sorted([fid for fid in cand if B.get(fid) and B[fid]['out'].get('pk')],key=lambda fid:-B[fid]['sc'])][:10]
    out=[]
    for fid,m in M.items():
        if 'lg_id' not in m:continue
        e={'id':f'af_{fid}','fid':fid,'lg':m['lg'],'rg':m['rg'],'dt':m['dt'],'st':m['st'],'clk':m.get('clk'),'h':m['h']['n'],'a':m['a']['n'],'hg':m['h']['sc'],'ag':m['a']['sc'],'v':m.get('v','')}
        if fid in B:e.update(B[fid]['out'])
        out.append(e)
    st['pl']={k:v for k,v in st['pl'].items() if k.endswith(str(TODAY))}
    st['enr']={k:v for k,v in st['enr'].items() if int(k) in M}
    wr('state.json',st)
    wr('data.json',{'updated':NOW.isoformat(timespec='minutes'),'meta':{'competiciones':len(LEAGUES),'con_datos':len(HL),'af':{'ok':AF['ok'],'err':AF['err'],'rem':AF['rem'],'n':AF['n']},'log':LOG[-12:]},'picks':[f'af_{i}' for i in picks],'matches':out})
    log('Listo:',len(out),'partidos,',len(picks),'picks')
if __name__=='__main__':main()
