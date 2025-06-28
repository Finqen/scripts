import csv
import sys

import psycopg
import os
from datetime import datetime

import dwarfinfo_return

def beautify_name(path):
        return path.split('/')[-1]

def get_package_info_db(compile_opt):
    # DB Conn
    conn = psycopg.connect(
        dbname="small-db",
        user="rouser",
        password="",
        host="kuria",
        port="5432"
    )

    query = """SELECT b.pkg, b.abspath, b.binary_id, b.relpath
               FROM binaries b
               WHERE b.compileopt = '{compile_opt}' AND b.abspath = '/small-db/pkg/clang-O0/acl-2.3.2-1-x86_64/usr/bin/getfacl'
               ORDER BY b.pkg LIMIT 10;""".format(compile_opt=compile_opt)
    packackge_container = []
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
        for row in rows:
            packackge_container.append([row[0], row[1], row[2], row[3]])
    conn.close()
    return packackge_container

def contains_c_files(srcpath):
    for foldername, subfolders, filenames in os.walk(srcpath):
        for filename in filenames:
            if filename.endswith('.c') or filename.endswith('.h'):
                return True

    return False

def write_to_csv_file(filename, line):
    with open(filename, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(line)
    csvfile.close()

def create_csv_file(filename):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["bin", "pkg", "abspath", "functions", "verified", "binary_id"])
    csvfile.close()

def main(compile_opt):
    now = datetime.now()
    datum_str = now.strftime("%Y-%m-%d-%H_%M_%S")
    filename = datum_str + ".csv"
    packages = get_package_info_db(compile_opt)
    create_csv_file(filename)
    for package in packages:
        metric = dwarfinfo_return.main(package[0], package[1], True, "", package[2])
        line = [beautify_name(package[3]), package[0], package[1], metric[0], metric[1], package[2]]
        write_to_csv_file(filename, line)

    duration = datetime.now()-now
    print("Done! Running took: " + str(duration.total_seconds()) + " seconds...")

#python run_dwarfinfo.py &> output.log &
#tmux zum starten des Skript
if __name__ == '__main__':
    main(sys.argv[1])
