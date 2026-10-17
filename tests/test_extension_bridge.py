import io
import json
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
from extension_bridge import register_extension

class BridgeTests(unittest.TestCase):
    def make(self,auth=True,url='http://companion:8090',token='private-token-'+'x'*32):
        app=Flask(__name__);app.testing=True
        imported=[]
        register_extension(app,url=url,token=token,authenticated=lambda:auth,
                           context_for=lambda vid:{'id':vid,'size':10,'mtime':1},
                           import_metadata=lambda *args:imported.append(args),start_worker=False)
        return app.test_client(),imported
    def test_disabled_and_unauthenticated(self):
        client,_=self.make(url='',token='')
        self.assertEqual(client.get('/api/extension/v1/config').status_code,404)
        client,_=self.make(auth=False)
        self.assertEqual(client.get('/api/extensions/library').status_code,401)
        self.assertEqual(client.get('/api/extensions/contexts').status_code,401)
        self.assertEqual(client.get('/api/extension/v1/config').status_code,401)
    def test_token_added_server_side_and_cookie_not_forwarded(self):
        client,_=self.make()
        response=MagicMock();response.read.return_value=b'{"ok":true}';response.status=200;response.headers={'Content-Type':'application/json'}
        response.__enter__.return_value=response
        with patch('urllib.request.OpenerDirector.open',return_value=response) as transport:
            result=client.get('/api/extension/v1/config',headers={'Cookie':'session=private'})
            req=transport.call_args.args[0]
            self.assertTrue(req.get_header('Authorization').startswith('Bearer private-token'))
            self.assertIsNone(req.get_header('Cookie'))
            self.assertNotIn(b'private-token',result.data)
    def test_transport_refuses_arbitrary_paths(self):
        client,_=self.make()
        self.assertEqual(client.get('/api/extension/health').status_code,404)
        self.assertEqual(client.get('/api/extension/v1/../private').status_code,404)
        self.assertEqual(client.post('/api/extension/v1/config',data='secret').status_code,415)
    def test_import_uses_server_context(self):
        client,imported=self.make()
        response=MagicMock();response.read.return_value=json.dumps({'result':{'tags':['landscape']}}).encode();response.status=200;response.headers={'Content-Type':'application/json'};response.__enter__.return_value=response
        with patch('urllib.request.OpenerDirector.open',return_value=response) as transport:
            self.assertEqual(client.post('/api/extensions/metadata/video',json={'size':999}).status_code,200)
            self.assertEqual(json.loads(transport.call_args.args[0].data)['size'],10)
            self.assertEqual(imported[0][1]['size'],10)
    def test_invalid_backend_configuration_rejected(self):
        for url in ('http://user:secret@host','file:///etc/passwd','http://host?token=secret'):
            with self.assertRaises(ValueError):self.make(url=url)
    def test_recommendations_distinguish_empty_results_from_companion_failure(self):
        client,_=self.make()
        response=MagicMock();response.status=200;response.headers={'Content-Type':'application/json'};response.__enter__.return_value=response
        response.read.return_value=json.dumps({'ok':True,'groups':[{'id':'similar','videos':[]}],'opinions':{}}).encode()
        with client.application.test_request_context('/'),patch('urllib.request.OpenerDirector.open',return_value=response) as transport:
            result=client.application.extensions['minivid_recommendations']('focus')
            self.assertEqual(result,{'videos':[],'opinions':{}})
            self.assertEqual(transport.call_args.kwargs['timeout'],3)
            payload=json.loads(transport.call_args.args[0].data)
            self.assertEqual(payload['focus'],'focus');self.assertEqual(payload['count'],20)
            response.read.return_value=b'{}'
            self.assertIsNone(client.application.extensions['minivid_recommendations']('focus'))
        client,_=self.make(auth=False)
        with client.application.test_request_context('/'),patch('urllib.request.OpenerDirector.open') as transport:
            self.assertIsNone(client.application.extensions['minivid_recommendations']('focus'))
            transport.assert_not_called()
