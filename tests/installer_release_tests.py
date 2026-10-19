"""Independent installer publication identity and safety tests."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/ci'))
import installer_release as release


class InstallerPublicationTests(unittest.TestCase):
    def setUp(self):
        self.job={'id':41,'name':'verify','status':'completed','conclusion':'success'}
    def build(self,**changes):
        values=dict(root=ROOT,source='a'*40,channel='devel',run=100,attempt=1,job=self.job)
        values.update(changes);return release.build(**values)
    def test_exact_installer_bytes_and_compatibility_are_published_without_firmware(self):
        manifest,files=self.build()
        self.assertEqual(set(files),{'usb-installer.json','usb_installer.py','release-manifest-1.schema.json'})
        self.assertEqual(manifest['contract'],1)
        self.assertEqual(manifest['transaction_schema'],'wsprrypico-usb-transaction/1')
        self.assertEqual(manifest['result_schema'],'wsprrypico-usb-result/1')
        self.assertEqual(files['usb_installer.py'],(ROOT/'scripts/usb_installer.py').read_bytes())
        for name,item in manifest['files'].items():
            self.assertEqual(release.digest(files[name]),item['sha256']);self.assertEqual(len(files[name]),item['bytes'])
        record=release.index(manifest,files)
        self.assertEqual(record['manifest_sha256'],release.digest(files['usb-installer.json']))
        self.assertIn(json.dumps(record,sort_keys=True),release.body(record))
    def test_failed_missing_or_ambiguous_verification_is_refused(self):
        for key,value in [('name','other'),('status','in_progress'),('conclusion','failure'),('id',True),('id',0)]:
            job=dict(self.job,**{key:value})
            with self.subTest(key=key),self.assertRaises(ValueError):self.build(job=job)
        for values in [dict(source='devel'),dict(channel='other'),dict(run=0),dict(attempt=True)]:
            with self.subTest(values=values),self.assertRaises(ValueError):self.build(**values)
    def test_existing_published_assets_cannot_be_replaced(self):
        manifest,files=self.build()
        existing={'tag_name':manifest['tag'],'prerelease':True,'body':release.body(release.index(manifest,files)),
                  'draft':False,'assets':[{'name':'usb_installer.py','state':'uploaded','size':1,'digest':'sha256:'+'0'*64}]}
        with tempfile.TemporaryDirectory() as temporary,patch.object(release.publish,'ensure_tag'),patch.object(release.publish,'find_version_release',return_value=existing):
            with self.assertRaisesRegex(ValueError,'size/SHA'):release.publish_bundle(manifest,files,Path(temporary)/'release')
    def test_workflow_has_independent_verify_and_publish_dependency(self):
        workflow=(ROOT/'.github/workflows/usb-installer.yml').read_text()
        self.assertIn('needs: verify',workflow);self.assertIn('python tests/usb_installer_tests.py',workflow)
        self.assertIn('python tests/installer_release_tests.py',workflow)
        self.assertNotIn('build_pico',workflow);self.assertNotIn('scripts/ci/run.py build',workflow)
    def test_channel_advances_only_after_every_asset_is_verified_and_public(self):
        manifest,files=self.build();state={'release':None,'channel':None,'calls':[]}
        def api(path,method='GET',data=None,missing=False):
            state['calls'].append((path,method,copy.deepcopy(data)))
            if path=='releases' and method=='POST':
                if data['draft']:
                    state['release']={**data,'id':1,'assets':[]};return state['release']
                self.assertFalse(state['release']['draft']);self.assertEqual(len(state['release']['assets']),3)
                state['channel']=data;return data
            if path=='releases/1':
                if method=='PATCH':state['release'].update(data)
                return state['release']
            if path=='releases/tags/usb-installer-v1-devel':return None
            raise AssertionError(path)
        def upload(args,check):
            path=Path(args[4]);data=path.read_bytes()
            state['release']['assets'].append({'name':path.name,'state':'uploaded','size':len(data),'digest':'sha256:'+release.digest(data)})
        with tempfile.TemporaryDirectory() as temporary,patch.object(release.publish,'ensure_tag'),patch.object(release.publish,'find_version_release',return_value=None),patch.object(release.publish,'api',side_effect=api),patch.object(release.subprocess,'run',side_effect=upload):
            release.publish_bundle(manifest,files,Path(temporary)/'release')
        self.assertIsNotNone(state['channel']);self.assertEqual(state['channel']['body'],release.body(release.index(manifest,files)))
    def test_failed_upload_never_publishes_or_advances_channel(self):
        manifest,files=self.build();pending={'tag_name':manifest['tag'],'prerelease':True,
            'body':release.body(release.index(manifest,files)),'draft':True,'assets':[]}
        with tempfile.TemporaryDirectory() as temporary,patch.object(release.publish,'ensure_tag'),patch.object(release.publish,'find_version_release',return_value=pending),patch.object(release.publish,'api') as api,patch.object(release.subprocess,'run',side_effect=RuntimeError('upload failed')):
            with self.assertRaisesRegex(RuntimeError,'upload failed'):release.publish_bundle(manifest,files,Path(temporary)/'release')
            api.assert_not_called()


if __name__=='__main__':unittest.main()
