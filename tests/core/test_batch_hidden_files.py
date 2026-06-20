import sys
import os
import tempfile
import shutil
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from main import main

class TestBatchHiddenFiles(unittest.TestCase):
    """Tests for batch processing skipping hidden files."""

    def setUp(self):
        self.test_source = tempfile.mkdtemp()
        self.test_outdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_source)
        shutil.rmtree(self.test_outdir)

    @patch('main.process_source')
    @patch('sys.argv')
    def test_skips_hidden_files(self, mock_argv, mock_process_source):
        # Create a visible file and a hidden file
        visible_file = os.path.join(self.test_source, "visible.pdf")
        hidden_file = os.path.join(self.test_source, ".hidden.pdf")
        
        with open(visible_file, 'w') as f:
            f.write("visible")
        with open(hidden_file, 'w') as f:
            f.write("hidden")

        mock_argv.__getitem__.side_effect = lambda i: [
            "main.py", self.test_source, "-o", self.test_outdir, "-m", "llama3"
        ][i] if isinstance(i, int) else [
            "main.py", self.test_source, "-o", self.test_outdir, "-m", "llama3"
        ][i.start:i.stop]
        
        # Patch argparse to return our args
        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            args = MagicMock()
            args.source = self.test_source
            args.outdir = self.test_outdir
            args.model = "llama3"
            mock_parse_args.return_value = args
            
            with patch('main.ensure_model_installed'):
                main()

        # Check that process_source was ONLY called for the visible file
        mock_process_source.assert_called_once()
        called_path = mock_process_source.call_args[0][0]
        self.assertEqual(called_path, visible_file)


if __name__ == '__main__':
    unittest.main()
