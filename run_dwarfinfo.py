import csv
import psycopg
import os
from datetime import datetime

import dwarfinfo_return

def beautify_pkg_name(path):
    if len(path.split("/bin/")) == 2:
        return path.split("/bin/")[1]
    else:
        return path

def get_package_info_db():
    # DB Conn
    conn = psycopg.connect(
        dbname="archsrc",
        user="rouser",
        password="",
        host="kuria",
        port="5432"
    )

    query = """SELECT b.pkg, b.abspath, b.binary_id
               FROM binaries b
               WHERE b.compileopt = '00000' AND b.pkg NOT LIKE 'aarch64-linux-gnu-%'
               ORDER BY b.pkg LIMIT 10;"""
    packackge_container = []
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
        for row in rows:
            packackge_container.append([row[0], row[1], row[2]])
    conn.close()
    return packackge_container

def contains_c_files(srcpath):
    for foldername, subfolders, filenames in os.walk(srcpath):
        for filename in filenames:
            if filename.endswith('.c') or filename.endswith('.h'):
                return True

    return False

def write_to_csv_file(filename, line):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["pkg", "abspath", "functions", "verified", "binary_id"])
        writer.writerow(line)
    csvfile.close()

def create_csv_file(filename):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["pkg", "abspath", "functions", "verified", "binary_id"])
    csvfile.close()

def main():
    now = datetime.now()
    datum_str = now.strftime("%Y-%m-%d-%H_%M_%S")
    filename = datum_str + ".csv"
    packages = get_package_info_db()
    metrics = []
    create_csv_file(filename)
    for package in packages:
        if contains_c_files(package[1].split("/bin/")[0]):
            metric = dwarfinfo_return.main(package[0], package[1], True, "")
            line = [beautify_pkg_name(package[1]), package[1], metric[0], metric[1], package[2]]
        else:
            line = [beautify_pkg_name(package[1]), package[1], '', "No source files", package[2]]
        write_to_csv_file(filename, line)

    duration = datetime.now()-now
    print("Done! Running took: " + str(duration.total_seconds()))

#python run_dwarfinfo.py &> output.log &
if __name__ == '__main__':
    main()
