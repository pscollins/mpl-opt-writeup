.PHONY: all clean

PDFS := $(wildcard *_vs_*.pdf)
CSVS := $(wildcard *_vs_*.csv)

all: all_charts.pdf

all_charts.pdf: all_charts.tex $(PDFS) $(CSVS)
	pdflatex -interaction=nonstopmode all_charts.tex
	pdflatex -interaction=nonstopmode all_charts.tex

clean:
	rm -f *.aux *.log *.out *.toc *.lof *.lot *.fls *.fdb_latexmk
