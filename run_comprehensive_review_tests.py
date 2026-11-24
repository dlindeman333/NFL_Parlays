"""Run offline comprehensive review tests without production credentials."""
import unittest
from pathlib import Path
import sys

if __name__ == '__main__':
    root=Path(__file__).resolve().parent
    sys.path.insert(0,str(root))
    loader=unittest.TestLoader()
    suite=unittest.TestSuite()
    for directory in (root,root/'phase3'):
        suite.addTests(loader.discover(str(directory),pattern='test_comprehensive*.py',top_level_dir=str(directory)))
    if not suite.countTestCases():
        raise SystemExit('No comprehensive tests discovered')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
