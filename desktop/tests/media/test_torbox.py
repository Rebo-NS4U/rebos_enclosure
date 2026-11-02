import json
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import direct_source
import torbox_source as source

TEST_KEY = 'test-only-not-a-real-torbox-key'


class TorBoxTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.credential = Path(self.folder.name) / 'private-key'
        self.path_patch = patch.object(source, 'CREDENTIAL', self.credential)
        self.path_patch.start()
        self.state_patch = patch.object(source, '_LINK_STATE', {'connected':False,'text':'Not connected'})
        self.state_patch.start()

    def tearDown(self):
        source._LINK_CANCEL.set()
        self.state_patch.stop()
        self.path_patch.stop()
        self.folder.cleanup()

    def test_credential_is_private_and_never_returned_in_status(self):
        with patch.object(source, 'request', return_value={'plan':2}):
            result = source.connect_key(TEST_KEY)
        self.assertEqual(stat.S_IMODE(self.credential.stat().st_mode),0o600)
        self.assertNotIn(TEST_KEY,json.dumps(result))
        self.assertNotIn(TEST_KEY,json.dumps(source.status()))
        self.assertEqual(source.read_key(),TEST_KEY)
        source.disconnect()
        self.assertFalse(self.credential.exists())

    def test_failed_account_check_does_not_save_a_key(self):
        with patch.object(source,'request',side_effect=source.TorBoxError('AUTH_ERROR')):
            with self.assertRaises(source.TorBoxError):source.connect_key(TEST_KEY)
        self.assertFalse(self.credential.exists())

    def test_device_sign_in_saves_token_and_reports_only_public_state(self):
        device={'device_code':'private-device-code','code':'ABCD-EFGH','verification_url_complete':'https://torbox.app/device?code=ABCD-EFGH','interval':5,'expires_in':600}
        notify=Mock()
        with patch.object(source,'request',side_effect=[device,{'token':TEST_KEY},{'plan':2}]), patch.object(source.threading,'Thread') as thread:
            public=source.start_link(notify)
            target=thread.call_args.kwargs['target']
            with patch.object(source._LINK_CANCEL,'wait',return_value=False):target()
        self.assertEqual(source.read_key(),TEST_KEY)
        self.assertNotIn('private-device-code',json.dumps(public))
        self.assertNotIn(TEST_KEY,json.dumps(notify.call_args.args[0]))
        self.assertTrue(notify.call_args.args[0]['connected'])

    def test_disconnect_cancels_pending_sign_in_before_saving(self):
        device={'device_code':'private-device-code','code':'ABCD','verification_url':'https://torbox.app/device','interval':5}
        with patch.object(source,'request',return_value=device),patch.object(source.threading,'Thread') as thread:
            source.start_link(Mock())
            target=thread.call_args.kwargs['target']
        source.disconnect()
        target()
        self.assertFalse(self.credential.exists())

    def test_authorization_url_must_belong_to_torbox(self):
        with patch.object(source,'request',return_value={'device_code':'code','verification_url':'https://other.example/'}):
            with self.assertRaises(source.TorBoxError):source.start_link(Mock())

    def test_episode_selection_does_not_choose_another_episode_or_sample(self):
        files=[dict(id=0,name='Show_S01E01.mkv',size=50),dict(id=1,name='Show.S01E02.mkv',size=100),dict(id=2,name='Show.S01E01.sample.mkv',size=200)]
        self.assertEqual(source.pick_file(files,'series','1:1')['id'],0)
        self.assertIsNone(source.pick_file(files,'series','2:1'))

    def candidates(self):
        return {'streams':[{'infoHash':'a'*40,'name':'1080p','title':'Example English WEB-DL'}]}

    def test_quality_limit_never_falls_back_to_4k(self):
        rows = {'streams': [
            {'infoHash': 'a' * 40, 'name': '2160p', 'title': 'English WEB-DL'},
            {'infoHash': 'b' * 40, 'name': '1080p', 'title': 'English WEB-DL'},
            {'infoHash': 'c' * 40, 'name': '720p', 'title': 'English WEB-DL'},
        ]}
        with patch.object(direct_source, 'get_json', return_value=rows):
            found = source.candidates_for('series', 'tt0111161', '1:7', '1080p')
        self.assertEqual([direct_source.resolution(row) for _, row in found], [1080, 720])

    def test_uncached_result_never_creates_a_cloud_job(self):
        source.save_key(TEST_KEY)
        with patch.object(direct_source,'get_json',return_value=self.candidates()) as search, patch.object(source,'request',return_value={}) as api:
            self.assertEqual(list(source.streams('movie','tt0111161','movie')),[])
        self.assertNotIn(TEST_KEY,search.call_args.args[0])
        self.assertEqual(api.call_count,1)
        self.assertEqual(api.call_args.args[0],'torrents/checkcached')

    def test_cached_result_uses_server_enforcement_and_returns_https_only(self):
        source.save_key(TEST_KEY)
        file=dict(id=0,name='Example.English.1080p.mkv',size=1000)
        responses=[{'a'*40:{'files':[file]}},{'torrent_id':42},{'id':42,'download_finished':True,'files':[file]},'https://cdn.torbox.app/example.mkv']
        with patch.object(direct_source,'get_json',return_value=self.candidates()) as search,patch.object(source,'request',side_effect=responses) as api:
            result=list(source.streams('movie','tt0111161','movie'))
        self.assertTrue(direct_source.eligible(result[0]))
        self.assertNotIn('infoHash',result[0])
        form=api.call_args_list[1].kwargs['form']
        self.assertEqual(form['add_only_if_cached'],'true')
        self.assertEqual(form['seed'],3)
        self.assertNotIn(TEST_KEY,search.call_args.args[0])

    def test_availability_is_read_only_and_reuses_cache(self):
        source.save_key(TEST_KEY)
        source._availability.cache_clear()
        file = dict(id=0, name='Example.English.mkv', size=1000)
        with patch.object(direct_source, 'get_json', return_value=self.candidates()), patch.object(source, 'request', return_value={'a'*40: {'files': [file]}}) as api:
            self.assertEqual(source.availability('movie', 'tt0111161'), 'cached')
            self.assertEqual(source.availability('movie', 'tt0111161'), 'cached')
        self.assertEqual(api.call_count, 1)
        self.assertEqual(api.call_args.args[0], 'torrents/checkcached')

    def test_availability_requires_exact_episode_and_handles_outages(self):
        source.save_key(TEST_KEY)
        source._availability.cache_clear()
        file = dict(id=0, name='Show.S01E02.English.mkv', size=1000)
        with patch.object(direct_source, 'get_json', return_value=self.candidates()), patch.object(source, 'request', return_value={'a'*40: {'files': [file]}}):
            self.assertEqual(source.availability('series', 'tt0386676', '1:1'), 'uncached')
            self.assertEqual(source.availability('series', 'tt0386676', '1:2'), 'cached')
        source._availability.cache_clear()
        with patch.object(direct_source, 'get_json', side_effect=RuntimeError('outage')):
            self.assertEqual(source.availability('movie', 'tt0111161'), 'unknown')
        source.disconnect()
        self.assertEqual(source.availability('movie', 'tt0111161'), 'unknown')

    def test_error_text_does_not_echo_api_response(self):
        self.assertNotIn(TEST_KEY,str(source.TorBoxError(TEST_KEY)))

    def test_token_bearing_cdn_links_stay_on_documented_torbox_domains(self):
        url='https://store-044.wnam.tb-cdn.io/dld/video?token='+TEST_KEY
        self.assertEqual(source.cdn_url(url,TEST_KEY),url)
        for host in ('unknown.example','tb-cdn.io.attacker.example','not-torbox.app'):
            with self.assertRaises(source.TorBoxError):
                source.cdn_url('https://'+host+'/video?token='+TEST_KEY,TEST_KEY)

    def test_connected_account_resolves_through_torbox_without_free_fallback(self):
        stream=dict(url='https://cdn.torbox.app/video',name='English 720p')
        with patch.object(source,'read_key',return_value=TEST_KEY),patch.object(source,'streams',return_value=iter([stream])),patch.object(direct_source,'metadata',return_value={'runtime':'22 min'}),patch.object(direct_source,'verify',return_value=['verified']) as verify,patch.object(direct_source,'streams') as free:
            self.assertEqual(direct_source.resolve('direct:series:tt0386676','1:1','720p'),['verified'])
            verify.assert_called_once_with(stream,1320,'720p')
            free.assert_not_called()
