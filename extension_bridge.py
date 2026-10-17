"""Optional external companion transport. No provider implementation lives here."""
import json
import threading
import time
from urllib.parse import urlsplit, quote
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
from urllib.error import URLError, HTTPError
from flask import Blueprint, request, jsonify, render_template, Response, abort

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):return None

def register_extension(app, *, url, token, authenticated, context_for, import_metadata, contexts_for=lambda: [], import_batch=None, library_for=lambda: [], start_worker=True):
    parsed=urlsplit(url)
    enabled=bool(url and token)
    if enabled and (parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or len(token)<24):
        raise ValueError('Configuration du module externe invalide')
    base=url.rstrip('/')
    opener=build_opener(ProxyHandler({}),NoRedirect())
    bp=Blueprint('extension',__name__)
    def forward(path,body=None,query='',timeout=30):
        if not enabled:abort(404)
        if '..' in path.split('/') or not path.startswith(('ui/','assets/','v1/')):abort(404)
        target=base+'/'+quote(path,safe='/')+('?' + query if query else '')
        req=Request(target,data=body,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json' if body is not None else 'application/octet-stream'})
        try:
            with opener.open(req,timeout=timeout) as response:
                content=response.read(6*1024*1024+1)
                if len(content)>6*1024*1024:raise ValueError('Réponse du module trop volumineuse')
                return content,response.status,response.headers.get('Content-Type','application/json')
        except HTTPError as exc:
            if exc.code>=500:return b'{"ok":false,"error":"Module temporairement indisponible"}',502,'application/json'
            # A configured service may return a validation error; never follow its redirect.
            if 300<=exc.code<400:return b'{"ok":false,"error":"Redirection du module refusee"}',502,'application/json'
            return exc.read(65536),exc.code,'application/json'
        except (URLError,TimeoutError,OSError,ValueError):
            return b'{"ok":false,"error":"Module externe inaccessible"}',502,'application/json'
    def guard():
        if not enabled:abort(404)
        if not authenticated():return jsonify(ok=False,error='authenticated_admin_required'),401
    @bp.route('/extensions')
    def page():
        failure=guard()
        if failure:return failure
        return render_template('extensions.html', extension_ui={'discover':'ui/discover/','library':'ui/library/','home':'ui/discover/?home=1'}.get(request.args.get('view'),'ui/'))
    @bp.route('/api/extension/<path:path>',methods=['GET','POST'])
    def proxy(path):
        failure=guard()
        if failure:return failure
        if request.content_length and request.content_length>8*1024*1024:return jsonify(ok=False,error='Requête trop volumineuse'),413
        if request.method=='POST' and not request.is_json:return jsonify(ok=False,error='JSON requis'),415
        payload=request.get_data() if request.method=='POST' else None
        content,status,mime=forward(path,payload,request.query_string.decode('ascii','replace'))
        response=Response(content,status=status,content_type=mime)
        response.headers['Cache-Control']='no-store'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'self'; base-uri 'self'"
        return response
    @bp.get('/api/extensions/contexts')
    def contexts():
        failure=guard()
        if failure:return failure
        response=jsonify(ok=True,videos=contexts_for());response.headers['Cache-Control']='no-store'
        return response
    @bp.get('/api/extensions/library')
    def library():
        failure=guard()
        if failure:return failure
        response=jsonify(ok=True,videos=library_for())
        response.headers['Cache-Control']='no-store'
        return response
    @bp.post('/api/extensions/metadata/<vid>')
    def metadata(vid):
        failure=guard()
        if failure:return failure
        try:context=context_for(vid)
        except (ValueError,OSError):return jsonify(ok=False,error='Vidéo indisponible'),404
        content,status,_=forward('v1/video/lookup',json.dumps(context).encode())
        if status!=200:return Response(content,status=status,content_type='application/json')
        try:
            result=json.loads(content).get('result',{})
            import_metadata(vid,context,result)
        except (ValueError,TypeError):return jsonify(ok=False,error='Métadonnées du module invalides'),502
        return jsonify(ok=True)
    @bp.post('/api/extensions/batch')
    def batch():
        failure=guard()
        if failure:return failure
        content,status,mime=forward('v1/batch',json.dumps({'videos':contexts_for()}).encode())
        return Response(content,status=status,content_type=mime)
    @bp.post('/api/extensions/import')
    def import_all():
        failure=guard()
        if failure:return failure
        content,status,_=forward('v1/export')
        if status!=200:return Response(content,status=status,content_type='application/json')
        try:
            records=json.loads(content).get('videos',[])
            count=0
            if import_batch is not None:
                import_batch(records)
                return jsonify(ok=True,imported=len(records))
            for record in records:
                try:context=context_for(record['id'])
                except (ValueError,OSError):continue
                import_metadata(record['id'],context,record['result']);count+=1
        except (ValueError,TypeError,KeyError):return jsonify(ok=False,error='Métadonnées invalides'),502
        return jsonify(ok=True,imported=count)
    def import_results():
        content,status,_=forward('v1/export')
        if status!=200:return
        records=json.loads(content).get('videos',[])
        if not isinstance(records,list) or len(records)>10000:return
        if import_batch is not None:
            import_batch(records)
            return
        for record in records:
            try:
                context=context_for(record['id'])
                import_metadata(record['id'],context,record['result'])
            except (ValueError,OSError,TypeError,KeyError):continue
    def synchronize():
        # Import completed work even when the browser has been closed.
        time.sleep(3)
        while True:
            try:import_results()
            except Exception:app.logger.warning('Synchronisation du compagnon temporairement indisponible')
            time.sleep(30)
    if enabled and start_worker:
        threading.Thread(target=synchronize,daemon=True,name='external-companion-import').start()
    def recommendations(vid, minimum=1):
        if not enabled or not authenticated():return None
        try:
            payload={'videos':library_for(),'focus':vid,'count':20,'unseen_only':False,'min_common_tags':minimum}
            content,status,_=forward('v1/collections',json.dumps(payload).encode(),timeout=3)
            if status != 200:return None
            data=json.loads(content)
            if data.get('ok') is not True:return None
            group=next((g for g in data.get('groups',[]) if g.get('id')=='similar'),None)
            if not group or not isinstance(group.get('videos'),list):return None
            if any(not isinstance(v,dict) or not isinstance(v.get('id'),str) for v in group['videos']):return None
            opinions=data.get('opinions',{})
            return {'videos':group['videos'],'opinions':opinions if isinstance(opinions,dict) else {}}
        except (ValueError,TypeError,AttributeError):return None
    app.extensions['minivid_recommendations']=recommendations
    app.register_blueprint(bp)
    app.context_processor(lambda:{'extension_enabled':enabled})


class SharedStateUnavailable(RuntimeError):pass

class SharedStateSnapshot(dict):
    def __init__(self,state):
        super().__init__(json.loads(json.dumps(state)))
        self.baseline=json.loads(json.dumps(state))

def state_changes(before,after,path=None):
    path=path or [];changes=[]
    for key in before.keys()|after.keys():
        current=path+[key]
        if key not in after:changes.append({'path':current,'remove':True})
        elif key not in before:changes.append({'path':current,'value':after[key]})
        elif isinstance(before[key],dict) and isinstance(after[key],dict):changes.extend(state_changes(before[key],after[key],current))
        elif before[key]!=after[key]:changes.append({'path':current,'value':after[key]})
    return changes

class SharedStateClient:
    def __init__(self,url,token):
        parsed=urlsplit(url)
        if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or len(token)<24:raise ValueError('Configuration des données partagées invalide')
        self.url=url.rstrip('/')+'/v1/state';self.token=token;self.opener=build_opener(ProxyHandler({}),NoRedirect())
    def call(self,payload=None):
        req=Request(self.url,data=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None,headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json'})
        try:
            with self.opener.open(req,timeout=8) as response:
                raw=response.read(6*1024*1024+1)
                if len(raw)>6*1024*1024:raise ValueError()
                result=json.loads(raw)
                if not result.get('ok') or not isinstance(result.get('state'),dict):raise ValueError()
                return result['state']
        except (OSError,ValueError,TypeError):raise SharedStateUnavailable('Données partagées indisponibles : vérifiez la connexion à l’instance centrale. Aucune modification locale n’a été enregistrée.') from None
    def read(self):return self.call()
    def write(self,state):
        if not isinstance(state,SharedStateSnapshot):raise SharedStateUnavailable('Modification sans état de référence refusée.')
        return self.call({'changes':state_changes(state.baseline,state)})
