# write_dxf.py

def write_dxf(dxf_filename, points_dict, lines_list):
    """
    Zapisuje minimalny plik DXF R12 ASCII z podanymi liniami 2D.
    :param points_dict: {nr_punktu: (x, y, z), ...}
    :param lines_list: [(start_p, end_p), (start_p, end_p), ...]
    """
    with open(dxf_filename, 'w', encoding='utf-8') as f:
        # Można też dodać sekcję HEADER, ale minimalnie wystarczy ENTITIES
        f.write("0\nSECTION\n  2\nENTITIES\n")

        for (p1, p2) in lines_list:
            x1, y1, z1 = points_dict[p1]
            x2, y2, z2 = points_dict[p2]

            # Zapis linii w formacie R12
            # "0" - typ obiektu
            # "LINE" - nazwa obiektu
            # "8" - kod warstwy (np. "0" = warstwa domyślna)
            # "10"/"20" => X/Y startu, "11"/"21" => X/Y końca
            f.write("  0\nLINE\n  8\n0\n")   # warstwa "0"
            f.write(f" 10\n{x1}\n 20\n{y1}\n")  # Start X, Y
            f.write(f" 11\n{x2}\n 21\n{y2}\n")  # End X, Y

        f.write("  0\nENDSEC\n  0\nEOF\n")
