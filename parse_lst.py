import re
import math


def parse_lst(lst_filename):
    """
    Parsuje plik LST (kodowanie cp1250) i wyodrębnia geometrię ścieżki cięcia
    z pierwszego bloku START_TEXT ... STOP_TEXT.

    Przyjmujemy:
      - G90/G91 ustawiają tryb pozycji (domyślnie absolutny, ale w naszym przykładzie pojawia się G91).
      - Jeśli linia zawiera X i/lub Y, a nie ma jawnej komendy G, zakładamy ruch liniowy (G01).
      - Polecenia TC_LASER_ON – sprawdzamy parametry; jeśli zawierają "2" lub "3", ustawiamy kolor na 2 (grawerka),
        w przeciwnym razie kolor pozostaje 7 (cięcie).

    Na końcu, jeśli ostatni punkt różni się od pierwszego, dodajemy jeden segment łączący ostatni punkt z pierwszym.

    Zwracane są:
      - points: słownik {id: (x, y, z)}
      - lines: lista [(p_start, p_end, color_idx), ...]
      - arcs:  lista [(p_center, p_start, p_end, direction, color_idx), ...]
      - circles: lista – pozostaje pusta.
    """
    # Wczytujemy cały plik z kodowaniem cp1250
    with open(lst_filename, 'r', encoding='cp1250') as f:
        all_lines = f.readlines()

    # Pobieramy tylko pierwszy blok START_TEXT ... STOP_TEXT
    in_block = False
    gcode_lines = []
    for line in all_lines:
        line = line.rstrip('\n')
        if "START_TEXT" in line:
            in_block = True
            continue
        if "STOP_TEXT" in line and in_block:
            break  # przetwarzamy tylko pierwszy blok
        if in_block:
            gcode_lines.append(line.strip())

    # Inicjujemy stan parsera
    current_mode = 'absolute'  # domyślnie
    last_motion = None  # ostatnia komenda ruchu (G01, G02, G03)
    current_pos = [0.0, 0.0]
    points = {}
    lines_geom = []
    arcs_geom = []
    circles_geom = []
    point_id_counter = 1

    # Dodajemy punkt początkowy – zakładamy, że początkowa pozycja to (0,0)
    points[point_id_counter] = (current_pos[0], current_pos[1], 0.0)
    first_point_id = point_id_counter
    last_point_id = point_id_counter
    point_id_counter += 1

    current_color = 7  # domyślny kolor: cięcie

    # Wzorzec do wyłapywania tokenów (G, X, Y, I, J)
    token_pattern = re.compile(r'([A-Z])([-+]?[0-9]*\.?[0-9]+)', re.IGNORECASE)

    for line in gcode_lines:
        # Pomijamy linie zawierające komunikaty (np. MSG)
        if "MSG(" in line:
            continue

        # Obsługa poleceń laserowych
        if "TC_LASER_ON" in line:
            m = re.search(r'TC_LASER_ON\((.*?)\)', line)
            if m:
                params = m.group(1)
                # Parametry dzielone są przecinkami lub spacjami
                tokens_param = re.split(r'[,\s]+', params)
                if '2' in tokens_param or '3' in tokens_param:
                    current_color = 2
                else:
                    current_color = 7
            continue  # nie traktujemy tej linii jako ruchu
        if "TC_LASER_OFF" in line:
            current_color = 7
            continue

        # Pobieramy tokeny – ignorujemy numery linii (N...)
        tokens = token_pattern.findall(line)
        tokens = [(letter.upper(), num) for letter, num in tokens]

        # Ustalamy, czy w linii jest komenda G
        motion_cmd = None
        for letter, num in tokens:
            if letter == 'G':
                if num == '90':
                    current_mode = 'absolute'
                elif num == '91':
                    current_mode = 'incremental'
                elif num in ['0', '00', '1', '01']:
                    motion_cmd = 'G01'
                elif num in ['2', '02']:
                    motion_cmd = 'G02'
                elif num in ['3', '03']:
                    motion_cmd = 'G03'
        # Jeśli nie ma jawnej komendy G, ale są współrzędne – zakładamy ruch liniowy
        if motion_cmd is None:
            if any(letter in ['X', 'Y'] for letter, num in tokens):
                motion_cmd = 'G01'
        if motion_cmd:
            last_motion = motion_cmd
        else:
            motion_cmd = last_motion
        if motion_cmd is None:
            continue  # pomijamy linię, jeśli nie udało się ustalić komendy ruchu

        # Pobieramy parametry X, Y, I, J (jeśli występują)
        x_val = None
        y_val = None
        i_val = 0.0
        j_val = 0.0
        for letter, num in tokens:
            if letter == 'X':
                try:
                    x_val = float(num)
                except:
                    pass
            elif letter == 'Y':
                try:
                    y_val = float(num)
                except:
                    pass
            elif letter == 'I':
                try:
                    i_val = float(num)
                except:
                    pass
            elif letter == 'J':
                try:
                    j_val = float(num)
                except:
                    pass

        # Przetwarzamy ruch – w trybie incremental (G91) zgodnie z przykładem
        if motion_cmd == 'G01':
            # Jeśli brak X i Y, pomijamy
            if x_val is None and y_val is None:
                continue
            new_x = current_pos[0]
            new_y = current_pos[1]
            if x_val is not None:
                new_x = x_val if current_mode == 'absolute' else current_pos[0] + x_val
            if y_val is not None:
                new_y = y_val if current_mode == 'absolute' else current_pos[1] + y_val
            points[point_id_counter] = (new_x, new_y, 0.0)
            new_point_id = point_id_counter
            point_id_counter += 1
            lines_geom.append((last_point_id, new_point_id, current_color))
            current_pos = [new_x, new_y]
            last_point_id = new_point_id

        elif motion_cmd in ['G02', 'G03']:
            new_x = current_pos[0]
            new_y = current_pos[1]
            if x_val is not None:
                new_x = x_val if current_mode == 'absolute' else current_pos[0] + x_val
            if y_val is not None:
                new_y = y_val if current_mode == 'absolute' else current_pos[1] + y_val
            # Dla łuku środek obliczamy jako bieżący punkt + (I, J)
            center_x = current_pos[0] + i_val
            center_y = current_pos[1] + j_val
            points[point_id_counter] = (center_x, center_y, 0.0)
            center_id = point_id_counter
            point_id_counter += 1
            points[point_id_counter] = (new_x, new_y, 0.0)
            new_point_id = point_id_counter
            point_id_counter += 1
            # Przyjmujemy: G03 = CCW (direction = 1), G02 = CW (direction = 0)
            direction = 1 if motion_cmd == 'G03' else 0
            arcs_geom.append((center_id, last_point_id, new_point_id, direction, current_color))
            current_pos = [new_x, new_y]
            last_point_id = new_point_id

    # Jeśli kontur nie jest zamknięty, dodajemy jeden segment łączący ostatni punkt z pierwszym.
    first_pt = points[first_point_id]
    last_pt = points[last_point_id]
    if abs(first_pt[0] - last_pt[0]) > 1e-6 or abs(first_pt[1] - last_pt[1]) > 1e-6:
        lines_geom.append((last_point_id, first_point_id, current_color))

    return points, lines_geom, arcs_geom, circles_geom


