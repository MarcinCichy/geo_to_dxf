import math

def parse_geo(geo_filename):
    """
    Odczytuje plik GEO Trumpfa (w uproszczeniu) i zwraca:
      - points: słownik {nr_punktu: (x, y, z)}
      - lines: lista [(start_p, end_p, color_idx), ...]
      - arcs:  lista [(center_p, start_p, end_p, direction, color_idx), ...]

    Logika:
      - W sekcji "LIN" pobieramy linię parametrów (np. "1 0", "3 0" itd.).
        Jeśli w tokenach pojawi się '2' lub '3', uznajemy, że to grawerka (kolor żółty, 2),
        w przeciwnym razie domyślnie kolor wynosi 7.
      - Analogicznie dla poleceń "ARC".
    """
    points = {}
    lines_list = []
    arcs = []

    with open(geo_filename, 'r', encoding='utf-8') as f:
        file_lines = [line.strip() for line in f]

    in_points_section = False
    in_edges_section = False
    i = 0
    while i < len(file_lines):
        line = file_lines[i]

        # Wykrywanie sekcji
        if line.startswith("#~31"):
            in_points_section = True
            in_edges_section = False
            i += 1
            continue
        elif line.startswith("#~331"):
            in_points_section = False
            in_edges_section = True
            i += 1
            continue
        elif line.startswith("#~") and not line.startswith("#~3"):
            in_points_section = False
            in_edges_section = False
            i += 1
            continue

        # Parsowanie sekcji punktów
        if in_points_section:
            if line == "P":
                # Kolejne linie: identyfikator, współrzędne, a potem separator ("|~")
                point_id = int(file_lines[i + 1])
                coords = file_lines[i + 2].split()
                x, y, z = float(coords[0]), float(coords[1]), float(coords[2])
                points[point_id] = (x, y, z)
                i += 4  # pomijamy: "P", id, współrzędne, "|~"
                continue

        # Parsowanie sekcji krawędzi (LIN/ARC)
        if in_edges_section:
            if line == "LIN":
                # Pobieramy linię parametrów (np. "1 0" lub "3 0")
                param_line = file_lines[i + 1]
                tokens = param_line.split()

                # Domyślnie: kolor = 7 (np. cięcie)
                # Jeśli w tokenach znajduje się '2' lub '3', uznajemy to za grawer (żółty)
                if any(token in {"2", "3"} for token in tokens):
                    color_index = 2
                else:
                    color_index = 7

                # Pobieramy identyfikatory punktów
                points_line = file_lines[i + 2]
                start_p_str, end_p_str = points_line.split()
                start_p = int(start_p_str)
                end_p = int(end_p_str)

                lines_list.append((start_p, end_p, color_index))
                i += 4  # LIN, param_line, punkty, separator ("|~")
                continue

            elif line == "ARC":
                param_line = file_lines[i + 1]
                tokens = param_line.split()

                if any(token in {"2", "3"} for token in tokens):
                    color_index = 2
                else:
                    color_index = 7

                arc_points_line = file_lines[i + 2]
                center_str, start_str, end_str = arc_points_line.split()
                center_id = int(center_str)
                start_id = int(start_str)
                end_id = int(end_str)

                direction_line = file_lines[i + 3]
                direction = int(direction_line)

                arcs.append((center_id, start_id, end_id, direction, color_index))
                i += 5  # ARC, param_line, punkty, kierunek, separator ("|~")
                continue

        i += 1

    return points, lines_list, arcs
