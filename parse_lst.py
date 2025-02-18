import re
import math


def parse_lst(lst_filename):
    """
    Parsuje sekcję START_TEXT ... STOP_TEXT z pliku LST (cp1250)
    i rejestruje wszystkie ruchy – zarówno gdy laser jest włączony (cięcie/grawerka)
    jak i gdy jest wyłączony (przejazdy). Dla ruchów z laserem wyłączonym przypisujemy kolor zielony (3).

    Zwraca: points, lines, arcs, circles
    """
    with open(lst_filename, 'r', encoding='cp1250') as f:
        all_lines = f.readlines()

    in_text = False
    gcode_lines = []
    for line in all_lines:
        line = line.strip()
        if "START_TEXT" in line:
            in_text = True
            continue
        if "STOP_TEXT" in line:
            in_text = False
            continue
        if in_text:
            gcode_lines.append(line)

    # Inicjalizacja stanu
    current_mode = 'absolute'  # domyślnie G90
    current_pos = [0.0, 0.0]  # układ arkusza – współrzędne globalne
    points = {}
    lines_geom = []
    arcs_geom = []
    circles_geom = []
    point_id_counter = 1

    # Dodajemy punkt startowy (przyjmujemy, że początek układu)
    points[point_id_counter] = (current_pos[0], current_pos[1], 0.0)
    last_point_id = point_id_counter
    point_id_counter += 1

    # Kolory – current_color dla ruchów z laserem włączonym; travel_color = 3 dla przejazdów (laser off)
    current_color = 7  # domyślnie (cięcie) lub 2 (grawerka)
    travel_color = 3
    last_command = None
    laser_on = False  # domyślnie laser wyłączony

    token_pattern = re.compile(r'([A-Z])([-+]?[0-9]*\.?[0-9]+)')

    for line in gcode_lines:
        # Obsługa komend lasera – zmiana stanu
        if "TC_LASER_ON" in line:
            m = re.search(r'TC_LASER_ON\((.*?)\)', line)
            if m:
                params_str = m.group(1)
                tokens_param = re.split(r'[,\s]+', params_str)
                # Jeśli wśród parametrów występuje '2' lub '3', ustaw kolor na 2 (grawerka),
                # w przeciwnym razie 7 (cięcie)
                if '2' in tokens_param or '3' in tokens_param:
                    current_color = 2
                else:
                    current_color = 7
            laser_on = True
            continue  # nie przetwarzamy tej linii jako ruchu

        if "TC_LASER_OFF" in line:
            laser_on = False
            continue

        # Pobieramy tokeny – ignorujemy numery linii (N...)
        tokens = token_pattern.findall(line)
        tokens = [(letter.upper(), num) for letter, num in tokens if letter.upper() != 'N']

        # Ustal komendę G
        g_cmd = None
        for letter, number in tokens:
            if letter == 'G':
                if number in ['90']:
                    current_mode = 'absolute'
                    g_cmd = 'G90'
                elif number in ['91']:
                    current_mode = 'incremental'
                    g_cmd = 'G91'
                elif number in ['0', '00']:
                    g_cmd = 'G01'  # traktujemy szybki ruch jako liniowy
                elif number in ['1', '01']:
                    g_cmd = 'G01'
                elif number in ['2', '02']:
                    g_cmd = 'G02'  # łuk
                elif number in ['3', '03']:
                    g_cmd = 'G03'
        if g_cmd:
            last_command = g_cmd
        else:
            g_cmd = last_command
        if not g_cmd:
            continue

        # Pobieramy parametry: X, Y, I, J
        x_val = None
        y_val = None
        i_val = 0.0
        j_val = 0.0
        for letter, number in tokens:
            if letter == 'X':
                x_val = float(number)
            elif letter == 'Y':
                y_val = float(number)
            elif letter == 'I':
                i_val = float(number)
            elif letter == 'J':
                j_val = float(number)

        # Obliczamy nowe współrzędne
        if current_mode == 'absolute':
            new_x = x_val if x_val is not None else current_pos[0]
            new_y = y_val if y_val is not None else current_pos[1]
        else:
            new_x = current_pos[0] + (x_val if x_val is not None else 0.0)
            new_y = current_pos[1] + (y_val if y_val is not None else 0.0)

        # Wybieramy kolor użyty dla tego ruchu
        used_color = current_color if laser_on else travel_color

        if g_cmd in ['G01', 'G00']:
            # Ruch liniowy
            points[point_id_counter] = (new_x, new_y, 0.0)
            new_point_id = point_id_counter
            point_id_counter += 1
            lines_geom.append((last_point_id, new_point_id, used_color))
            current_pos = [new_x, new_y]
            last_point_id = new_point_id

        elif g_cmd in ['G02', 'G03']:
            # Ruch łukowy – wyznaczamy punkt końcowy i środek łuku
            new_x_calc = new_x
            new_y_calc = new_y
            center_x = current_pos[0] + i_val
            center_y = current_pos[1] + j_val
            # Dodaj punkt środka
            points[point_id_counter] = (center_x, center_y, 0.0)
            center_point_id = point_id_counter
            point_id_counter += 1
            # Dodaj punkt końcowy
            points[point_id_counter] = (new_x_calc, new_y_calc, 0.0)
            new_point_id = point_id_counter
            point_id_counter += 1
            direction = 1 if g_cmd == 'G03' else 0
            arcs_geom.append((center_point_id, last_point_id, new_point_id, direction, used_color))
            current_pos = [new_x_calc, new_y_calc]
            last_point_id = new_point_id

    return points, lines_geom, arcs_geom, circles_geom


