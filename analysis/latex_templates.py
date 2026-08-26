"""LaTeX template definitions and rendering helpers for benchmark charts."""

from string import Template

DOCUMENT_PREAMBLE = r"""\documentclass[leqno,11pt]{article}

\usepackage{graphicx}
\usepackage{subcaption}
\usepackage[margin=1in]{geometry}
\usepackage{float}
\usepackage{hyperref}
\usepackage{cleveref}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{csvsimple}

\csvset{respect underscore}

\newcommand{\importcsv}[1]{{\scriptsize\setlength{\tabcolsep}{3pt}\csvautobooklongtable{#1}}}

\hypersetup{
  colorlinks=true,
  linkcolor=red,
  filecolor=magenta,
  urlcolor=blue,
}

\graphicspath{{./}{../charts/}{../../analysis/charts/}}

\title{Benchmark Evaluation Charts}
\author{Standalone Figure Compilation}
\date{\today}

\begin{document}

\maketitle
"""

DOCUMENT_POSTAMBLE = r"""\end{document}
"""

SECTION_TITLES = {
    'tuple': 'Tuple Flattening',
    'con': r'\texttt{ConApp} Flattening',
    'aos': 'AoS Flattening',
    'soa': 'SoA Flattening',
}

MLTON_CAPTIONS = {
    'tuple': r'Relative performance for with- vs without-\texttt{PreFlatten} on the MLton benchmark suite.',
    'con': r'Relative performance for with- vs without-\texttt{PreFlatten}, applied to \texttt{ConApp} on the MLton benchmark suite.',
    'aos': r'Relative performance for with- vs without-\texttt{ShallowFlatten}, using the AoS transformation on the MLton benchmark suite.',
    'soa': r'Relative performance for with- vs without-\texttt{ShallowFlatten}, using the SoA transformation on the MLton benchmark suite.',
}

PARALLEL_MLTON_CAPTIONS = {
    'tuple': r'Relative performance for with- vs without-\texttt{PreFlatten}, applied to tuple constructors on the \texttt{parallel-ml-bench} benchmark suite.',
    'con': r'Relative performance for with- vs without-\texttt{PreFlatten}, applied to \texttt{ConApp} on the \texttt{parallel-ml-bench} benchmark suite.',
    'aos': r'Relative performance for with- vs without-\texttt{ShallowFlatten}, using the AoS transformation on the \texttt{parallel-ml-bench} benchmark suite.',
    'soa': r'Relative performance for with- vs without-\texttt{ShallowFlatten}, using the SoA transformation on the \texttt{parallel-ml-bench} benchmark suite.',
}

PARALLEL_MPL_CAPTIONS = {
    'tuple': r'Relative performance for with- vs without-\texttt{PreFlatten}, applied to tuple constructors on the \texttt{parallel-ml-bench} benchmark suite, for the MPL compiler, at a variety of core counts.',
    'con': r'Relative performance for with- vs without-\texttt{PreFlatten}, applied to \texttt{ConApp} on the \texttt{parallel-ml-bench} benchmark suite, for the MPL compiler, at a variety of core counts.',
    'aos': r'Relative performance for with- vs without-\texttt{ShallowFlatten}, using the AoS transformation on the \texttt{parallel-ml-bench} benchmark suite, for the MPL compiler, at a variety of core counts.',
    'soa': r'Relative performance for with- vs without-\texttt{ShallowFlatten}, using the SoA transformation on the \texttt{parallel-ml-bench} benchmark suite, for the MPL compiler, at a variety of core counts.',
}

MLTON_SUBSECTION_TEMPLATE = r"""\subsection{MLton Benchmarks (${test_type})}

\begin{figure}[H]
  \centering
  \begin{subfigure}[b]{0.32\textwidth}
    \centering
    \includegraphics[width=\textwidth]{${t}_mlton_run_mlton_vs_mlton.pdf}
    \caption{Run time}
    \label{fig:${t}_mlton_run_mlton_vs_mlton}
  \end{subfigure}
  \hfill
  \begin{subfigure}[b]{0.32\textwidth}
    \centering
    \includegraphics[width=\textwidth]{${t}_mlton_compile_mlton_vs_mlton.pdf}
    \caption{Compile time}
    \label{fig:${t}_mlton_compile_mlton_vs_mlton}
  \end{subfigure}
  \hfill
  \begin{subfigure}[b]{0.32\textwidth}
    \centering
    \includegraphics[width=\textwidth]{${t}_mlton_size_mlton_vs_mlton.pdf}
    \caption{Binary size}
    \label{fig:${t}_mlton_size_mlton_vs_mlton}
  \end{subfigure}
  \caption{${caption}}
  \label{fig:${t}_mlton}
\end{figure}
"""

