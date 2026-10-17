"""Fail-closed tests; these never run user-controlled Blender or remote compute."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import enterprise_worker as worker

FIXTURE = Path(__file__).resolve().parents[1] / 'examples' / 'approved_demo.json'


class WorkerPolicyTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = Path(self.t.name)
        self.job = self.root / 'job.json'
        self.job.write_bytes(FIXTURE.read_bytes())
        self.sha = worker.digest(self.job)
        self.output = self.root / 'runs'
        self.output.mkdir(mode=0o700)
        self.blender = self.root / 'mock-blender'
        self.blender.write_text('#!/bin/sh\nexit 1\n')
        self.blender.chmod(0o700)

    def tearDown(self):
        self.t.cleanup()

    def test_loads_valid_job(self):
        self.assertEqual(worker.validate_request(self.job, self.sha, self.output, self.blender)['schema'], 'musitu.blender.job.v1')

    def test_rejects_modified_job_after_approval(self):
        d = json.loads(self.job.read_text())
        d['objects'][0]['material'] = 'copper'
        self.job.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
            worker.validate_request(self.job, self.sha, self.output, self.blender)

    def test_rejects_noncanonical_digest(self):
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            worker.validate_request(self.job, 'A' * 64, self.output, self.blender)

    def test_rejects_job_symlink(self):
        other = self.root / 'linked.json'
        other.symlink_to(self.job)
        with self.assertRaisesRegex(ValueError, 'non-symlink'):
            worker.validate_request(other, self.sha, self.output, self.blender)

    def test_rejects_blender_symlink(self):
        other = self.root / 'linked-blender'
        other.symlink_to(self.blender)
        with self.assertRaisesRegex(ValueError, 'not a symlink'):
            worker.validate_request(self.job, self.sha, self.output, other)

    def test_rejects_output_root_symlink(self):
        other = self.root / 'linked-out'
        other.symlink_to(self.output, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'must not be a symlink'):
            worker.validate_request(self.job, self.sha, other, self.blender)

    def test_rejects_unsupported_gpu_device_argument(self):
        args = ['--job', str(self.job), '--expected-sha256', self.sha,
                '--output-root', str(self.output), '--blender', str(self.blender),
                '--device', 'CUDA']
        with self.assertRaises(SystemExit) as cm:
            worker.main(args)
        self.assertEqual(cm.exception.code, 2)

    def test_rejects_threads_over_cap_without_calling_blender(self):
        with patch.object(worker.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'threads'):
                worker.execute(self.job, self.sha, self.output, self.blender, cpu_threads=100)
            run.assert_not_called()

    def test_rejects_timeout_over_cap_without_calling_blender(self):
        with patch.object(worker.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'Timeout'):
                worker.execute(self.job, self.sha, self.output, self.blender, timeout_seconds=601)
            run.assert_not_called()

    def test_success_records_receipt_and_does_not_inherit_env(self):
        with patch.object(worker.subprocess, 'run', return_value=SimpleNamespace(returncode=0)) as run, \
             patch.object(worker, 'verify', return_value={'result': 'PASS', 'verified_meshes': 12}):
            os.environ['MUSITU_LEAK_TEST_SECRET'] = 'NEVER_COPY_THIS'
            try:
                code, receipt, folder = worker.execute(self.job, self.sha, self.output, self.blender)
            finally:
                os.environ.pop('MUSITU_LEAK_TEST_SECRET', None)
        self.assertEqual(code, 0)
        self.assertEqual(receipt['state'], 'VERIFIED')
        self.assertFalse(receipt['gpu_verified'])
        self.assertNotIn('MUSITU_LEAK_TEST_SECRET', run.call_args.kwargs['env'])
        self.assertFalse(run.call_args.kwargs.get('shell', False))
        self.assertEqual(receipt, json.loads((folder / 'worker_receipt.json').read_text()))
        self.assertEqual(run.call_args.args[0][-4:], ['--job', str(self.job), '--outdir', str(folder/'artifacts')])

    def test_never_overwrites_duplicate_job_id(self):
        with patch.object(worker.subprocess, 'run', return_value=SimpleNamespace(returncode=0)), \
             patch.object(worker, 'verify', return_value={'result': 'PASS'}):
            _, _, folder = worker.execute(self.job, self.sha, self.output, self.blender)
            snapshot = (folder/'worker_receipt.json').read_text()
            with self.assertRaises(FileExistsError):
                worker.execute(self.job, self.sha, self.output, self.blender)
        self.assertEqual(snapshot, (folder/'worker_receipt.json').read_text())

    def test_blender_nonzero_fails_closed(self):
        with patch.object(worker.subprocess, 'run', return_value=SimpleNamespace(returncode=1)):
            code, receipt, folder = worker.execute(self.job, self.sha, self.output, self.blender)
        self.assertEqual(code, worker.EXIT_RUNTIME)
        self.assertEqual(receipt['state'], 'FAILED')
        self.assertEqual(receipt['process_returncode'], 1)
        self.assertTrue((folder/'worker_receipt.json').exists())

    def test_blender_zero_exit_without_evidence_fails_closed(self):
        # Key regression: Blender may return 0 despite a failed Python script.
        with patch.object(worker.subprocess, 'run', return_value=SimpleNamespace(returncode=0)):
            code, receipt, _ = worker.execute(self.job, self.sha, self.output, self.blender)
        self.assertNotEqual(code, 0)
        self.assertEqual(receipt['state'], 'FAILED')

    def test_timeout_preserves_failure_receipt(self):
        def expire(*a, **kw):
            raise worker.subprocess.TimeoutExpired(cmd='blender', timeout=5)
        with patch.object(worker.subprocess, 'run', side_effect=expire):
            code, receipt, folder = worker.execute(self.job, self.sha, self.output, self.blender, timeout_seconds=5)
        self.assertNotEqual(code, 0)
        self.assertEqual(receipt['failure'], 'TIMEOUT')
        self.assertTrue((folder/'worker_receipt.json').exists())


if __name__ == '__main__':
    unittest.main()
