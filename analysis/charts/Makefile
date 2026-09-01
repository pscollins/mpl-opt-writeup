.PHONY: all clean

PDFS := $(filter-out all_charts.pdf all_charts.old%, $(wildcard *.pdf))
CSVS := $(wildcard *.csv)

all: all_charts.pdf

all_charts.pdf: all_charts.tex $(PDFS) $(CSVS)
	pdflatex -interaction=nonstopmode all_charts.tex
	pdflatex -interaction=nonstopmode all_charts.tex

clean:
	rm -f *.aux *.log *.out *.toc *.lof *.lot *.fls *.fdb_latexmk
