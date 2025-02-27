from collections import defaultdict
import os, sys
from elftools.elf.elffile import ELFFile
from prettytable import PrettyTable


def get_srcinfo(dwarf):
    srcinfo = defaultdict(list)
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
                    
                    srcinfo[name].append((path, offset, line))
        except KeyError:
            continue
    return srcinfo

def main(path):
    print("Starting script for <" + path + "> ...")
    # check for DWARF information
    srcinfo = None
    with open(path, 'rb') as fo:
        elffile = ELFFile(fo)
        if elffile.has_dwarf_info():
            print("<" + path + ">" + " has dwarf info...")
            dwarfinfo = elffile.get_dwarf_info()
            srcinfo = get_srcinfo(dwarfinfo)
    prettyPrint(srcinfo, path)


def determineCompiler():
    return ".c"
    return ".cpp"
    return ".rs"

def prettyPrint(srcinfo, path):

    table = PrettyTable()
    table.field_names = ["Function", "Line", "Path"]

    pathArray = path.split(".")
    

    countFunctions = 0
    endsNotWith_c = 0

    for row in srcinfo:
        # Setting vars
        name = row
        path = srcinfo[row][0][0]
        line = srcinfo[row][0][2]

        table.add_row([name, path, line])
        countFunctions += 1
        if not path.endswith(determineCompiler()):
            endsNotWith_c += 1

    
    print(table)
    printMetrics(1-(0 if endsNotWith_c == 0 else endsNotWith_c/countFunctions), countFunctions, endsNotWith_c)


    
def printMetrics(verScore, countFunctions, endsNotWith_c):
    metricsTable = PrettyTable()
    metricsTable.field_names = ["Verification score", "Functions analyzed", "Wrong suffix"]
    metricsTable.add_row([toPercentageString(verScore), countFunctions, endsNotWith_c])
    print(metricsTable)


def toPercentageString(float):
    return str(float*100)[0:5] + " %"


if __name__ == '__main__':
    main(sys.argv[1])