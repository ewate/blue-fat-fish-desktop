import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import bridge


class BridgeTests(unittest.TestCase):
    def test_remaining_and_missing_windows(self):
        result = bridge.limit_windows({'rateLimitsByLimitId': {
            'codex': {'primary': {'usedPercent': 86, 'windowDurationMins': 10080},
                      'secondary': None},
            'other': {'primary': {'usedPercent': None}}}})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['remaining'], 14)
        self.assertIn('7 天', result[0]['label'])
        self.assertEqual(bridge.limit_windows({}), [])

    def test_values_clamp_and_second_window(self):
        result = bridge.limit_windows({'rateLimits': {
            'primary': {'usedPercent': 103, 'windowDurationMins': 300},
            'secondary': {'usedPercent': -1, 'windowDurationMins': 10080}}})
        self.assertEqual([x['remaining'] for x in result], [0, 100])

    def test_live_message_and_completion_are_refreshed(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            db = sqlite3.connect(folder/'thread_history_1.sqlite')
            db.executescript('CREATE TABLE thread_turns(thread_id,turn_id,status,started_at,completed_at,rollout_ordinal);'
                             'CREATE TABLE thread_items(thread_id,item_json,created_at_ms,item_type,rollout_ordinal);')
            db.execute('INSERT INTO thread_turns VALUES(?,?,?,?,?,?)', ('a','t','inProgress',1,None,1))
            db.execute('INSERT INTO thread_items VALUES(?,?,?,?,?)',
                       ('a',json.dumps({'text':'第一条进度','phase':'commentary'}),1000,'agentMessage',1))
            db.commit()
            with patch.object(bridge,'CODEX_DIR',folder):
                self.assertEqual(bridge.read_chat('a')['label'],'正在工作')
                self.assertEqual(bridge.read_chat('a')['text'],'第一条进度')
                db.execute("UPDATE thread_turns SET status='completed',completed_at=3")
                db.execute('INSERT INTO thread_items VALUES(?,?,?,?,?)',
                           ('a',json.dumps({'text':'新的最终回复','phase':'final_answer'}),3000,'agentMessage',2))
                db.commit()
                snapshot = bridge.read_chat('a')
                self.assertEqual(snapshot['label'],'已完成')
                self.assertEqual(snapshot['text'],'新的最终回复')
                self.assertEqual(snapshot['phase'],'final_answer')
                self.assertEqual(bridge.read_chat('missing')['state'],'unknown')
            db.close()


if __name__ == '__main__':
    unittest.main()
