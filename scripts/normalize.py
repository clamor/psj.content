# -*- coding: utf-8 -*-
#
# normalize terms
#
# This file contains tests. You can run tests simply by::
#
#   `python -m unittest normalize`
#
# or you install py.test in your virtualenv (pip install pytest) and run
#
#   `py.test normalize.py`
#
# in this directory. The latter is much more comfortable in the long run.
#
import dinsort
import gzip
import os
import tempfile
import shutil
import unittest


INFILE_PATH = "identifier.txt.gz"
OUTFILE_PATH = "terms.txt"

# how are numbers and terms separated in files?
SEPARATOR = "&&"


def filter_term(term):
    """Strip unwanted chars.

    Currently we only remove "<" and ">".
    """
    for removable in ("<", ">"):
        term = term.replace(removable, "")
    return term


def normalize_list(inpath, outpath, separator):
    """Turn a list of terms into normalized form.

    For instance::

        123&&Term1
        124&&Term Number 2

    will become::

        123&&term1&&Term1
        124&&term number 2&&Term Number 2

    etc. Here the `separator` string is "&&" in both,
    input and output file.
    """
    print("Opening %s for reading..." % inpath)
    with gzip.open(inpath, "r") as infile:
        with open(outpath, "w") as outfile:
            for cnt, line in enumerate(infile.readlines()):
                if cnt % 100000 == 0:
                    # ping back every 10**6th entry
                    print("Done: %s entries" % cnt)
                id_num, term = line.strip().split(separator, 1)
                term = filter_term(term)
                term = term.decode("utf-8")
                normalized = dinsort.normalize(term)
                out_term = "%s%s%s%s%s\n" % (
                    id_num, separator, normalized, separator, term)
                outfile.write(out_term.encode("utf-8"))
    print("Done. Written results to %s" % outpath)


class TestFilterTerm(unittest.TestCase):

    def test_no_change_string(self):
        # most terms will be returned unchanged
        result = filter_term("foo")
        assert result == "foo"
        assert isinstance(result, str)

    def test_no_change_unicode(self):
        # we can pass in unicode terms.
        result = filter_term(u"foo")
        assert result == u"foo"
        assert isinstance(result, unicode)

    def test_tags_are_stripped(self):
        # tag chars ('<', '>') are stripped
        result = filter_term(u"foo <bar>")
        assert result == u"foo bar"

    def test_umlauts(Self):
        # we cope with umlauts
        assert filter_term(u"fär <bar>") == u"fär bar"
        assert filter_term("fär <bar>") == "fär bar"


class TestNormalizeList(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.infile = os.path.join(self.tempdir, "identifiers.gz")
        self.outfile = os.path.join(self.tempdir, "terms.txt")
        self.create_gzip_file(b"1&&Term1\n2&&Term2\n3&&Tärm3\n")

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def create_gzip_file(self, contents):
        with gzip.open(self.infile, 'wb') as fd:
            fd.write(contents)

    def test_normalize_list(self):
        normalize_list(self.infile, self.outfile, "&&")
        assert os.path.isfile(self.outfile)
        with open(self.outfile, "rb") as fd:
            result = fd.read()
        assert result == (
            "1&&term1&&Term1\n"
            "2&&term2&&Term2\n"
            "3&&tarm3&&Tärm3\n")

if __name__ == "__main__":
    normalize_list(INFILE_PATH, OUTFILE_PATH, SEPARATOR)
