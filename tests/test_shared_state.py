import json
import unittest
from unittest.mock import MagicMock,patch
from extension_bridge import SharedStateClient,SharedStateSnapshot,SharedStateUnavailable,state_changes

class SharedStateTests(unittest.TestCase):
    def test_patch_preserves_unrelated_changes_and_explicit_removal(self):
        before={'fav':{'one':True},'prefs':{'theme':'dark','lang':'fr'},'progress':{'one':5}}
        after=SharedStateSnapshot(before);after['fav']['two']=True;after['fav'].pop('one');after['progress']['one']=8
        patch=state_changes(after.baseline,after)
        self.assertEqual({tuple(i['path']) for i in patch},{('fav','one'),('fav','two'),('progress','one')})
        self.assertEqual(next(i for i in patch if i['path']==['fav','one']),{'path':['fav','one'],'remove':True})
        self.assertEqual(after.baseline,before)
    def test_client_uses_fixed_endpoint_server_token_and_no_local_fallback(self):
        client=SharedStateClient('http://companion:8090','x'*32)
        response=MagicMock();response.__enter__.return_value=response;response.read.return_value=b'{"ok":true,"state":{"fav":{}}}'
        with patch.object(client.opener,'open',return_value=response) as call:
            self.assertEqual(client.read(),{'fav':{}})
            self.assertEqual(call.call_args.args[0].full_url,'http://companion:8090/v1/state')
            self.assertEqual(call.call_args.args[0].get_header('Authorization'),'Bearer '+'x'*32)
            state=SharedStateSnapshot({'fav':{}});state['fav']['one']=True;client.write(state)
            self.assertEqual(json.loads(call.call_args.args[0].data)['changes'],[{'path':['fav','one'],'value':True}])
        with patch.object(client.opener,'open',side_effect=OSError('private-token')):
            with self.assertRaises(SharedStateUnavailable) as error:client.read()
            self.assertNotIn('private-token',str(error.exception))
    def test_write_requires_a_snapshot_and_config_rejects_unsafe_urls(self):
        with self.assertRaises(SharedStateUnavailable):SharedStateClient('http://companion','x'*32).write({'fav':{}})
        for url in ('file:///data','http://user:secret@host','http://host?token=secret'):
            with self.assertRaises(ValueError):SharedStateClient(url,'x'*32)
