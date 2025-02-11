import sys
import math
import svgwrite
from parse_geo import parse_geo
# import cairosvg


def geo_to_svg(points, lines, arcs, circles, output_filename="output.svg", margin=10):
    """
    Generuje plik SVG na podstawie danych z GEO.

    Parametry:
      - points: słownik {id: (x, y, z)}
      - lines: lista [(start_point, end_point, color_idx), ...]
      - arcs: lista [(center_point, start_point, end_point, direction, color_idx), ...]
      - circles: lista [(center_point, radius, color_idx), ...]
      - output_filename: nazwa pliku SVG (np. "thumbnail.svg")
      - margin: margines wokół rysunku
    """
    # Obliczamy granice rysunku na podstawie punktów (i elementów, które rozszerzają zakres)
    xs, ys = [], []
    for (x, y, _) in points.values():
        xs.append(x)
        ys.append(y)
    for (center_id, radius, _) in circles:
        cx, cy, _ = points.get(center_id, (0, 0, 0))
        xs.extend([cx - radius, cx + radius])
        ys.extend([cy - radius, cy + radius])
    for (center_id, start_id, end_id, _, _) in arcs:
        for pid in (center_id, start_id, end_id):
            x, y, _ = points.get(pid, (0, 0, 0))
            xs.append(x)
            ys.append(y)
    if xs and ys:
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
    else:
        min_x = min_y = 0
        max_x = max_y = 100

    width = max_x - min_x + 2 * margin
    height = max_y - min_y + 2 * margin

    # Tworzymy rysunek SVG – ustawiamy viewBox tak, aby rysunek mieścił się z marginesem
    dwg = svgwrite.Drawing(output_filename, size=(f"{width}px", f"{height}px"),
                           viewBox=f"{min_x - margin} {min_y - margin} {width} {height}")

    # Rysowanie linii
    for start_id, end_id, color_idx in lines:
        start = points.get(start_id)
        end = points.get(end_id)
        if start and end:
            color = "yellow" if color_idx in {2, 3} else "black"
            dwg.add(dwg.line(start=(start[0], start[1]), end=(end[0], end[1]),
                             stroke=color, stroke_width=1))

    # Rysowanie łuków – używamy komendy SVG "A" (arc)
    # Obliczamy kąty tak, jak w wersji DXF/matplotlib, by zachować zgodność
    for center_id, start_id, end_id, direction, color_idx in arcs:
        center = points.get(center_id)
        start = points.get(start_id)
        end = points.get(end_id)
        if center and start and end:
            # Obliczamy promień (odległość od środka do punktu startowego)
            radius = math.hypot(start[0] - center[0], start[1] - center[1])
            # Obliczamy kąty startowy i końcowy (w stopniach, zakres 0-360)
            start_angle = math.degrees(math.atan2(start[1] - center[1], start[0] - center[0])) % 360
            end_angle = math.degrees(math.atan2(end[1] - center[1], end[0] - center[0])) % 360

            # Korekta kątów w zależności od kierunku (direction: 1 = CCW, inaczej CW)
            if direction == 1:
                if end_angle < start_angle:
                    end_angle += 360
            else:
                if start_angle < end_angle:
                    start_angle += 360

            angle_range = end_angle - start_angle
            # Wyznaczamy flagi SVG: large_arc_flag = 1 gdy kąt > 180°, sweep_flag zależny od kierunku
            large_arc_flag = 1 if angle_range > 180 else 0
            sweep_flag = 1 if direction == 1 else 0  # zakładamy, że CCW daje sweep_flag = 1

            color = "yellow" if color_idx in {2, 3} else "black"
            # Tworzymy ścieżkę: zaczynamy w punkcie start, następnie komenda "A" rysuje łuk
            path_data = f"M {start[0]},{start[1]} " \
                        f"A {radius},{radius} 0 {large_arc_flag},{sweep_flag} {end[0]},{end[1]}"
            dwg.add(dwg.path(d=path_data, fill="none", stroke=color, stroke_width=1))

    # Rysowanie okręgów (opcjonalnie – jeśli mają być rysowane)
    for center_id, radius, color_idx in circles:
        center = points.get(center_id)
        if center:
            color = "yellow" if color_idx in {2, 3} else "black"
            dwg.add(dwg.circle(center=(center[0], center[1]), r=radius,
                               stroke=color, fill="none", stroke_width=1))

    dwg.save()
    print(f"SVG zapisany do pliku: {output_filename}")


def geo_to_thumbnail(geo_file, output_file="output.svg", margin=10):
    points, lines, arcs, circles = parse_geo(geo_file)
    geo_to_svg(points, lines, arcs, circles, output_filename=output_file, margin=margin)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python geo_to_thumbnail.py <plik.geo> <output.svg>")
        sys.exit(1)
    geo_file = sys.argv[1]
    output_file = sys.argv[2]
    geo_to_thumbnail(geo_file, output_file)

    # cairosvg.svg2png(url='output.svg', write_to='output.png')