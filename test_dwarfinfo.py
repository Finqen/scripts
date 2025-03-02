from unittest import TestCase
from dwarfinfo import DwarfFunctionInfo, pretty_print, traverse_for_function, check_if_really_a_function, \
    check_if_really_a_function_next_line
from mock import patch


class Test(TestCase):

    @patch('dwarfinfo.traverse_for_function')
    def test_pretty_print(self, traverse_for_function_mock):
        traverse_for_function_mock.return_value = True
        srcinfo = [DwarfFunctionInfo("main", "testfiles/hello.c", 1, 16)]
        pretty_print(srcinfo)

    def test_traverse_for_function(self):
        assert traverse_for_function("main", 1, "testfiles/hello.c") == True

    def test_traverse_for_function_h(self):
        assert traverse_for_function("main", 2, "testfiles/hello.h") == True

    def test_traverse_for_function_next_line(self):
        assert traverse_for_function("main", 1, "testfiles/hello_next_line.c") == True

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

