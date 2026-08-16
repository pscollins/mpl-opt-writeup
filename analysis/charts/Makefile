.PHONY: all clean

PDFS := $(wildcard *_vs_*.pdf)

all: all_charts.pdf

all_charts.pdf: all_charts.tex $(PDFS)
	pdflatex -interaction=nonstopmode all_charts.tex
	pdflatex -interaction=nonstopmode all_charts.tex

clean:
	rm -f *.aux *.log *.out *.toc *.lof *.lot *.fls *.fdb_latexmk
