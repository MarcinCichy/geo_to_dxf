# parse_geo.py
import math

def parse_geo(geo_filename):
    """
    Odczytuje plik GEO Trumpfa (w uproszczeniu) i zwraca:
      - points: słownik {nr_punktu: (x, y, z)}
      - lines: lista [(start_p, end_p), ...]
      - arcs: lista [(center_p, start_p, end_p, direction), ...]
    """
    points = {}
    lines = []
    arcs = []

    with open(geo_filename, 'r', encoding='utf-8') as f:
        lines_file = f.readlines()

    in_points_section = False
    in_lines_section = False

    i = 0
    while i < len(lines_file):
        line = lines_file[i].strip()

        # Wykrywanie sekcji
        if line.startswith("#~31"):
            # Sekcja punktów
            in_points_section = True
            in_lines_section = False
            i += 1
            continue
        elif line.startswith("#~331"):
            # Sekcja krawędzi (linia/łuk) – tzw. #~3xx
            in_points_section = False
            in_lines_section = True
            i += 1
            continue
        elif line.startswith("#~") and not line.startswith("#~3"):
            # Koniec aktualnej sekcji
            in_points_section = False
            in_lines_section = False
            i += 1
            continue

        # --- Parsowanie sekcji punktów (#~31) ---
        if in_points_section:
            if line == "P":
                i += 1
                point_id_str = lines_file[i].strip()
                point_id = int(point_id_str)

                i += 1
                coords_str = lines_file[i].strip()
                x_str, y_str, z_str = coords_str.split()
                x, y, z = float(x_str), float(y_str), float(z_str)

                points[point_id] = (x, y, z)

                # Następna linia powinna być "|~"
                i += 2  # pomijamy "|~" i przesuwamy się dalej
                continue

        # --- Parsowanie sekcji linii i łuków (#~331) ---
        if in_lines_section:
            # LIN lub ARC
            if line == "LIN":
                i += 1
                param_line = lines_file[i].strip()  # np. "1 0"
                i += 1
                points_line = lines_file[i].strip()
                start_p_str, end_p_str = points_line.split()
                start_p = int(start_p_str)
                end_p = int(end_p_str)

                lines.append((start_p, end_p))

                i += 2  # pomijamy "|~"
                continue

            elif line == "ARC":
                i += 1
                param_line = lines_file[i].strip()  # np. "1 0"
                i += 1
                arc_points_line = lines_file[i].strip()  # np. "363 364 362"
                center_str, start_str, end_str = arc_points_line.split()
                center_id = int(center_str)
                start_id = int(start_str)
                end_id   = int(end_str)

                i += 1
                direction_line = lines_file[i].strip()  # np. "-1" lub "1"
                direction = int(direction_line)

                arcs.append((center_id, start_id, end_id, direction))

                i += 2  # pomijamy "|~"
                continue

        i += 1

    return points, lines, arcs
