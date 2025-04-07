# from collections import defaultdict
import os, sys, re
from elftools.elf.elffile import ELFFile
from prettytable import PrettyTable
from tree_sitter import Parser, Language
import tree_sitter_c as ts_c

# tree-sitter global object
C_LANGUAGE = Language(ts_c.language())
parser = Parser(C_LANGUAGE)

FUNCTION_QUERY= """
(
    ( function_definition
        declarator: ( function_declarator
            declarator: (identifier) @function_names (#eq? @function_names "{function_name}")
        )
        body: (compound_statement) @function.body
    )
)
"""
class CFunction:
    def __init__(self, tree, function_name):
        function_query = C_LANGUAGE.query(FUNCTION_QUERY.format(function_name=function_name))
        function_captures = function_query.captures(tree.root_node)

        if function_captures:
            self.function_node = function_captures['function_names'][0]
        else:
            self.function_node = None

class DwarfFunctionInfo:
    def __init__(self, name, path, line, offset):
        self.name = name
        self.path = path
        self.line = line
        self.offset = offset
        self.verification = False
        self.verification_reason = None

def get_srcinfo(dwarf):
    function_container = []
    # srcinfo = defaultdict(list)
    for CU in dwarf.iter_CUs():
        lineprog = dwarf.line_program_for_CU(CU)
        file_entries = lineprog.header['file_entry']
        dir_entries = lineprog.header['include_directory']
        file_table, dir_table = dict(), dict()
        #funcnames = set()
        for i, entry in enumerate(file_entries):
            file_table[i] = (entry.dir_index, entry.name.decode('latin-1'))
        for i, entry in enumerate(dir_entries):
            dir_table[i] = entry.decode('latin-1')
        try:
            for DIE in CU.iter_DIEs():
                if DIE.tag == 'DW_TAG_subprogram':
                    name = DIE.attributes['DW_AT_name'].value.decode('latin-1')
                    file_idx = DIE.attributes['DW_AT_decl_file'].value
                    dir_idx, file_name = file_table[file_idx]
                    dir_name = dir_table[dir_idx]
                    line = DIE.attributes['DW_AT_decl_line'].value
                    path = os.path.join(dir_name, file_name)
                    try:
                        declaration = DIE.attributes['DW_AT_declaration'].value
                    except KeyError:
                        declaration = False
                    if declaration:
                        continue
                    try:
                        offset = DIE.attributes['DW_AT_low_pc'].value
                    except KeyError:
                        offset = 0

                    function_container.append(DwarfFunctionInfo(name, path, line, offset))

        except KeyError:
            continue
    return function_container

def main(path, src_path):
    print("Starting script for " + path.rsplit('/', 1)[0] + " ...")
    # check for DWARF information
    srcinfo = None
    with open(path, 'rb') as fo:
        elffile = ELFFile(fo)
        if elffile.has_dwarf_info():
            dwarfinfo = elffile.get_dwarf_info()
            srcinfo = get_srcinfo(dwarfinfo)
    pretty_print(srcinfo, src_path)


def determine_compiler():
    return ".c"

def pretty_print(srcinfo, src_path):

    table = PrettyTable()
    table.field_names = ["Function", "Line", "Path", "Reason"]

    count_functions = 0
    verifications = 0

    for row in srcinfo:
        count_functions += 1
        '''
        row.verification_reason = traverse_for_function(row)
        print(row.verification_reason)

        if row.verification_reason is None:
            row.verification = True
            verifications += 1

        if row.verification is False:
            table.add_row([row.name, row.line, row.path, row.verification_reason])
        '''
        if not(row.path.startswith('/usr/include')):
            if tree_sitter_finding_bool(src_path + row.path, row.name):
                verifications += 1
            else:
                if defines_extension(src_path + row.path, row.name):
                    verifications += 1
                else:
                    table.add_row([row.name, row.line, row.path, ''])
        else:
            print(row.path)

    print(table)
    print_metrics((verifications / count_functions) if verifications > 0 else 0, count_functions, count_functions-verifications)


    
def print_metrics(ver_score, count_functions, fails):
    metrics_table = PrettyTable()
    metrics_table.field_names = ["Verification score", "Functions analyzed", "Fails"]
    metrics_table.add_row([to_percentage_string(ver_score), count_functions, fails])
    print(metrics_table)


def to_percentage_string(percentage_float):
    return str(percentage_float * 100)[0:5] + " %"

def traverse_for_function(row):
    path = row.path
    function_name = row.name
    line = row.line

    # Guards for special cases
    # .h Class
    if path.endswith(".h"):
        if not adjustement_for_fortify_functions(path, function_name):
            return  "h. File - Prototype function"
    # rlp_ function
    if function_name.startswith(get_malloc_prefixes()):
        function_name = function_name.split("_")[1]
    source_file = open(path)
    for i, source_file_line in enumerate(source_file, 1):
        if i == line:
            next_line = source_file.readlines()[0]
            if check_if_really_a_function(function_name, source_file_line):
                source_file.close()
                return None
            # readlines okay here, because we want to stop iterating after
            elif check_if_really_a_function_next_line(function_name, source_file_line, next_line):
                source_file.close()
                return None
            elif check_if_really_a_function_next_lines(function_name, source_file_line, next_line, source_file.readlines()):
                source_file.close()
                return None
            break
    source_file.close()
    return "Not a function!"

def check_if_really_a_function(function_name, line):
    return bool(re.search(function_name + r'\s*\(.*\)*\{', line))

def check_function_definition(function_name, line):
    return bool(re.search(function_name + r'\s*\(.*\)', line))

def check_curly_brace(line):
    return bool(re.search(r'\s*\{', line))

def check_if_really_a_function_next_line(function_name, line, next_line):
    return check_function_definition(function_name, line) and check_curly_brace(next_line)

def check_if_really_a_function_next_lines(function_name, line, next_line, rest_of_lines):
    if check_function_definition(function_name, line):
        if next_line.startswith("#"):
            for i, rest_of_lines_line in enumerate(rest_of_lines):
                if ";" in rest_of_lines_line:
                    return False
                elif check_curly_brace(rest_of_lines_line):
                    return True
                if rest_of_lines_line.startswith("#"):
                    continue
                return False

def adjustement_for_fortify_functions(path, function_name):
    source_file = open(path)
    for i, source_file_line in enumerate(source_file):
        if '__fortify_function' in source_file_line:
            source_file.close()
            return True
    return False

def check_for_fortify_function(line, function_name):
    return 0

def get_malloc_prefixes():
    prefixes = ["rlp_"]
    return tuple(prefixes)

def tree_sitter_finding_bool(path, name):
    return ts_get_function(get_code(path), name)

def ts_get_function(code, function_name):
    tree = parser.parse(code.encode(encoding='utf-8'))
    if CFunction(tree, function_name).function_node is not None:
        return CFunction(tree, function_name).function_node.text.decode('utf-8') == function_name
    return False

def get_code(path):
    with open(path, 'r') as file:
        code = file.read()
    return code

def defines_extension(path, name):
    print("defines_extension for: ",name," and ", path)
    code = get_code(path)
    for line in code:
        match = re.match(r"# define\s+(\S+)\s+" + name, line)
        if match:
            print("Found:", line.strip())
            print("New name: " + match.group(1).trim())
            return ts_get_function(code, match.group(1).trim())
        else:
            return False

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
