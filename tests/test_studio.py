import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from studio.store import StudioStore, Conflict, Missing
from studio.web import create_app
from studio.queue_worker import execute_one

ADMIN='x' * 48
SAMPLE={'schema':'musitu.blender.job.v1','frame_end':12,'objects':[
    {'name':'Cuboid','type':'cube','location':[0,0,0],
     'dimensions':[1,2,3],'material':'teal'}]}

class QueueStorage(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=StudioStore(self.tmp.name)
        self.project=self.store.create_project('Development proof')
    def tearDown(self):self.tmp.cleanup()
    def job(self):return self.store.create_job(self.project['id'], SAMPLE)

    def test_persistent_restart(self):
        j=self.job()
        new=StudioStore(self.tmp.name)
        self.assertEqual(new.job(j['id'])['job_sha256'],j['job_sha256'])
        self.assertEqual(len(new.projects()),1)

    def test_approval_and_immutable_digest(self):
        j=self.job()
        self.assertEqual(j['state'],'DRAFT')
        self.store.approve(j['id'])
        claimed=self.store.claim()
        self.assertEqual(claimed['id'],j['id'])
        self.assertEqual(claimed['state'],'RUNNING')
        self.assertIsNone(self.store.claim())
        self.store.finish(j['id'],True,'d'*64)
        self.assertEqual(self.store.job(j['id'])['state'],'VERIFIED')
        with self.assertRaises(Conflict):self.store.approve(j['id'])

    def test_changed_input_cannot_be_approved(self):
        j=self.job()
        p=Path(j['input_path'])
        p.write_text(p.read_text()+'\n')
        with self.assertRaisesRegex(Conflict,'digest changed'):
            self.store.approve(j['id'])
        self.assertEqual(self.store.job(j['id'])['state'],'DRAFT')

    def test_cancel_before_start(self):
        j=self.job()
        self.store.cancel(j['id'])
        self.assertIsNone(self.store.claim())
        with self.assertRaises(Conflict):self.store.cancel(j['id'])

    def test_recover_worker_crash_fail_closed(self):
        j=self.job()
        self.store.approve(j['id'])
        self.store.claim()
        self.assertEqual(StudioStore(self.tmp.name).recover_interrupted(),1)
        self.assertEqual(self.store.job(j['id'])['state'],'FAILED')
        self.assertIsNone(self.store.claim())

    def test_concurrent_atomic_claim_once(self):
        j=self.job();self.store.approve(j['id'])
        found=[]
        threads=[threading.Thread(target=lambda:found.append(self.store.claim())) for _ in range(8)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(len([x for x in found if x]),1)

    def test_no_direct_job_id_or_code_injection(self):
        with self.assertRaises(ValueError):self.store.create_job(self.project['id'],{**SAMPLE,'job_id':'MyOwnId'})
        with self.assertRaises(ValueError):self.store.create_job(self.project['id'],{**SAMPLE,'python':'open("/etc/passwd")'})

    def test_failed_worker_records_failure_and_does_not_retry(self):
        j=self.job();self.store.approve(j['id'])
        with patch('studio.queue_worker.execute',side_effect=RuntimeError('simulated failure')):
            status=execute_one(self.store,Path('/fake/blender'))
        self.assertEqual(status['state'],'FAILED')
        self.assertIsNone(self.store.claim())
        self.assertEqual(len(self.store.audit_log()),5)

    def test_session_csrf(self):
        token,csrf=self.store.session_create()
        self.assertTrue(self.store.session_check(token,csrf))
        self.assertEqual(self.store.session_csrf(token),csrf)
        self.assertFalse(self.store.session_check(token,'bad'))
        self.store.session_delete(token)
        self.assertFalse(self.store.session_check(token,csrf))

class WebAPITest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.app=create_app(root=self.tmp.name,admin_token=ADMIN,allowed_hosts=['testserver'])
        self.client=TestClient(self.app)
        response=self.client.post('/api/login',json={'token':ADMIN})
        self.assertEqual(response.status_code,200,response.text)
        self.csrf=response.json()['csrf']
    def tearDown(self):
        self.client.close()
        self.tmp.cleanup()
    def change(self,url,payload=None,csrf=True):
        hdr={'X-CSRF-Token':self.csrf} if csrf else {}
        return self.client.post(url,json=payload if payload is not None else {},headers=hdr)

    def test_assets_and_auth_headers(self):
        self.assertEqual(self.client.get('/').status_code,200)
        self.assertEqual(self.client.get('/static/app.css').status_code,200)
        self.assertEqual(self.client.get('/healthz').json()['ready_for_commercial_rendering'],False)
        r=self.client.get('/api/projects')
        self.assertEqual(r.status_code,200)
        self.assertIn('Content-Security-Policy',r.headers)
        anon=TestClient(self.app)
        self.assertEqual(anon.get('/api/projects').status_code,401)
        anon.close()

    def test_project_job_approval_flow(self):
        p=self.change('/api/projects',{'name':'MUSITU Designs'})
        self.assertEqual(p.status_code,201,p.text)
        pid=p.json()['id']
        job=self.change('/api/projects/'+pid+'/jobs',SAMPLE)
        self.assertEqual(job.status_code,201,job.text)
        jid=job.json()['id']
        self.assertEqual(job.json()['state'],'DRAFT')
        self.assertEqual(self.change('/api/jobs/'+jid+'/approve').json()['state'],'QUEUED')
        self.assertEqual(self.client.get('/api/jobs/'+jid+'/files/preview.png').status_code,409)
        self.assertEqual(len(self.client.get('/api/jobs').json()['jobs']),1)
        self.assertEqual(len(self.client.get('/api/audit').json()['events']),4)

    def test_csrf_refusal(self):
        self.assertEqual(self.change('/api/projects',{'name':'hack'},csrf=False).status_code,403)
        bad=self.client.post('/api/projects',json={'name':'hack'},headers={'X-CSRF-Token':'wrong'})
        self.assertEqual(bad.status_code,403)
        wrong=self.client.post('/api/projects',json={'name':'hack'},headers={'X-CSRF-Token':self.csrf,'Origin':'https://evil.example'})
        self.assertEqual(wrong.status_code,403)
        self.assertEqual(self.client.get('/api/projects').json()['projects'],[])

    def test_duplicate_json_keys_rejected(self):
        r=self.client.post('/api/projects',content=b'{"name":"good","name":"bad"}',headers={'x-csrf-token':self.csrf,'content-type':'application/json'})
        self.assertEqual(r.status_code,400,r.text)

    def test_token_cannot_be_used_as_file_path(self):
        self.assertEqual(self.client.get('/api/jobs/../../../../etc/passwd').status_code,404)
        self.assertEqual(self.client.get('/api/jobs/wrong/files/secrets.txt').status_code,404)

    def test_logout_revokes_session(self):
        self.assertEqual(self.change('/api/logout').status_code,200)
        self.assertEqual(self.client.get('/api/projects').status_code,401)

    def test_secure_cookie(self):
        app=create_app(root=self.tmp.name,admin_token=ADMIN,secure_cookie=True,allowed_hosts=['testserver'])
        # Secure cookies only get sent over HTTPS; check Set-Cookie attributes.
        with TestClient(app) as client:
            r=client.post('/api/login',json={'token':ADMIN})
            self.assertIn('Secure',r.headers['set-cookie'])
            self.assertIn('HttpOnly',r.headers['set-cookie'])
            self.assertIn('SameSite=strict',r.headers['set-cookie'])
            self.assertIn('__Host-',r.headers['set-cookie'])

if __name__=='__main__':unittest.main()
