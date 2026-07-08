# latexmk config for the thesis build (run from tex/): `latexmk` suffices.
$pdf_mode = 1;                      # pdflatex
$pdflatex = 'pdflatex -interaction=nonstopmode -file-line-error %O %S';
$clean_ext = 'lof lot fls fdb_latexmk synctex.gz';
@default_files = ('tese.tex');
