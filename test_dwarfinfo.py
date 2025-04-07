from unittest import TestCase
from dwarfinfo import DwarfFunctionInfo, pretty_print, traverse_for_function, check_if_really_a_function, \
    check_if_really_a_function_next_line, ts_get_function, tree_sitter_finding_bool
from mock import patch


class Test(TestCase):
    class Object(object):
        pass

    row = Object()
    row.function_name = 'main'
    row.line = 1
    row.path = 'testfiles/hello.c'


    @patch('dwarfinfo.traverse_for_function')
    def test_pretty_print(self, traverse_for_function_mock):
        traverse_for_function_mock.return_value = True
        srcinfo = [DwarfFunctionInfo("main", "testfiles/hello.c", 1, 16)]
        pretty_print(srcinfo)

    def test_traverse_for_function(self):
        row = Test.row
        assert traverse_for_function(row) == True

    def test_traverse_for_function_h(self):
        row = Test.row
        row.line = 2
        row.path = 'testfiles/hello_fort.h'
        assert traverse_for_function(row) == True

    def test_traverse_for_function_next_line(self):
        row = Test.row
        row.path = 'testfiles/hello_next_line.c'
        assert traverse_for_function(row) == True

    def test_traverse_for_function_malloc(self):
        assert traverse_for_function("rlp_main", 1, "testfiles/hello.c") == True

    def test_check_if_really_a_function(self):
        assert check_if_really_a_function("main", "int main() {") == True

    def test_check_if_really_a_function_fortify(self):
        assert check_if_really_a_function("main", "__fortify_function int main() {") == True

    def test_check_if_really_afunction_next_line(self):
        assert check_if_really_a_function_next_line("main", "int main()", "     {") == True

    def test_check_if_really_afunction_false(self):
        assert check_if_really_a_function("main", "int main();") == False

    def test_ts_get_function(self):
        with open('testfiles/hello.c') as f: code = f.read()
        assert ts_get_function(code, 'main') == True

    def test_ts_get_function_h_fort_file(self):
        with open('testfiles/hello_fort.h') as f: code = f.read()
        assert ts_get_function(code, 'main') == True

    def test_ts_get_function_h_file(self):
        with open('testfiles/hello.h') as f: code = f.read()
        assert ts_get_function(code, 'main') == False

    def test_ts_get_function_with_open(self):
        assert tree_sitter_finding_bool('testfiles/hello_fort.h', 'main') == True

    def test_ts_get_function_with_open_false(self):
        assert tree_sitter_finding_bool('testfiles/hello.h', 'main') == False

