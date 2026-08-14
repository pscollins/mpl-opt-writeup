solution:
	pdflatex -shell-escape solution.tex
	bibtex solution.aux
	pdflatex -shell-escape solution.tex
	pdflatex -shell-escape solution.tex

clean:
	rm -f *.aux *.log *.out *.toc *.lof *.lot *.synctex.gz *.fls *.fdb_latexmk *.bbl *.blg *.bcf *.run.xml *.nav *.snm *.vrb *.idx *.ind *.ilg

.PHONY: clean
