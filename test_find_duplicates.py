
from unittest import TestCase
import subprocess
import os
from tempfile import mkdtemp
import shutil
import re

HERE = os.path.dirname(__file__)
CORPUS = os.path.join(HERE, 'test-recordings')
CORPUS_A = os.path.join(CORPUS, 'a')
CORPUS_B = os.path.join(CORPUS, 'b')
CORPUS_C = os.path.join(CORPUS, 'c')
BIN = os.path.join(HERE, 'find-duplicates')

COLOUR_RE = r"(?:\033|\x1b)\[0\d(;\d\d)?m"


class FindDupesTest(TestCase):
    maxDiff = 5000

    @classmethod
    def setUpClass(cls):
        cls.tempdir = mkdtemp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tempdir)

    def setUp(self):
        self.output_file = os.path.join(self.tempdir,
                                        self.id().rsplit('.', 1)[1])

    def _test_run(self, cmd,
                  stdout_patterns=(),
                  file_patterns=None,
                  returncode=0,
                  n_lines=None):
        p = subprocess.run(cmd, capture_output=True)
        self.assertEqual(p.returncode, returncode)

        stdout = p.stdout.decode()

        for regex in stdout_patterns:
            self.assertRegex(stdout, regex)

        if file_patterns is None:
            self.assertFalse(os.path.exists(self.output_file))
        else:
            for regex in file_patterns:
                with open(self.output_file) as f:
                    self.assertRegex(f.read(), regex)

        if n_lines is not None:
            self.assertEqual(n_lines, stdout.count('\n'))

        return stdout

    def _test_a(self, cmd, extra_patterns=[], **kwargs):
        s = self._test_run(cmd,
                           stdout_patterns=[
                               'fingerprinting 3 files\n'
                               r'...\nfingerprinting took [\d.]+ seconds\n'
                               'comparing 3 pairs',
                               f'{CORPUS_A}/maple-leaf-rag-4.opus',
                               f'{CORPUS_A}/maple-leaf-rag-8k-2.opus'
                           ] + extra_patterns,
                           **kwargs
                           )
        return s

    def test_a_simple(self):
        cmd = [BIN, CORPUS_A]
        self._test_a(cmd, n_lines=16)

    def test_a_verbose(self):
        # in this case, output is nearly the same as non-verbose
        cmd = [BIN, CORPUS_A, '-v']
        self._test_a(cmd,
                     ['possible match: \d\d / 640'],
                     n_lines=17)

    def test_a_trim_verbose(self):
        cmd = [BIN, CORPUS_A, '-v', '--trim-silence']
        self._test_a(cmd,
                     ['possible match: \d\d / 640'])

    def test_a_colour_auto(self):
        # --colour=auto is the default
        cmd = [BIN, CORPUS_A, '--colour=auto']
        self._test_a(cmd)

    def test_a_colour_no(self):
        # the same as the --colour=auto when not directed to a
        # terminal.
        cmd = [BIN, CORPUS_A, '--colour=no']
        self._test_a(cmd)

    def test_a_colour_yes(self):
        cmd = [BIN, CORPUS_A, '-v', '--colour=yes']
        stdout = self._test_a(cmd)
        self.assertRegex(stdout, COLOUR_RE)

        colourless = re.sub(COLOUR_RE, '', stdout)
        cmd_no = [BIN, CORPUS_A, '-v', '--colour=no']
        stdout_no = self._test_a(cmd_no)

        # we can't assert on exact timings
        colourless = re.sub("[\d.]+ seconds", "X", colourless)
        stdout_no = re.sub("[\d.]+ seconds", "X", stdout_no)

        self.assertEqual(stdout_no, colourless)

    def test_a_output(self):
        cmd = [BIN, CORPUS_A, '-o', self.output_file]
        self._test_a(cmd, file_patterns=[
            '--- 2 duplicates ---',
            (r'20\d\d-\d\d-\d\d \d\d:\d\d +292580  '
             f'{CORPUS_A}/maple-leaf-rag-4.opus'),
            (r'20\d\d-\d\d-\d\d \d\d:\d\d +171483  '
             f'{CORPUS_A}/maple-leaf-rag-8k-2.opus'),
        ])

    def test_a_plus_readme(self):
        cmd = [BIN, CORPUS_A, os.path.join(CORPUS, 'README')]
        self._test_run(cmd,
                       stdout_patterns=[
                           'fingerprinting 4 files\n'
                           r'[.2]{4}\nfingerprinting took [\d.]+ seconds\n'
                           'comparing 3 pairs',
                           f'{CORPUS_A}/maple-leaf-rag-4.opus',
                           f'{CORPUS_A}/maple-leaf-rag-8k-2.opus'
                       ])

    def test_a_plus_readme_verbose(self):
        readme = os.path.join(CORPUS, 'README')
        cmd = [BIN, CORPUS_A, readme, '-v']
        self._test_run(cmd,
                       stdout_patterns=[
                           f"{readme} is not audio",
                           'comparing 3 pairs',
                       ])

    def test_a_plus_non_file(self):
        # A non-existent path should result in an error code and
        # message. The output file won't be created.
        notthere = os.path.join(CORPUS, 'sdfo apo ss')
        cmd = [BIN, CORPUS_A, notthere, '-o', self.output_file]
        self._test_run(cmd,
                       returncode=1,
                       stdout_patterns=[
                           f"can't read {notthere}"
                       ])

        self.assertRaises(FileNotFoundError, open, self.output_file)

    def _test_b(self, cmd, extra_patterns=[], **kwargs):
        files = [os.path.join(CORPUS_B, x) for x in os.listdir(CORPUS_B)
                 if 'middle' not in x and 'trailing' not in x]

        stdout_patterns = [
            ('fingerprinting 7 files\n'
             '[.]{7}\nfingerprinting took'),
            'comparing 21 pairs',
            f'found one cluster in:\s+{CORPUS_B}',
            '--- 5 duplicates ---'
        ]
        stdout_patterns.extend(files)
        stdout_patterns.extend(extra_patterns)

        return self._test_run(cmd,
                              stdout_patterns=stdout_patterns,
                              **kwargs
                              )

    def test_b_simple(self):
        cmd = [BIN, CORPUS_B]
        self._test_b(cmd, n_lines=55)

    def test_b_verbose(self):
        cmd = [BIN, CORPUS_B, '-v']
        self._test_b(cmd,
                     extra_patterns=['possible match: 0 / 640',
                                     r'\n1\.0\n'],
                     n_lines=85)

    def test_b_trim_silence(self):
        # corpus b is very different with --trim-silence: there are no
        # matches at all (i.e. all matches were on leading silence)
        cmd = [BIN, CORPUS_B, '-t']

        stdout_patterns = [
            '^fingerprinting 7 files\n'
            '[2.]{7}\n'
            'fingerprinting took \d+\.\d{2} seconds\n'
            'comparing 10 pairs\n'
            'comparisons took \d\.\d{2} seconds\n'
            '\n'
            'found no clusters in: \n'
            f'   {CORPUS_B}\n$'
        ]
        self._test_run(cmd,
                       stdout_patterns=stdout_patterns,
                       n_lines=8)

    def test_a_b_trim_silence(self):
        # one file in b matches the pair in a
        cmd = [BIN, '-t', CORPUS_B, CORPUS_A]

        stdout_patterns = [
            '^fingerprinting 10 files\n'
            '[2.:]{10}\n'
            'fingerprinting took \d+\.\d{2} seconds\n'
            'comparing 28 pairs\n',
             f'{CORPUS_A}/maple-leaf-rag-4.opus',
             f'{CORPUS_A}/maple-leaf-rag-8k-2.opus',
             f'{CORPUS_B}/scott-joplin-maple-leaf-rag-45s-silence.mp3',
            'comparisons took \d+\.\d{2} seconds\n',
            'found one cluster in: \n',
            f'   {CORPUS_A}\n',
            f'   {CORPUS_B}\n',
            '--- 3 duplicates ---',
             f' 171483  {CORPUS_A}/maple-leaf-rag-8k-2.opus',
        ]
        self._test_run(cmd,
                       stdout_patterns=stdout_patterns)

    def test_a_c(self):
        # in this we have two different performances of maple leaf rag
        # that do not clister together.
        cmd = [BIN, CORPUS_A, CORPUS_C]

        stdout_patterns = [
            '^fingerprinting 12 files\n'
            r'\.{9}:\.\.\n'
            'fingerprinting took \d+\.\d{2} seconds\n'
            'comparing 66 pairs\n',
            'found 3 clusters in: \n'
            f'   {CORPUS_A}\n'
            f'   {CORPUS_C}\n',
            '--- 2 duplicates ---',
            '--- 3 duplicates ---',
        ]
        self._test_run(cmd,
                       stdout_patterns=stdout_patterns,
                       n_lines=42)

    def test_c_a(self):
        # reversing the order of arguments will find the same
        # clusters, but output order will differ slightly
        cmd = [BIN, CORPUS_C, CORPUS_A]

        stdout_patterns = [
            '^fingerprinting 12 files\n'
            r'\.{9}:\.\.\n'
            'fingerprinting took \d+\.\d{2} seconds\n'
            'comparing 66 pairs\n',
            'found 3 clusters in: \n'
            f'   {CORPUS_C}\n'
            f'   {CORPUS_A}\n',
            '--- 2 duplicates ---',
            '--- 3 duplicates ---',
        ]
        self._test_run(cmd,
                       stdout_patterns=stdout_patterns,
                       n_lines=42)

    def test_a_c_trim(self):
        # same clusters as without trim, but a silent file is ignored
        cmd = [BIN, '-t', CORPUS_C, CORPUS_A]

        stdout_patterns = [
            '^fingerprinting 12 files\n'
            r'[2:.]{12}\n',
            'comparing 55 pairs\n',
            'found 3 clusters in: \n'
            f'   {CORPUS_C}\n'
            f'   {CORPUS_A}\n',
            '--- 2 duplicates ---',
            '--- 3 duplicates ---',
        ]
        self._test_run(cmd,
                       stdout_patterns=stdout_patterns,
                       n_lines=42)

    def test_b_c(self):
        # in this we have two different performances of maple leaf rag
        # that do not clister together.
        cmd = [BIN, CORPUS_B, CORPUS_C]

        stdout_patterns = [
            '^fingerprinting 16 files\n'
            r'\.{9}:\.{6}\n'
            'fingerprinting took \d+\.\d{2} seconds\n'
            'comparing 120 pairs\n',
            'found 3 clusters in: \n'
            f'   {CORPUS_B}\n'
            f'   {CORPUS_C}\n',
            '--- 2 duplicates ---',
            '--- 7 duplicates ---',
        ]
        self._test_run(cmd,
                       stdout_patterns=stdout_patterns)

    def test_b_c_trim(self):
        # several files reduce to nothing
        cmd = [BIN, '-t', CORPUS_B, CORPUS_C]

        stdout_patterns = [
            '^fingerprinting 16 files\n'
            r'[2:.]{16}\n',
            'comparing 78 pairs\n',
            'found 3 clusters in: \n'
            f'   {CORPUS_B}\n'
            f'   {CORPUS_C}\n',
            '--- 2 duplicates ---',
        ]
        self._test_run(cmd,
                       stdout_patterns=stdout_patterns,
                       n_lines=33)

    def test_all(self):
        cmd = [BIN, CORPUS]
        stdout_patterns = [
            # allow for uncertainty because there might be a backup README~
            '^fingerprinting 2\d files\n'
            '[2.:]{20,21}\n'
            'fingerprinting took \d+\.\d{2} seconds\n'
            'comparing 171 pairs\n',
             f'{CORPUS_A}/',
             f'{CORPUS_B}/',
             f'{CORPUS_C}/',
            'comparisons took \d+\.\d{2} seconds\n',
            'found 4 clusters in: \n'
            f'   {CORPUS}\n',
            '--- 2 duplicates ---',
            '--- 9 duplicates ---',
        ]
        self._test_run(cmd,
                       stdout_patterns=stdout_patterns)

    def test_all_trim(self):
        cmd = [BIN, CORPUS, '-t']
        stdout_patterns = [
            '^fingerprinting 2\d files\n'
            '[2.:]{20,21}\n'
            'fingerprinting took \d+\.\d{2} seconds\n'
            'comparing 120 pairs\n',
            'comparisons took \d+\.\d{2} seconds\n',
            'found 4 clusters in: \n'
            f'   {CORPUS}\n',
            '--- 2 duplicates ---',
            '--- 4 duplicates ---',
        ]
        self._test_run(cmd,
                       stdout_patterns=stdout_patterns)

    def test_all_trim_verbose(self):
        cmd = [BIN, CORPUS, '-tv']
        stdout_patterns = [
            '^fingerprinting 2\d files\n',
            f'ERROR 2  {CORPUS}/README is not audio\n',
            # These files *are* audio, but when silence is trimmed,
            # there is nothing left.
            f'ERROR 2  {CORPUS_B}/120s-silence-2.opus is not audio',
            f'ERROR 2  {CORPUS_B}/120s-silence.ogg is not audio',
            f'ERROR 2  {CORPUS_C}/120s-silence-2.opus is not audio',
            'fingerprinting took \d+\.\d{2} seconds\n'
            'comparing 120 pairs\n',
            'possible match: 107 / 640',
            'possible match: 43 / 640',
            'possible match: 33 / 640',
            'possible match: 0 / 640',
            'possible match: 48 / 640',
            'possible match: 103 / 640',
            'possible match: 143 / 640',
            'possible match: 130 / 640',
            'possible match: 50 / 640',
            'comparisons took \d+\.\d{2} seconds\n',
            'found 4 clusters in: \n'
            f'   {CORPUS}\n',
            '--- 2 duplicates ---',
            '--- 4 duplicates ---',
        ]
        self._test_run(cmd,
                       stdout_patterns=stdout_patterns)
