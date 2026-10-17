import copy
import json
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
from job_schema import validate_job, load_job

GOOD = {'schema':'musitu.blender.job.v1','job_id':'StudioDemo01',
        'objects':[{'name':'Floor', 'type':'cube','location':[0,0,0],
                    'dimensions':[5,5,0.2], 'material':'ivory'}],
        'frame_end':24,
        'animations':[{'object':'Floor','axis':'Z','degrees':90,'start':1,'end':24}]}


class JobValidationTests(unittest.TestCase):
    def changed(self, fn):
        value = copy.deepcopy(GOOD)
        fn(value)
        with self.assertRaises((ValueError, TypeError)):
            validate_job(value)

    def test_valid_job(self):
        self.assertEqual(validate_job(copy.deepcopy(GOOD))['job_id'], 'StudioDemo01')

    def test_reject_script(self):
        self.changed(lambda x: x.update({'python':'import os; os.system("true")'}))

    def test_reject_path_id(self):
        self.changed(lambda x: x.update({'job_id':'../../data'}))

    def test_reject_bad_schema(self):
        self.changed(lambda x: x.update({'schema':'other'}))

    def test_reject_nan(self):
        self.changed(lambda x: x['objects'][0]['dimensions'].__setitem__(0, float('nan')))

    def test_reject_nonpositive_dimensions(self):
        self.changed(lambda x: x['objects'][0]['dimensions'].__setitem__(0, -1))

    def test_reject_unsupported_material(self):
        self.changed(lambda x: x['objects'][0].update({'material':'file:///etc/passwd'}))

    def test_reject_unsupported_primitive(self):
        self.changed(lambda x: x['objects'][0].update({'type':'script'}))

    def test_reject_unknown_object_reference(self):
        self.changed(lambda x: x['animations'][0].update({'object':'NoSuchObject'}))

    def test_reject_keyframes_out_of_range(self):
        self.changed(lambda x: x['animations'][0].update({'end':2000}))

    def test_reject_boolean_number(self):
        self.changed(lambda x: x['objects'][0]['location'].__setitem__(0, True))

    def test_reject_duplicate_name(self):
        self.changed(lambda x: x['objects'].append(dict(x['objects'][0])))

    def test_reject_invalid_frame_end(self):
        self.changed(lambda x: x.update({'frame_end':1}))

    def test_reject_duplicate_track(self):
        self.changed(lambda x: x['animations'].append(dict(x['animations'][0])))

    def test_reject_unexpected_object_field(self):
        self.changed(lambda x: x['objects'][0].update({'filepath':'/tmp/secrets'}))

    def test_reject_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/'test.json'
            p.write_text('{"schema":"musitu.blender.job.v1","schema":"second","job_id":"A","objects":[]}')
            with self.assertRaises(ValueError):
                load_job(p)

    def test_reject_nonfinite_json_token(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/'test.json'
            p.write_text('{"schema":"musitu.blender.job.v1","job_id":"A","objects":[],"x":NaN}')
            with self.assertRaises(ValueError):
                load_job(p)

    def test_reject_oversized_file(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/'test.json'
            p.write_text(' ' * (70*1024))
            with self.assertRaises(ValueError):
                load_job(p)


if __name__ == '__main__':
    unittest.main()
