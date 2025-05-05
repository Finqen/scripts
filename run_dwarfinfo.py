import subprocess
import csv
import psycopg
import sys
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

    query = """SELECT b.pkg, b.abspath, f.srcabspath
               FROM binaries b JOIN binary_functions f on b.binary_id = f.binary_id
               WHERE b.compileopt = '00000' and f.srcabspath like '/usr%'
               ORDER BY b.pkg LIMIT 100;"""
    packackge_container = []
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
        for row in rows:
            if row[2] != None:
                srcabspath = row[1].split("/usr")[0]+row[2]
                packackge_container.append([row[0], row[1], srcabspath])

    conn.close()
    return packackge_container

def main():
    now = datetime.now()
    datum_str = now.strftime("%Y-%m-%d-%H_%M_%S")
    filename = datum_str + ".csv"
    packages = get_package_info_db()
    metrics = []
    for package in packages:
        metric = dwarfinfo_return.main(package[1], package[2], True, "")
        metrics.append([package[0], metric[0], metric[1]])

    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow("package, functions, verified")

        for line in metrics:
            writer.writerow(line)

    csvfile.close()

    duration = datetime.now()-now
    print("Done! Running took: " + str(duration.total_seconds()))


if __name__ == '__main__':
    main()
