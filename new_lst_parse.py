import re
import math
import xml.etree.ElementTree as ET


def parse_gcode_block(lst_filename):
    """
    Parsuje plik LST, szukając bloku START_TEXT/STOP_TEXT w sekcji PROGRAMM.
    Wyodrębnia kontury cięcia – każdy blok między TC_LASER_ON a TC_LASER_OFF traktowany jest jako jeden kontur.
    Zwraca listę konturów – każdy kontur to lista punktów (x, y).
    """
    with open(lst_filename, 'r', encoding='cp1250') as f:
        lines = f.readlines()

    in_text = False
    gcode_lines = []
    for line in lines:
        line = line.strip()
        if "START_TEXT" in line:
            in_text = True
            continue
        if "STOP_TEXT" in line:
            in_text = False
            break
        if in_text:
            gcode_lines.append(line)

    mode_incremental = True
    contours = []
    current_contour = []
    current_pos = (0.0, 0.0)

    regex_cmd = re.compile(r'G(\d+\.?\d*)')
    regex_coord = re.compile(r'([XYIJ])([-+]?[0-9]*\.?[0-9]+)')
    regex_laser_on = re.compile(r'TC_LASER_ON')
    regex_laser_off = re.compile(r'TC_LASER_OFF')
    regex_mode = re.compile(r'G(90|91)')

    def approximate_arc(start, end, i_offset, j_offset, is_clockwise, steps=10):
        cx = start[0] + i_offset
        cy = start[1] + j_offset
        r = math.hypot(i_offset, j_offset)
        start_ang = math.atan2(start[1] - cy, start[0] - cx)
        end_ang = math.atan2(end[1] - cy, end[0] - cx)
        if is_clockwise:
            if end_ang > start_ang:
                end_ang -= 2 * math.pi
        else:
            if end_ang < start_ang:
                end_ang += 2 * math.pi
        points = []
        for step in range(steps):
            t = step / (steps - 1)
            ang = start_ang + t * (end_ang - start_ang)
            x = cx + r * math.cos(ang)
            y = cy + r * math.sin(ang)
            points.append((x, y))
        return points

    for line in gcode_lines:
        m = regex_mode.search(line)
        if m:
            if m.group(1) == "90":
                mode_incremental = False
            elif m.group(1) == "91":
                mode_incremental = True

        if regex_laser_on.search(line):
            if current_contour:
                contours.append(current_contour)
                current_contour = []
            continue
        if regex_laser_off.search(line):
            if current_contour:
                contours.append(current_contour)
                current_contour = []
            continue

        cmd_match = regex_cmd.search(line)
        if not cmd_match:
            continue
        cmd = float(cmd_match.group(1))
        params = {match.group(1): float(match.group(2)) for match in regex_coord.finditer(line)}
        if cmd in [0.0, 1.0]:  # ruch liniowy
            new_x = current_pos[0]
            new_y = current_pos[1]
            if 'X' in params:
                new_x = params['X'] + (current_pos[0] if mode_incremental else 0)
            if 'Y' in params:
                new_y = params['Y'] + (current_pos[1] if mode_incremental else 0)
            current_pos = (new_x, new_y)
            current_contour.append(current_pos)
        elif cmd in [2.0, 3.0]:  # ruch łukowy
            if 'X' in params or 'Y' in params:
                new_x = current_pos[0]
                new_y = current_pos[1]
                if 'X' in params:
                    new_x = params['X'] + (current_pos[0] if mode_incremental else 0)
                if 'Y' in params:
                    new_y = params['Y'] + (current_pos[1] if mode_incremental else 0)
                end_point = (new_x, new_y)
            else:
                continue
            i_offset = params.get('I', 0.0)
            j_offset = params.get('J', 0.0)
            arc_points = approximate_arc(current_pos, end_point, i_offset, j_offset, is_clockwise=(cmd == 2.0),
                                         steps=10)
            current_contour.extend(arc_points[1:])
            current_pos = end_point
    if current_contour:
        contours.append(current_contour)
    return contours


