# from collections import defaultdict
import os, sys, re
from elftools.elf.elffile import ELFFile
from prettytable import PrettyTable
from tree_sitter import Parser, Language
import tree_sitter_c as ts_c
import psycopg

function_names = []

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
            #print("Tree sitter CFunction error for:", function_name)
            self.function_node = None


class DwarfFunctionInfo:
    def __init__(self, name, path, line, offset):
        self.name = name
        self.path = path
        self.line = line
        self.offset = offset
        self.verification = False
        self.verification_reason = None

def get_srcinfo_db(path):
    # DB Conn
    conn = psycopg.connect(
        dbname="archsrc",
        user="rouser",
        password="",
        host="kuria",
        port="5432"
    )

    query = """SELECT name, srcabspath, srcline, vaddr
               FROM binary_functions
               WHERE binary_id = (SELECT binary_id
                   FROM binaries
               WHERE compileopt = '00000' and relpath = 'usr/{path}');""".format(path=path)
    function_container = []
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
        for row in rows:
            print(row[0][0], row[1], row[3])
            if row[1] != None:
                function_container.append(DwarfFunctionInfo(row[0], row[1], row[2], row[3]))

    conn.close()
    return function_container

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

def main(path, src_path, db):
    print("Starting script for " + path + " ...")
    # check for DWARF information
    srcinfo = None
    if db:
        srcinfo = get_srcinfo_db(path)
    else:
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

    functions_list = []




    for row in srcinfo:
        combined_path = src_path + row.path
        if row.path.startswith('../'):
            combined_path = src_path + row.path.replace('../', '')

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
        if '/usr/include' in row.path:
            row.path = row.path.replace('/usr/include', './include')

        if tree_sitter_finding_bool(combined_path, row.name):
            functions_list.append(row.name)
            verifications += 1
        else:
            if defines_extension(combined_path, row.name):
                functions_list.append(row.name)
                verifications += 1
            else:
                table.add_row([row.name, row.line, row.path, ''])


    print(sorted(functions_list))
    print(table)
    print_metrics((verifications / count_functions) if verifications > 0 else 0, count_functions, count_functions-verifications)


    
def print_metrics(ver_score, count_functions, fails):
    metrics_table = PrettyTable()
    metrics_table.field_names = ["Verification score", "Functions analyzed", "Fails"]
    metrics_table.add_row([to_percentage_string(ver_score), count_functions, fails])
    print(metrics_table)


def to_percentage_string(percentage_float):
    return str(percentage_float * 100)[0:5] + " %"

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

def adjustment_for_fortify_functions(path, function_name):
    source_file = open(path)
    for i, source_file_line in enumerate(source_file):
        if '__fortify_function' in source_file_line:
            source_file.close()
            return True
    return False

def tree_sitter_finding_bool(path, name):
    #print_if(path, name)
    return ts_get_function(get_code(path), name)

def ts_get_function(code, function_name):
    #print("tree sitter finding function:", function_name)
    tree = parser.parse(code.encode(encoding='utf-8'))
    #print_if(tree.root_node.__str__(), function_name)
    #if CFunction(tree, function_name).function_node is not None:
       # return CFunction(tree, function_name).function_node.text.decode('utf-8') == function_name
    #else:
        #print("tree sitter error:", function_name)
        #return False
    global function_names

    find_function_names(tree.root_node)
    function_names_tree = function_names
    function_names = []
    #print(function_names_tree)
    #for x in function_names_tree:
        #print("ArrayList:", x, "Function_Name:", function_name)
    if function_name in function_names_tree:
        return True
    else:
        if _gl_check(code, function_name):
            return True
        return False

def get_code(path):
    with open(path, 'r') as file:
        code = file.read()
    return code

def _gl_check(code, function_name):
    lines = code.splitlines()
    for i, line in enumerate(lines):
        if '_GL_' in line:
            if function_name in lines[i + 1]:
                return True
    return False

def find_function_names(node):
    #print("Searching for function names in tree...node", str(node.type))
    if str(node.type) == 'function_declarator' or str(node.type) == 'function_declaration':
        #print("Found function declarator")
        for child in node.named_children:
            #print(str(child.type))
            if str(child.type) == 'identifier':
                #print(child.text.decode('utf-8'))
                function_names.append(child.text.decode('utf-8'))
    for child in node.named_children:
        find_function_names(child)

    return function_names



def defines_extension(path, name):
    #print("defines_extension for: ",name," and ", path)
    code = get_code(path)
    for line in code.splitlines():
        match = re.match(r"#\s*define\s+(\S+)\s+" + name, line)
        if match:
            #print("New name: " + match.group(1).strip())
            return tree_sitter_finding_bool(path, match.group(1).strip())
    return tree_sitter_finding_bool(path, renaming(name))

def renaming(name):
    prefixes = ["rpl_", "i_", "m_", "i", "m", "x"]
    #print("Checking for renaming:", name)
    for prefix in prefixes:
        if name.startswith(prefix):
            #print("renaming:", name.replace(prefix, ""))
            return name.replace(prefix, "")
    return name

def print_if(string, name):
    if name == "fseeko":
        print(string)



if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
