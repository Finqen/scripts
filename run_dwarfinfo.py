import csv
import psycopg
import os
from datetime import datetime

import dwarfinfo_return


def get_package_info_db():
    # DB Conn
    conn = psycopg.connect(
        dbname="archsrc",
        user="rouser",
        password="",
        host="kuria",
        port="5432"
    )

    query = """SELECT b.pkg, b.abspath
               FROM binaries b
               WHERE b.compileopt = '00000'
               ORDER BY b.pkg;"""
    packackge_container = []
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
        for row in rows:
            packackge_container.append([row[0], row[1]])

    conn.close()
    return packackge_container

def contains_c_files(srcpath):
    for foldername, subfolders, filenames in os.walk(srcpath):
        for filename in filenames:
            if filename.endswith('.c') or filename.endswith('.h'):
                return True

    return False

def main():
    now = datetime.now()
    datum_str = now.strftime("%Y-%m-%d-%H_%M_%S")
    filename = datum_str + ".csv"
    packages = get_package_info_db()
    metrics = []
    for package in packages:
        if contains_c_files(package[1].split("/bin/")[0]):
            metric = dwarfinfo_return.main(package[0], package[1], True, "")
            metrics.append([package[1].split("/bin/")[1], package[1], metric[0], metric[1]])
        else:
            metrics.append([package[1].split("/bin/")[1], package[1], '', "No source files"])

    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["pkg", "abspath", "functions", "verified"])

        for line in metrics:
            writer.writerow(line)

    csvfile.close()

    duration = datetime.now()-now
    print("Done! Running took: " + str(duration.total_seconds()))


if __name__ == '__main__':
    main()