def detect_circle(contour, tol=0.05):
    """
    Sprawdza, czy dany kontur można aproksymować jako okrąg.
    Oblicza środek jako średnią punktów i promień jako średnią odległość.
    Jeśli maksymalny względny błąd (odchylenie od średniej) nie przekracza tol,
    zwraca (center_x, center_y, radius), w przeciwnym razie zwraca None.
    """
    if len(contour) < 5:
        return None
    xs = [p[0] for p in contour]
    ys = [p[1] for p in contour]
    center_x = sum(xs) / len(xs)
    center_y = sum(ys) / len(ys)
    distances = [math.hypot(x - center_x, y - center_y) for x, y in contour]
    avg_r = sum(distances) / len(distances)
    max_dev = max(abs(r - avg_r) for r in distances)
    if avg_r == 0:
        return None
    if max_dev / avg_r < tol:
        return (center_x, center_y, avg_r)
    return None


def generate_svg_from_contours(contours, svg_filename):
    """
    Generuje plik SVG na podstawie listy konturów.
    Jeśli mamy więcej niż jeden kontur, przyjmujemy, że pierwszy to obrys zewnętrzny,
    a kolejne to otwory. Dla każdego konturu sprawdzamy, czy aproksymuje on okrąg,
    a jeśli tak – generujemy element <circle>.
    W przeciwnym razie łączymy wszystkie kontury w jeden element <path> z fill-rule="evenodd".
    """
    if not contours:
        print("Brak ścieżek cięcia do generacji SVG!")
        return

    # Ustal bounding box dla wszystkich punktów
    all_x = []
    all_y = []
    for path in contours:
        for (x, y) in path:
            all_x.append(x)
            all_y.append(y)
    min_x, min_y = min(all_x), min(all_y)
    max_x, max_y = max(all_x), max(all_y)
    svg_width = max_x - min_x
    svg_height = max_y - min_y

    svg = ET.Element("svg", xmlns="http://www.w3.org/2000/svg",
                     version="1.1", width=str(svg_width), height=str(svg_height))

    # Lista elementów SVG, zaczynamy od obrysu zewnętrznego i potem dodajemy otwory
    # Jeśli detalu mamy więcej niż jeden kontur, przyjmujemy, że pierwszy jest obrysem.
    # Jeśli kontur da się aproksymować jako okrąg, tworzymy <circle>.
    external = None
    holes = []
    if contours:
        external = contours[0]
        for inner in contours[1:]:
            holes.append(inner)

    # Funkcja do przesunięcia konturu
    def shift_contour(contour):
        return [(x - min_x, y - min_y) for (x, y) in contour]

    d_total = ""
    # Obrys zewnętrzny – generujemy ścieżkę
    if external:
        ext = shift_contour(external)
        d_ext = "M " + " L ".join(f"{x:.3f} {y:.3f}" for (x, y) in ext) + " Z "
        d_total += d_ext

    # Dla każdego otworu – jeśli otwór to okrąg, dodajemy <circle>, inaczej do ścieżki
    circle_elements = []
    path_holes = ""
    for hole in holes:
        hole_shifted = shift_contour(hole)
        circ = detect_circle(hole_shifted)
        if circ:
            cx, cy, r = circ
            # Utwórz element <circle>
            circle_el = ET.Element("circle", cx=f"{cx:.3f}", cy=f"{cy:.3f}", r=f"{r:.3f}",
                                   fill="none", stroke="black", style="stroke-width:1;")
            circle_elements.append(circle_el)
        else:
            d_hole = "M " + " L ".join(f"{x:.3f} {y:.3f}" for (x, y) in hole_shifted) + " Z "
            path_holes += d_hole

    # Jeśli mamy jakiekolwiek ścieżki (obrys i ewentualne nieokrągłe otwory)
    if d_total or path_holes:
        combined_d = d_total + path_holes
        ET.SubElement(svg, "path", d=combined_d, fill="none", stroke="black",
                      style="stroke-width:1;", **{"fill-rule": "evenodd"})
    # Dodajemy okrągłe otwory jako oddzielne elementy
    for ce in circle_elements:
        svg.append(ce)

    tree = ET.ElementTree(svg)
    tree.write(svg_filename, encoding="utf-8", xml_declaration=True)
    print("SVG zapisane jako:", svg_filename)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Użycie: python new_lst_parse.py <input.lst> <output.svg>")
        sys.exit(1)
    lst_file = sys.argv[1]
    svg_file = sys.argv[2]
    contours = parse_gcode_block(lst_file)
    print(f"Znaleziono {len(contours)} konturów cięcia.")
    generate_svg_from_contours(contours, svg_file)
