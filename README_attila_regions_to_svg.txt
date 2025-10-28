Usage quickstart:

1) Install deps:
   pip install opencv-python numpy

2) Run the converter (replace input path):
   python attila_regions_to_svg.py regions_map.png --outdir out --bg 0,0,0,0 --simplify 0.75 --tolerance 0 --min-area 64 --make-html

3) (Optional) Provide a color->ID mapping CSV for clean IDs and display names:
   python attila_regions_to_svg.py regions_map.png --mapping color_map.csv --make-html

Outputs:
 - out/provinces.svg
 - out/provinces.json
 - out/index.html (demo)
