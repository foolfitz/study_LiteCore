"""Run causal reversions entirely in memory against the actual cleanup tests."""
from pathlib import Path
import contextlib
import io
import types
import unittest
from unittest import mock
import test_v23_packaging_resume as resume_tests
import v23_diagnostic_packaging_test as wrapper_tests


def module_variant(original, before, after):
    source = Path(original.__file__).read_text()
    if source.count(before) != 1:
        raise AssertionError('mutation site drift')
    changed = types.ModuleType('cleanup_mutant')
    changed.__file__ = original.__file__
    exec(compile(source.replace(before, after), original.__file__, 'exec'), changed.__dict__)
    return changed


class CleanupMutations(unittest.TestCase):
    def test_causal_reversions_are_red(self):
        cases = [
            (resume_tests, 'resume', resume_tests.Resume, 'test_partial_profile_is_refused_without_overwrite',
             "(output.exists() and (not output.is_dir() or any(output.iterdir()))) or ", ''),
            (resume_tests, 'resume', resume_tests.Resume, 'test_postpackage_input_change_quarantines_whole_profile',
             '        verify_rows(protected, ROOT)\n        return result', '        return result'),
            (resume_tests, 'resume', resume_tests.Resume, 'test_quarantine_error_keeps_primary_error_and_continues',
             '                error.add_note(f"quarantine failed for {path}: {cleanup_error}")', '                raise'),
            (wrapper_tests, 'builder', wrapper_tests.PackagingFailures, 'test_rejected_manifest_bytes_are_preserved',
             '''                    fd, failed = tempfile.mkstemp(prefix="sdk-manifest.failed-", suffix=".json",
                                                   dir=known.output)
                    os.close(fd)
                    os.replace(manifest_path, failed)''',
             '                    manifest_path.unlink()'),
        ]
        for host, name, cls, test, before, after in cases:
            with self.subTest(test=test):
                mutant = module_variant(getattr(host, name), before, after)
                with mock.patch.object(host, name, mutant), contextlib.redirect_stdout(io.StringIO()):
                    result = unittest.TestResult()
                    unittest.TestSuite([cls(test)]).run(result)
                self.assertEqual(result.testsRun, 1)
                self.assertFalse(result.wasSuccessful(), 'causal reversion did not turn red')

if __name__ == '__main__':unittest.main()
