import sys
from parse_geo import parse_geo
from write_dxf import write_dxf

def geo_to_dxf(geo_file, dxf_file):
    """
    Konwertuje plik GEO do DXF.
    Kolor linii ustalany jest na podstawie parametrów z pliku GEO:
      - Jeśli linia ma w parametrach token '2' lub '3' (np. "3 0"),
        to traktujemy ją jako grawer (kolor żółty, czyli 2).
      - W przeciwnym wypadku kolor domyślny wynosi 7.
    """
    points, lines, arcs, circles = parse_geo(geo_file)
    write_dxf(dxf_file, points, lines, arcs, circles)
    print(f"Plik GEO '{geo_file}' został skonwertowany do '{dxf_file}'.")

def main():
    if len(sys.argv) < 3:
        print("Użycie: python main.py <plik.geo> <plik.dxf>")
        sys.exit(1)

    geo_file = sys.argv[1]
    dxf_file = sys.argv[2]
    geo_to_dxf(geo_file, dxf_file)

if __name__ == "__main__":
    main()