PARALLEL_BENCH_MLTON_SUBSECTION_TEMPLATE = r"""\subsection{\texttt{parallel-ml-bench}: MLton vs MLton (${test_type})}

\begin{figure}[H]
  \centering
  \begin{subfigure}[b]{0.48\textwidth}
    \centering
    \includegraphics[width=\textwidth]{${t}_parallel_bench_run_mlton_vs_mlton.pdf}
    \caption{Run time}
    \label{fig:${t}_parallel_bench_run_mlton_vs_mlton}
  \end{subfigure}
  \hfill
  \begin{subfigure}[b]{0.48\textwidth}
    \centering
    \includegraphics[width=\textwidth]{${t}_parallel_bench_size_mlton_vs_mlton.pdf}
    \caption{Binary size}
    \label{fig:${t}_parallel_bench_size_mlton_vs_mlton}
  \end{subfigure}
  \caption{${caption}}
  \label{fig:${t}_parallel_bench}
\end{figure}
"""

PARALLEL_BENCH_MPL_SUBSECTION_TEMPLATE = r"""\subsection{\texttt{parallel-ml-bench}: MPL vs MPL (${test_type})}

\begin{figure}[H]
  \centering
  \begin{subfigure}[b]{0.48\textwidth}
    \centering
    \includegraphics[width=\textwidth]{${t}_parallel_bench_run_mpl_vs_mpl.pdf}
    \caption{Run time}
    \label{fig:${t}_parallel_bench_run_mpl_vs_mpl}
  \end{subfigure}
  \hfill
  \begin{subfigure}[b]{0.48\textwidth}
    \centering
    \includegraphics[width=\textwidth]{${t}_parallel_bench_size_mpl_vs_mpl.pdf}
    \caption{Binary size}
    \label{fig:${t}_parallel_bench_size_mpl_vs_mpl}
  \end{subfigure}
  \caption{${caption}}
  \label{fig:${t}_parallel_bench_mpl}
\end{figure}

\begin{figure}[H]
  \centering
  \includegraphics[width=\textwidth,height=0.88\textheight,keepaspectratio]{${t}_parallel_bench_run_mpl_vs_mpl_geomean.pdf}
  \caption{${caption}}
  \label{fig:${t}_parallel_bench_mpl_geomean}
\end{figure}

\begin{figure}[H]
  \centering
  \includegraphics[width=\textwidth,height=0.88\textheight,keepaspectratio]{${t}_parallel_bench_run_mpl_vs_mpl_trellis.pdf}
  \caption{${caption}}
  \label{fig:${t}_parallel_bench_mpl_trellis}
\end{figure}
"""

MLTON_TABLES_TEMPLATE = r"""\subsubsection{MLton Benchmarks (${test_type})}

\paragraph*{Run time}
\importcsv{${t}_mlton_run_mlton_vs_mlton.csv}

\paragraph*{Compile time}
\importcsv{${t}_mlton_compile_mlton_vs_mlton.csv}

\paragraph*{Binary size}
\importcsv{${t}_mlton_size_mlton_vs_mlton.csv}
"""

PARALLEL_BENCH_MLTON_TABLES_TEMPLATE = r"""\subsubsection{\texttt{parallel-ml-bench}: MLton vs MLton (${test_type})}

\paragraph*{Run time}
\importcsv{${t}_parallel_bench_run_mlton_vs_mlton.csv}

\paragraph*{Binary size}
\importcsv{${t}_parallel_bench_size_mlton_vs_mlton.csv}
"""

PARALLEL_BENCH_MPL_TABLES_TEMPLATE = r"""\subsubsection{\texttt{parallel-ml-bench}: MPL vs MPL (${test_type})}

\paragraph*{Run time}
\importcsv{${t}_parallel_bench_run_mpl_vs_mpl.csv}

\paragraph*{Binary size}
\importcsv{${t}_parallel_bench_size_mpl_vs_mpl.csv}
"""

TRIAL_SCATTER_SUBSECTION_TEMPLATE = r"""\subsection{${bench_display} (${context_desc})}

\begin{figure}[H]
  \centering
  \includegraphics[width=\textwidth,keepaspectratio]{${out_filename}.pdf}
  \caption{${caption}}
  \label{fig:${out_filename}}
\end{figure}
"""

TRIAL_SCATTER_TABLES_TEMPLATE = r"""\subsubsection{${bench_display} (${context_desc})}

\importcsv{${out_filename}.csv}
"""


def format_caption(base_caption: str, data_file: str) -> str:
    return fr'{base_caption} Data: \protect\nolinkurl{{{data_file}}}. <0\% represents an improvement, >0\% represents a regression.'


