import math


def compute_arc_params(cx, cy, sx, sy, ex, ey, direction):
    """
    Oblicza (xc, yc, r, angle_start, angle_end) w stopniach,
    tak by łuk w DXF R12 narysować CCW od angle_start do angle_end.
    """
    vx_s = sx - cx
    vy_s = sy - cy
    vx_e = ex - cx
    vy_e = ey - cy

    r = math.hypot(vx_s, vy_s)
    a_s = math.degrees(math.atan2(vy_s, vx_s)) % 360
    a_e = math.degrees(math.atan2(vy_e, vx_e)) % 360

    if direction == 1:
        # CCW – gdy kąt końcowy jest mniejszy, dodajemy pełen obrót
        if a_e < a_s:
            a_e += 360
    else:
        # CW – zamieniamy kąty
        a_s, a_e = a_e, a_s
        if a_e < a_s:
            a_e += 360

    return (cx, cy, r, a_s, a_e)


def write_dxf(dxf_filename, points, lines, arcs, circles):
    """
    Zapisuje plik DXF (R12), ustawiając kolor (group code 62)
    zgodnie z color_idx (2 = żółty, 7 = domyślny).

    lines: [(start_p, end_p, color_idx), ...]
    arcs:  [(center_p, start_p, end_p, direction, color_idx), ...]
    circles: [(center_p, radius, color_idx), ...]   # nowa obsługa okręgów (CIR)
    """
    if circles is None:
        circles = []

    with open(dxf_filename, 'w', encoding='utf-8') as f:
        f.write("0\nSECTION\n  2\nENTITIES\n")

        # Zapis linii
        for (p1, p2, color_idx) in lines:
            x1, y1, _ = points[p1]
            x2, y2, _ = points[p2]

            f.write("  0\nLINE\n")
            f.write("  8\n0\n")  # warstwa "0"
            f.write(f" 62\n{color_idx}\n")  # ustawienie koloru
            f.write(f" 10\n{x1}\n 20\n{y1}\n")
            f.write(f" 11\n{x2}\n 21\n{y2}\n")

        # Zapis łuków
        for (center_id, start_id, end_id, direction, color_idx) in arcs:
            cx, cy, _ = points[center_id]
            sx, sy, _ = points[start_id]
            ex, ey, _ = points[end_id]

            (xc, yc, r, ang_s, ang_e) = compute_arc_params(cx, cy, sx, sy, ex, ey, direction)

            f.write("  0\nARC\n")
            f.write("  8\n0\n")  # warstwa "0"
            f.write(f" 62\n{color_idx}\n")
            f.write(f" 10\n{xc}\n 20\n{yc}\n")
            f.write(f" 40\n{r}\n")
            f.write(f" 50\n{ang_s}\n")
            f.write(f" 51\n{ang_e}\n")

        # Zapis okręgów
        for (center_id, radius, color_idx) in circles:
            cx, cy, _ = points[center_id]
            f.write("  0\nCIRCLE\n")
            f.write("  8\n0\n")  # warstwa "0"
            f.write(f" 62\n{color_idx}\n")
            f.write(f" 10\n{cx}\n 20\n{cy}\n")
            f.write(f" 40\n{radius}\n")

        f.write("  0\nENDSEC\n  0\nEOF\n")