def compute_arc_params(cx, cy, sx, sy, ex, ey, direction):
    """
    Oblicza parametry łuku do zapisu w DXF:
      - (cx, cy): środek łuku,
      - r: promień,
      - ang_s, ang_e: kąt początkowy i końcowy (w stopniach).
    """
    vx_s = sx - cx
    vy_s = sy - cy
    vx_e = ex - cx
    vy_e = ey - cy
    r = math.hypot(vx_s, vy_s)
    a_s = math.degrees(math.atan2(vy_s, vx_s)) % 360
    a_e = math.degrees(math.atan2(vy_e, vx_e)) % 360
    if direction == 1:
        if a_e < a_s:
            a_e += 360
    else:
        a_s, a_e = a_e, a_s
        if a_e < a_s:
            a_e += 360
    return (cx, cy, r, a_s, a_e)


def write_dxf(dxf_filename, points, lines, arcs, circles):
    """
    Zapisuje geometrię do pliku DXF (R12). Dla każdej linii, łuku lub okręgu
    ustawiany jest kolor (group code 62) – 2 dla grawerki, 7 domyślnie.
    """
    with open(dxf_filename, 'w', encoding='utf-8') as f:
        f.write("0\nSECTION\n  2\nENTITIES\n")
        # Zapis linii
        for (p1, p2, color_idx) in lines:
            x1, y1, _ = points[p1]
            x2, y2, _ = points[p2]
            f.write("  0\nLINE\n")
            f.write("  8\n0\n")
            f.write(f" 62\n{color_idx}\n")
            f.write(f" 10\n{x1}\n 20\n{y1}\n")
            f.write(f" 11\n{x2}\n 21\n{y2}\n")
        # Zapis łuków
        for (center_id, start_id, end_id, direction, color_idx) in arcs:
            cx, cy, _ = points[center_id]
            sx, sy, _ = points[start_id]
            ex, ey, _ = points[end_id]
            (xc, yc, r, ang_s, ang_e) = compute_arc_params(cx, cy, sx, sy, ex, ey, direction)
            f.write("  0\nARC\n")
            f.write("  8\n0\n")
            f.write(f" 62\n{color_idx}\n")
            f.write(f" 10\n{xc}\n 20\n{cy}\n")
            f.write(f" 40\n{r}\n")
            f.write(f" 50\n{ang_s}\n")
            f.write(f" 51\n{ang_e}\n")
        # Zapis okręgów (jeśli występują)
        for (center_id, radius, color_idx) in circles:
            cx, cy, _ = points[center_id]
            f.write("  0\nCIRCLE\n")
            f.write("  8\n0\n")
            f.write(f" 62\n{color_idx}\n")
            f.write(f" 10\n{cx}\n 20\n{cy}\n")
            f.write(f" 40\n{radius}\n")
        f.write("  0\nENDSEC\n  0\nEOF\n")


if __name__ == '__main__':
    lst_filename = 'example.LST'  # Podaj ścieżkę do Twojego pliku LST
    dxf_filename = 'output.dxf'
    pts, lines_geom, arcs_geom, circles_geom = parse_lst(lst_filename)
    write_dxf(dxf_filename, pts, lines_geom, arcs_geom, circles_geom)
    print("Plik DXF został wygenerowany:", dxf_filename)
