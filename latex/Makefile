solution:
	pdflatex -shell-escape solution.tex
	bibtex solution.aux
	pdflatex -shell-escape solution.tex
	pdflatex -shell-escape solution.tex

clean:
	rm *.aux *.log *.out
