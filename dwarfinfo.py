# from collections import defaultdict
import os, sys, re
from elftools.elf.elffile import ELFFile
from prettytable import PrettyTable


class DwarfFunctionInfo:
    def __init__(self, name, path, line, offset):
        self.name = name
        self.path = path
        self.line = line
        self.offset = offset
        self.verification = False

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

def main(path):
    print("Starting script for " + path.rsplit('/', 1)[0] + " ...")
    # check for DWARF information
    srcinfo = None
    with open(path, 'rb') as fo:
        elffile = ELFFile(fo)
        if elffile.has_dwarf_info():
            dwarfinfo = elffile.get_dwarf_info()
            srcinfo = get_srcinfo(dwarfinfo)
    pretty_print(srcinfo)


def determine_compiler():
    return ".c"

def pretty_print(srcinfo):

    table = PrettyTable()
    table.field_names = ["Function", "Line", "Path"]

    count_functions = 0
    verifications = 0

    for row in srcinfo:
        table.add_row([row.name, row.path, row.line])
        count_functions += 1
        if row.path.endswith(determine_compiler()):
            if traverse_for_function(row.name, row.line, row.path):
                row.verification = True
                verifications += 1

    
    print(table)
    print_metrics((verifications / count_functions) if verifications > 0 else 0, count_functions, count_functions-verifications)


    
def print_metrics(ver_score, count_functions, ends_not_with_suffix):
    metrics_table = PrettyTable()
    metrics_table.field_names = ["Verification score", "Functions analyzed", "Wrong suffix"]
    metrics_table.add_row([to_percentage_string(ver_score), count_functions, ends_not_with_suffix])
    print(metrics_table)


def to_percentage_string(percentage_float):
    return str(percentage_float * 100)[0:5] + " %"

def traverse_for_function(function_name, line, path):
    # Guards for special cases
    # .h Class
    if path.endswith(".h"):
        if not adjustement_for_fortify_functions(path, function_name):
            return False
    # rlp_ function
    if function_name.startswith(get_malloc_prefixes()):
        function_name = function_name.split("_")[1]
    source_file = open(path)
    for i, source_file_line in enumerate(source_file, 1):
        if i == line:
            if check_if_really_a_function(function_name, source_file_line):
                source_file.close()
                return True
            # readlines okay here, because we want to stop iterating after
            elif check_if_really_a_function_next_line(function_name, source_file_line, source_file.readlines()[0]):
                source_file.close()
                return True
            break
    source_file.close()
    return False

def check_if_really_a_function(function_name, line):
    return bool(re.search(function_name + r'\s*\(.*\)*\{', line))

def check_if_really_a_function_next_line(function_name, line, next_line):
    return bool(re.search(function_name + r'\s*\(.*\)', line)) and bool(re.search(r'\s*\{', next_line))

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



if __name__ == '__main__':
    main(sys.argv[1])
