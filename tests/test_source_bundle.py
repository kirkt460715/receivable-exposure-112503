"""验证资料交换格式并检查常见交付格式错误。"""

import json
from pathlib import Path
import tempfile
import unittest

from source_bundle import BundleError, load_bundle


class SourceBundleTest(unittest.TestCase):
    def test_example_bundle(self):
        directory = Path(__file__).resolve().parents[1] / 'input'
        contract = json.loads((directory / 'contract.json').read_text(encoding='utf-8'))
        tables = load_bundle(directory)
        self.assertEqual(set(contract['tables']), set(tables))
        self.assertTrue(all(tables.values()))

    def test_preserves_null_and_order(self):
        with tempfile.TemporaryDirectory() as work:
            path = self.bundle(work, ['{"id":"2","parent":null}', '{"id":"1","parent":"P"}'])
            rows = load_bundle(path)['events']
            self.assertEqual(rows, [{'id': '2', 'parent': None}, {'id': '1', 'parent': 'P'}])

    def test_rejects_duplicate_and_bad_reference(self):
        samples = [
            (['{"id":"1","parent":"P"}', '{"id":"1","parent":"P"}'], '主键重复'),
            (['{"id":"1","parent":"missing"}'], '无对应记录'),
            (['{"id":"1"}'], '字段与字典不一致'),
        ]
        for rows, error in samples:
            with self.subTest(rows=rows), tempfile.TemporaryDirectory() as work:
                with self.assertRaisesRegex(BundleError, error):
                    load_bundle(self.bundle(work, rows))

    def bundle(self, work, rows):
        path = Path(work)
        contract = {
            'tables': {
                'owners': {'columns': {'id': '主体'}, 'key': ['id'], 'refs': {}},
                'events': {'columns': {'id': '事件', 'parent': '主体'},
                           'key': ['id'], 'refs': {'parent': 'owners.id'}},
            },
        }
        (path / 'contract.json').write_text(json.dumps(contract), encoding='utf-8')
        (path / 'owners.jsonl').write_text('{"id":"P"}\n', encoding='utf-8')
        (path / 'events.jsonl').write_text('\n'.join(rows) + '\n', encoding='utf-8')
        return path