def render_mlton_subsection(t: str, data_file: str) -> str:
    test_type = SECTION_TITLES.get(t, f'{t.capitalize()} Flattening')
    base_cap = MLTON_CAPTIONS.get(t, fr'Relative performance for \texttt{{{t}}} on the MLton benchmark suite.')
    cap = format_caption(base_cap, data_file)
    return Template(MLTON_SUBSECTION_TEMPLATE).substitute(t=t, test_type=test_type, caption=cap)


def render_parallel_bench_mlton_subsection(t: str, data_file: str) -> str:
    test_type = SECTION_TITLES.get(t, f'{t.capitalize()} Flattening')
    base_cap = PARALLEL_MLTON_CAPTIONS.get(t, fr'Relative performance for \texttt{{{t}}} on the \texttt{{parallel-ml-bench}} benchmark suite.')
    cap = format_caption(base_cap, data_file)
    return Template(PARALLEL_BENCH_MLTON_SUBSECTION_TEMPLATE).substitute(t=t, test_type=test_type, caption=cap)


def render_parallel_bench_mpl_subsection(t: str, data_file: str) -> str:
    test_type = SECTION_TITLES.get(t, f'{t.capitalize()} Flattening')
    base_cap = PARALLEL_MPL_CAPTIONS.get(t, fr'Relative performance for \texttt{{{t}}} on the \texttt{{parallel-ml-bench}} benchmark suite, for the MPL compiler, at a variety of core counts.')
    cap = format_caption(base_cap, data_file)
    return Template(PARALLEL_BENCH_MPL_SUBSECTION_TEMPLATE).substitute(t=t, test_type=test_type, caption=cap)


def render_mlton_tables_subsection(t: str) -> str:
    test_type = SECTION_TITLES.get(t, f'{t.capitalize()} Flattening')
    return Template(MLTON_TABLES_TEMPLATE).substitute(t=t, test_type=test_type)


def render_parallel_bench_mlton_tables_subsection(t: str) -> str:
    test_type = SECTION_TITLES.get(t, f'{t.capitalize()} Flattening')
    return Template(PARALLEL_BENCH_MLTON_TABLES_TEMPLATE).substitute(t=t, test_type=test_type)


def render_parallel_bench_mpl_tables_subsection(t: str) -> str:
    test_type = SECTION_TITLES.get(t, f'{t.capitalize()} Flattening')
    return Template(PARALLEL_BENCH_MPL_TABLES_TEMPLATE).substitute(t=t, test_type=test_type)


def render_trial_scatter_subsection(out_filename: str, bench: str, data_file: str, compiler: str = 'mlton', suite: str = 'parallel_bench', exp_type: str = 'tuple') -> str:
    bench_display = fr'\texttt{{{bench}}}'
    test_type = SECTION_TITLES.get(exp_type, f'{exp_type.capitalize()} Flattening')
    suite_name = r'\texttt{parallel-ml-bench}' if suite == 'parallel_bench' else suite
    compiler_display = 'MLton' if compiler.lower() == 'mlton' else ('MPL' if compiler.lower() == 'mpl' else compiler.capitalize())
    context_desc = fr'{suite_name}: {compiler_display} ({test_type})' if compiler else f'{suite_name} ({test_type})'
    caption = fr'Per-trial execution times for \texttt{{{bench}}} on the {suite_name} benchmark suite. Data: \protect\nolinkurl{{{data_file}}}.'
    return Template(TRIAL_SCATTER_SUBSECTION_TEMPLATE).substitute(
        bench_display=bench_display,
        context_desc=context_desc,
        out_filename=out_filename,
        caption=caption,
    )


def render_trial_scatter_tables_subsection(out_filename: str, bench: str, compiler: str = 'mlton', suite: str = 'parallel_bench', exp_type: str = 'tuple') -> str:
    bench_display = fr'\texttt{{{bench}}}'
    test_type = SECTION_TITLES.get(exp_type, f'{exp_type.capitalize()} Flattening')
    suite_name = r'\texttt{parallel-ml-bench}' if suite == 'parallel_bench' else suite
    compiler_display = 'MLton' if compiler.lower() == 'mlton' else ('MPL' if compiler.lower() == 'mpl' else compiler.capitalize())
    context_desc = fr'{suite_name}: {compiler_display} ({test_type})' if compiler else f'{suite_name} ({test_type})'
    return Template(TRIAL_SCATTER_TABLES_TEMPLATE).substitute(
        bench_display=bench_display,
        context_desc=context_desc,
        out_filename=out_filename,
    )

