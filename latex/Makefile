solution:
	pdflatex -shell-escape -interaction=nonstopmode solution.tex
	biber solution
	pdflatex -shell-escape -interaction=nonstopmode solution.tex
	pdflatex -shell-escape -interaction=nonstopmode solution.tex

clean:
	rm -f *.aux *.log *.out *.toc *.lof *.lot *.synctex.gz *.fls *.fdb_latexmk *.bbl *.blg *.bcf *.run.xml *.nav *.snm *.vrb *.idx *.ind *.ilg solution.pdf

.PHONY: solution clean
