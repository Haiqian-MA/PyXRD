#!/usr/bin/python
# coding=UTF-8
# ex:ts=4:sw=4:et=on

# Copyright (c) 2013, Mathijs Dumon
# All rights reserved.
# Complete license can be found in the LICENSE file.

import os, io

from pyxrd.generic.io.file_parsers import BaseParser

__all__ = [
    'TestParserMixin',
]


def load_data_from_files(*files):
    basepath = os.path.realpath(os.getcwd())
    for fname in files:
        with open(basepath + "/" + fname, 'rb') as f:
            yield f.read()

class TestParserMixin(object):

    parser_class = BaseParser
    file_data = [
        "",
    ]

    def test_description(self):
        self.assertNotEqual(self.parser_class.description, "")

    def test_filters(self):
        self.assertIsNotNone(self.parser_class.file_filter)

    def test_parsing(self):
        for data in self.file_data:
            f = io.BytesIO(data)
            data_objects = self.parser_class.parse("Test", f=f)
            self.assertGreater(len(data_objects), 0)

    # TODO:
    # - check arguments such as close.