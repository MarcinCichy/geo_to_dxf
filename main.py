# main.py

import sys
from parse_geo import parse_geo
from write_dxf import write_dxf

def geo_to_dxf(geo_file, dxf_file):
    """
    Łączy parsowanie GEO i zapis do DXF.
    """
    points, lines = parse_geo(geo_file)
    write_dxf(dxf_file, points, lines)

    print(f"Plik GEO '{geo_file}' został skonwertowany do '{dxf_file}'.")

def main():
    """
    Główna funkcja - interpretacja argumentów z linii komend.
    Użycie: python main.py input.geo output.dxf
    """
    if len(sys.argv) < 3:
        print("Użycie: python main.py <plik.geo> <plik.dxf>")
        sys.exit(1)

    geo_file = sys.argv[1]
    dxf_file = sys.argv[2]

    geo_to_dxf(geo_file, dxf_file)

if __name__ == "__main__":
    main()
