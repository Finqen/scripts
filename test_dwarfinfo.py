from unittest import TestCase
from dwarfinfo import DwarfFunctionInfo, pretty_print, traverse_for_function
from mock import patch


class Test(TestCase):

    @patch('dwarfinfo.traverse_for_function')
    def test_pretty_print(self, traverse_for_function_mock):
        traverse_for_function_mock.return_value = True
        srcinfo = [DwarfFunctionInfo("main", "./hello.c", 1, 16)]
        pretty_print(srcinfo)


    def test_traverse_for_function(self):
        assert traverse_for_function("main", 1, "./hello.c") == True