# Total War: Attila Map

A website builder for Total War: Attila which can render regions and some details on hover.

Currently only the mod [Fireforged Empire](https://late-roman.ru/fireforged-empire/) is available to view.

## Notes

- The `data\_rex_start_pos_regions_to_unit_resources.csv` is extracted from the `campaigns/main_attila/startpos.esf` file.

## Local debugging

If you have Python installed, open a terminal or PowerShell in your project folder:

```ps
cd .\docs\
python -m http.server 8000
```

Then open your browser to: <http://localhost:8000>