def compute_arc_params(cx, cy, sx, sy, ex, ey, direction):
    """
    Oblicza parametry łuku do DXF: (xc, yc, r, angle_start, angle_end) w stopniach.
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


def parse_sheet_contour(lst_filename):
    """
    Szuka w pliku LST linii zawierającej DA,'SHT-1' i próbuje odczytać wymiary arkusza.
    Zakładamy, że po identyfikatorze SHT-1 następują szerokość i wysokość (w mm).
    Zwraca kontur arkusza jako listę punktów:
       [(0,0), (width,0), (width,height), (0,height), (0,0)]
    lub None, jeśli nie znaleziono.
    """
    with open(lst_filename, 'r', encoding='cp1250') as f:
        lines = f.readlines()
    sheet_width = None
    sheet_height = None
    for line in lines:
        if "DA,'SHT-1'" in line:
            parts = line.strip().split(',')
            try:
                sheet_width = float(parts[2])
                sheet_height = float(parts[3])
                break
            except Exception as e:
                pass
    if sheet_width is None or sheet_height is None:
        return None
    return [(0, 0), (sheet_width, 0), (sheet_width, sheet_height), (0, sheet_height), (0, 0)]


def parse_part_position(lst_filename, detail_name):
    """
    Szuka w pliku LST sekcji BEGIN_PARTS_IN_PROGRAM_POS i próbuje odnaleźć
    pozycję detalu o nazwie detail_name.
    Zakładamy, że linia z danymi ma postać:
      DA,1,'detail_name','NOID_1',offsetX,offsetY, ...
    Zwraca offset (x, y) lub (0,0) jeśli nie znaleziono.
    """
    with open(lst_filename, 'r', encoding='cp1250') as f:
        lines = f.readlines()
    in_block = False
    for line in lines:
        if "BEGIN_PARTS_IN_PROGRAM_POS" in line:
            in_block = True
            continue
        if "ENDE_PARTS_IN_PROGRAM_POS" in line and in_block:
            in_block = False
            break
        if in_block and detail_name in line:
            # Przykładowa linia: DA,1,'test_pr100x80_1','NOID_1',10.00,10.00,...
            parts = line.strip().split(',')
            try:
                offset_x = float(parts[4])
                offset_y = float(parts[5])
                return (offset_x, offset_y)
            except Exception as e:
                return (0.0, 0.0)
    return (0.0, 0.0)


def write_dxf_with_sheet(dxf_filename, points, lines, arcs, circles, sheet_contour, part_offset):
    """
    Zapisuje plik DXF (R12) zawierający:
      - Geometrię detalu (wszystkie ruchy – zarówno cięcia, jak i przejazdy),
        przy czym geometrię przesuwamy o podany part_offset (offset detalu na arkuszu).
      - Kontur arkusza (rysowany jako POLYLINE, kolor niebieski, np. 5).

    Kolory:
      - Ruchy z laserem włączonym: kolor zgodny z rejestrowanym (7 lub 2)
      - Ruchy z laserem wyłączonym: zielony (3)
      - Kontur arkusza: niebieski (5)
    """

    # Funkcja pomocnicza: przesunięcie punktu
    def shift_point(pt, offset):
        return (pt[0] + offset[0], pt[1] + offset[1], pt[2])

    # Przesuwamy wszystkie punkty geometrii detalu
    shifted_points = {}
    for pid, pt in points.items():
        shifted_points[pid] = shift_point(pt, part_offset)

    with open(dxf_filename, 'w', encoding='cp1250') as f:
        f.write("0\nSECTION\n  2\nENTITIES\n")
        # Zapisujemy linie i łuki
        for (p1, p2, color_idx) in lines:
            x1, y1, _ = shifted_points[p1]
            x2, y2, _ = shifted_points[p2]
            f.write("  0\nLINE\n")
            f.write("  8\n0\n")
            f.write(f" 62\n{color_idx}\n")
            f.write(f" 10\n{x1}\n 20\n{y1}\n")
            f.write(f" 11\n{x2}\n 21\n{y2}\n")
        for (center_id, start_id, end_id, direction, color_idx) in arcs:
            cx, cy, _ = shifted_points[center_id]
            sx, sy, _ = shifted_points[start_id]
            ex, ey, _ = shifted_points[end_id]
            (xc, yc, r, ang_s, ang_e) = compute_arc_params(cx, cy, sx, sy, ex, ey, direction)
            f.write("  0\nARC\n")
            f.write("  8\n0\n")
            f.write(f" 62\n{color_idx}\n")
            f.write(f" 10\n{xc}\n 20\n{cy}\n")
            f.write(f" 40\n{r}\n")
            f.write(f" 50\n{ang_s}\n")
            f.write(f" 51\n{ang_e}\n")
        for (center_id, radius, color_idx) in circles:
            cx, cy, _ = shifted_points[center_id]
            f.write("  0\nCIRCLE\n")
            f.write("  8\n0\n")
            f.write(f" 62\n{color_idx}\n")
            f.write(f" 10\n{cx}\n 20\n{cy}\n")
            f.write(f" 40\n{radius}\n")
        # Zapis konturu arkusza – rysujemy POLYLINE, kolor niebieski (5)
        if sheet_contour:
            f.write("  0\nPOLYLINE\n")
            f.write("  8\n0\n")
            f.write(" 62\n5\n")
            f.write(" 66\n1\n")
            for (x, y) in sheet_contour:
                f.write("  0\nVERTEX\n")
                f.write("  8\n0\n")
                f.write(f" 10\n{x}\n 20\n{y}\n 30\n0.0\n")
            f.write("  0\nSEQEND\n")
        f.write("  0\nENDSEC\n  0\nEOF\n")


# Przykładowe użycie:
if __name__ == '__main__':
    lst_filename = 'example.LST'  # Ścieżka do pliku LST
    dxf_filename = 'output.dxf'
    # Odczyt geometrii detalu (wszystkich ruchów)
    pts, lines_geom, arcs_geom, circles_geom = parse_lst(lst_filename)
    # Odczyt konturu arkusza (np. szerokość i wysokość)
    sheet_contour = parse_sheet_contour(lst_filename)
    # Odczyt pozycji detalu – nazwa detalu wg części programu
    part_offset = parse_part_position(lst_filename, 'test_pr100x80_1')
    print("Part offset:", part_offset)
    # Zapis do DXF – geometrię detalu (przesuniętą) oraz kontur arkusza
    write_dxf_with_sheet(dxf_filename, pts, lines_geom, arcs_geom, circles_geom, sheet_contour, part_offset)
    print("Plik DXF został wygenerowany:", dxf_filename)
