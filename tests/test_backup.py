from pathlib import Path
import tempfile
import unittest
from studio.store import StudioStore
from studio.backup import write_backup,check_backup,restore_backup


class BackupTest(unittest.TestCase):
    def test_backup_restore_and_integrity(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'data'
            s=StudioStore(root)
            proj=s.create_project('Real project')
            job=s.create_job(proj['id'],{'schema':'musitu.blender.job.v1','objects':[
                {'name':'Item','type':'sphere','location':[0,0,0],
                 'dimensions':[1,1,1],'material':'teal'}]})
            archive=Path(t)/'backup.zip'
            receipt=write_backup(root,archive)
            self.assertEqual(receipt['entries'],2)
            self.assertTrue(check_backup(archive)['verified'])
            dest=Path(t)/'restore'
            self.assertTrue(restore_backup(archive,dest)['restored'])
            restored=StudioStore(dest)
            self.assertEqual(restored.project(proj['id'])['name'],'Real project')
            self.assertEqual(restored.job(job['id'])['job_sha256'],job['job_sha256'])
            self.assertTrue(str(dest) in restored.job(job['id'])['input_path'])
            with self.assertRaisesRegex(ValueError,'overwrite'):
                write_backup(root,archive)
            with self.assertRaisesRegex(ValueError,'empty'):
                restore_backup(archive,dest)
