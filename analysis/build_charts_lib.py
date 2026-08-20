import json
import os
from dataclasses import dataclass
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd

from latex_templates import (
    DOCUMENT_PREAMBLE,
    DOCUMENT_POSTAMBLE,
    SECTION_TITLES,
    render_mlton_subsection,
    render_parallel_bench_mlton_subsection,
    render_parallel_bench_mpl_subsection,
    render_mlton_tables_subsection,
    render_parallel_bench_mlton_tables_subsection,
    render_parallel_bench_mpl_tables_subsection,
)

# Use system latex
plt.rcParams.update({
    "text.usetex": True,
    "font.family": "serif",
    "font.serif": ["Computer Modern Roman"]
})

DATA_ROOT = 'data'
METADATA_KEYS = {'compiler', 'suite'}
CHECKSUM_FIELD_PARALLEL = 'binary_md5'
COMPILER_NAME_FIELD_PARALLEL = 'config'
ALLOWABLE_BASELINES = {'mlton-baseline', 'mpl-baseline'}

USE_NEW_ANALYSIS_STYLE = True


def safe_std(all_abs_ratios):
    arr = np.atleast_1d(all_abs_ratios)
    if len(arr) <= 1:
        return 0.0
    return np.std(arr, ddof=1)


def calculate_error_bars(test_rows, base_rows, n_bootstraps=10000, ci=0.95, random_state=None):
    """
    Calculates % speedup and 95% CI bounds using non-parametric bootstrapping.
    Assumes B is the baseline and A is the new configuration.
    """
    rng = np.random.default_rng(random_state)
    alpha = (1.0 - ci) / 2.0 * 100

    def _bootstrap_ci(test_trials, base_trials):
        t = np.atleast_1d(np.asarray(test_trials, dtype=float))
        b = np.atleast_1d(np.asarray(base_trials, dtype=float))
        if len(t) <= 1 or len(b) <= 1 or np.mean(b) == 0:
            return 0.0, 0.0
        boot_t = rng.choice(t, size=(n_bootstraps, len(t)), replace=True).mean(axis=1)
        boot_b = rng.choice(b, size=(n_bootstraps, len(b)), replace=True).mean(axis=1)
        boot_ratios = boot_t / boot_b
        ci_lower = np.percentile(boot_ratios, alpha)
        ci_upper = np.percentile(boot_ratios, 100 - alpha)
        point_est = np.mean(t) / np.mean(b)
        err_minus = max(0.0, float(point_est - ci_lower))
        err_plus = max(0.0, float(ci_upper - point_est))
        return err_minus, err_plus

    # Single pair of 1D trial arrays / lists
    if isinstance(test_rows, (list, np.ndarray, tuple)) and len(test_rows) > 0:
        if isinstance(test_rows[0], (int, float, np.number)):
            err_minus, err_plus = _bootstrap_ci(test_rows, base_rows)
            return [err_minus, err_plus]

    err_minus_list = []
    err_plus_list = []
    for t_row, b_row in zip(test_rows, base_rows):
        em, ep = _bootstrap_ci(t_row, b_row)
        err_minus_list.append(em)
        err_plus_list.append(ep)

    if isinstance(test_rows, pd.Series):
        err_minus = pd.Series(err_minus_list, index=test_rows.index)
        err_plus = pd.Series(err_plus_list, index=test_rows.index)
    else:
        err_minus = np.array(err_minus_list)
        err_plus = np.array(err_plus_list)

    return [err_minus, err_plus]


def infer_configs(df, abbrevs=None):
    if abbrevs is not None:
        return abbrevs[0], abbrevs[1]
    configs = set(df[COMPILER_NAME_FIELD_PARALLEL].dropna().unique())
    baselines = [c for c in configs if c in ALLOWABLE_BASELINES]
    if len(baselines) == 1:
        base_key = baselines[0]
        test_keys = [c for c in configs if c != base_key]
        if len(test_keys) == 1:
            return base_key, test_keys[0]
        else:
            raise ValueError(f"Expected exactly 1 test configuration after removing '{base_key}', found {len(test_keys)}: {test_keys}")
    else:
        raise ValueError(f"Could not find a unique valid baseline from {ALLOWABLE_BASELINES} in configurations: {configs}")


# Plots data from the parallel-ml-bench suite
def plot_parallel_bench(df, values='test_results_secs', title='', out_filename='', abbrevs=None, out_dir='charts', use_new_analysis_style=USE_NEW_ANALYSIS_STYLE):
    base_key, test_key = infer_configs(df, abbrevs)

    # Remove columns we don't care about
    filtered = df[['bench', COMPILER_NAME_FIELD_PARALLEL, values, CHECKSUM_FIELD_PARALLEL]]
    filtered = filtered[filtered[COMPILER_NAME_FIELD_PARALLEL].isin([base_key, test_key])]
    # Remove benchmarks with identical binaries
    filtered = filtered[filtered.groupby('bench')[CHECKSUM_FIELD_PARALLEL].transform('nunique') > 1]
    if filtered.empty:
        print("No benchmarks with differing binary hash found.")
        return

    # Drop older duplicate runs before pivoting
    filtered = filtered.drop_duplicates(subset=['bench', COMPILER_NAME_FIELD_PARALLEL], keep='last')

    pivot = filtered.pivot(index='bench', columns=COMPILER_NAME_FIELD_PARALLEL, values=values)
    pivot = pivot.dropna(subset=[base_key, test_key])
    if pivot.empty:
        print("No matching benchmark runs found for comparison.")
        return

    if use_new_analysis_style:
        mean_abs_ratios = pivot.apply(
            lambda row: np.mean(row[test_key]) / np.mean(row[base_key]),
            axis=1
        )
        err_minus, err_plus = calculate_error_bars(pivot[test_key], pivot[base_key])
        err_minus_pct = np.asarray(err_minus) * 100
        err_plus_pct = np.asarray(err_plus) * 100
        relative_pct = (mean_abs_ratios - 1) * 100

        results_df = pd.DataFrame({
            'bench': pivot.index,
            'relative_pct': relative_pct.values,
            'err_minus_pct': err_minus_pct,
            'err_plus_pct': err_plus_pct,
        }).round(3)

        yerr = np.vstack([err_minus_pct, err_plus_pct])
        ax = relative_pct.plot(kind='bar', yerr=yerr)
    else:
        # Calculate the ratio (<1 is good, >1 is bad) between pairs of trials
        all_abs_ratios = pivot.apply(lambda row:
                                  np.array(row[test_key]) / np.array(row[base_key]),
                                  axis=1)
        mean_abs_ratios = all_abs_ratios.apply(np.mean)
        std_abs_ratios = all_abs_ratios.apply(safe_std)
        # Convert to relative_pct (<0% is good, >0% is bad)
        relative_pct = (mean_abs_ratios - 1) * 100
        std_pct = std_abs_ratios * 100

        results_df = pd.DataFrame({
            'bench': pivot.index,
            'relative_pct': relative_pct.values,
            'std_pct': std_pct.values,
        }).round(3)

        ax = relative_pct.plot(kind='bar',
                               yerr=std_abs_ratios)

    # Calculate the absolute geomean (1.0 is neutral)
    abs_geomean = np.exp(np.mean(np.log(mean_abs_ratios.dropna())))
    # Scale to match the metric for relative_pct
    geomean_pct = (abs_geomean - 1) * 100
    # Add a text box
    textstr = fr'Geomean: {geomean_pct:+.1f}\%'
    props = dict(boxstyle='square,pad=0.5', facecolor='white', alpha=0.9, edgecolor='black', linewidth=0.5)
    ax.text(0.95, 0.95, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', horizontalalignment='right', bbox=props)
    
    ax.set_title(title)
    ax.set_xlabel('Benchmark name')
    ax.set_ylabel(r'Relative \% $\frac{\mathrm{test}}{\mathrm{base}} - 1 \times 100\%$')
    ax.yaxis.set_major_formatter(ticker.PercentFormatter())
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, f'{out_filename}.csv')
    print(f'Saving data to {csv_path}')
    results_df.to_csv(csv_path, index=False)
    path = os.path.join(out_dir, f'{out_filename}.pdf')
    print(f'Saving chart to {path}')
    plt.savefig(path, format='pdf', bbox_inches='tight', metadata={'CreationDate': None})
    plt.close()


# Plots run time data across core counts (procs) from the parallel-ml-bench suite
def plot_parallel_bench_cores(df, values='test_results_secs', title='', out_filename='', abbrevs=None, out_dir='charts', use_new_analysis_style=USE_NEW_ANALYSIS_STYLE):
    # 1. Find the benchmarks where the compiled binary has a differing hash
    filtered = df[df.groupby('bench')[CHECKSUM_FIELD_PARALLEL].transform('nunique') > 1]
    if filtered.empty:
        print("No benchmarks with differing binary hash found.")
        return

    base_key, test_key = infer_configs(filtered, abbrevs)
    filtered = filtered[filtered[COMPILER_NAME_FIELD_PARALLEL].isin([base_key, test_key])]
    
    # 2. Among benchmarks with a differing hash, collect all runs according to their core-count ("procs")
    filtered = filtered.drop_duplicates(subset=['bench', 'procs', COMPILER_NAME_FIELD_PARALLEL], keep='last')
    pivot = filtered.pivot(index=['bench', 'procs'], columns=COMPILER_NAME_FIELD_PARALLEL, values=values)
    pivot = pivot.dropna(subset=[base_key, test_key])
    if pivot.empty:
        print("No matching benchmark runs found for comparison.")
        return

    if use_new_analysis_style:
        mean_abs_ratios = pivot.apply(
            lambda row: np.mean(row[test_key]) / np.mean(row[base_key]),
            axis=1
        )
        err_minus, err_plus = calculate_error_bars(pivot[test_key], pivot[base_key])
        err_minus_pct = np.asarray(err_minus) * 100
        err_plus_pct = np.asarray(err_plus) * 100
        relative_pct = (mean_abs_ratios.values - 1) * 100

        results_df = pd.DataFrame({
            'bench': [idx[0] for idx in pivot.index],
            'procs': [idx[1] for idx in pivot.index],
            'relative_pct': relative_pct,
            'err_minus_pct': err_minus_pct,
            'err_plus_pct': err_plus_pct,
        }).round(3)
    else:
        # 3. Calculate the base-vs-test ratio for each core-count, plus a stddev
        all_abs_ratios = pivot.apply(
            lambda row: np.array(row[test_key]) / np.array(row[base_key]),
            axis=1
        )
        mean_abs_ratios = all_abs_ratios.apply(np.mean)
        std_abs_ratios = all_abs_ratios.apply(safe_std)

        relative_pct = (mean_abs_ratios.values - 1) * 100
        std_pct = std_abs_ratios.values * 100

        results_df = pd.DataFrame({
            'bench': [idx[0] for idx in pivot.index],
            'procs': [idx[1] for idx in pivot.index],
            'relative_pct': relative_pct,
            'std_pct': std_pct,
        }).round(3)

    # 5. Add an additional series for the geomean speedup at each core count
    df_with_ratios = pd.DataFrame({
        'procs': [idx[1] for idx in pivot.index],
        'mean_ratio': mean_abs_ratios.values,
    })
    geomean_per_proc = df_with_ratios.groupby('procs')['mean_ratio'].apply(
        lambda s: np.exp(np.mean(np.log(s.dropna())))
    )
    geomean_pct = (geomean_per_proc - 1) * 100

    # 4. Plot data as a line chart, with each series corresponding to a benchmark, marking stddev with error bar
    fig, ax = plt.subplots(figsize=(8, 5))
    markers = ['o', 's', '^', 'v', 'D', 'p', 'h', '*', 'X', '<', '>']
    benches = sorted(results_df['bench'].unique())

    for i, bench in enumerate(benches):
        bench_data = results_df[results_df['bench'] == bench].sort_values('procs')
        marker = markers[i % len(markers)]
        if use_new_analysis_style:
            yerr = [bench_data['err_minus_pct'], bench_data['err_plus_pct']]
        else:
            yerr = bench_data['std_pct']
        ax.errorbar(
            bench_data['procs'],
            bench_data['relative_pct'],
            yerr=yerr,
            label=bench,
            marker=marker,
            capsize=3,
            capthick=1,
            linewidth=1.5,
            markersize=5,
            alpha=0.85
        )

    # Dotted line for Geomean series
    ax.plot(
        geomean_per_proc.index,
        geomean_pct.values,
        label='Geomean',
        linestyle=':',
        color='black',
        marker='D',
        linewidth=2.5,
        markersize=6,
        zorder=10
    )

    ax.axhline(0, color='grey', linestyle='--', linewidth=0.8, alpha=0.7)

    unique_procs = sorted(results_df['procs'].unique())
    if len(unique_procs) > 2 and all(p > 0 for p in unique_procs) and max(unique_procs) / min(unique_procs) >= 8:
        ax.set_xscale('log', base=2)
    ax.set_xticks(unique_procs)
    ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())

    ax.set_xlabel('Core count')
    ax.set_ylabel(r'Relative \% $\frac{\mathrm{test}}{\mathrm{base}} - 1 \times 100\%$')
    ax.yaxis.set_major_formatter(ticker.PercentFormatter())
    if title:
        ax.set_title(title)
    ax.grid(True, linestyle=':', alpha=0.5)
    ax.legend(loc='best')

    plt.tight_layout()
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, f'{out_filename}.csv')
    print(f'Saving data to {csv_path}')
    results_df.to_csv(csv_path, index=False)
    path = os.path.join(out_dir, f'{out_filename}.pdf')
    print(f'Saving chart to {path}')
    plt.savefig(path, format='pdf', bbox_inches='tight', metadata={'CreationDate': None})
    plt.close()


# Plots binary size comparison (using procs=1 as binary size is independent of core count)
def plot_parallel_bench_size(df, values='binary_bytes', title='', out_filename='', abbrevs=None, out_dir='charts', use_new_analysis_style=USE_NEW_ANALYSIS_STYLE):
    # Filter for procs == 1 if procs column exists
    if 'procs' in df.columns:
        df_size = df[df['procs'] == 1].copy()
    else:
        df_size = df.copy()

    plot_parallel_bench(df_size, values=values, title=title, out_filename=out_filename, abbrevs=abbrevs, out_dir=out_dir, use_new_analysis_style=use_new_analysis_style)


def load_df(fname):
    df = pd.read_json(os.path.join(DATA_ROOT, fname), lines=True)
    df.set_index('bench')
    return df


# Plots data from the MLton benchmark suite
def plot_mlton(df, values='runTime', title='', out_filename='', abbrevs=('MLton0', 'MLton1'), out_dir='charts', use_new_analysis_style=USE_NEW_ANALYSIS_STYLE):
    # Remove columns we don't care about
    filtered = df[['bench', 'compilerAbbrev', values, 'binaryChecksum']]
    # Remove benchmarks with identical binaries
    filtered = df[filtered.groupby('bench')['binaryChecksum'].transform('nunique') > 1]
    if filtered.empty:
        print("No benchmarks with differing binary hash found.")
        return

    pivot = filtered.pivot(index='bench', columns='compilerAbbrev', values=values)
    pivot = pivot.dropna(subset=[abbrevs[0], abbrevs[1]])
    if pivot.empty:
        print("No matching benchmark runs found for comparison.")
        return

    if use_new_analysis_style:
        mean_abs_ratios = pivot.apply(
            lambda row: np.mean(row[abbrevs[1]]) / np.mean(row[abbrevs[0]]),
            axis=1
        )
        relative_pct = (mean_abs_ratios - 1) * 100
        pivot['relative_pct'] = relative_pct
        abs_ratio = mean_abs_ratios
    else:
        # Calculate the ratio (<1 is good, >1 is bad)
        abs_ratio = pivot[abbrevs[1]] / pivot[abbrevs[0]]
        # Convert to relative_pct (<0% is good, >0% is bad)
        pivot['relative_pct'] = (abs_ratio - 1) * 100

    results_df = pd.DataFrame({
        'bench': pivot.index,
        abbrevs[0]: pivot[abbrevs[0]].values,
        abbrevs[1]: pivot[abbrevs[1]].values,
        'relative_pct': pivot['relative_pct'].values,
    }).round(3)

    ax = (pivot['relative_pct']).plot(kind='bar')

    # Calculate the absolute geomean (1.0 is neutral)
    abs_geomean = np.exp(np.mean(np.log(abs_ratio.dropna())))
    # Scale to match the metric for relative_pct
    geomean_pct = (abs_geomean - 1) * 100
    # Add a text box
    textstr = fr'Geomean: {geomean_pct:+.1f}\%'
    props = dict(boxstyle='square,pad=0.5', facecolor='white', alpha=0.9, edgecolor='black', linewidth=0.5)
    ax.text(0.95, 0.95, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', horizontalalignment='right', bbox=props)
    
    ax.set_title(title)
    ax.set_xlabel('Benchmark name')
    ax.set_ylabel(r'Relative \% $\frac{\mathrm{test}}{\mathrm{base}} - 1 \times 100\%$')
    ax.yaxis.set_major_formatter(ticker.PercentFormatter())
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, f'{out_filename}.csv')
    print(f'Saving data to {csv_path}')
    results_df.to_csv(csv_path, index=False)
    path = os.path.join(out_dir, f'{out_filename}.pdf')
    print(f'Saving chart to {path}')
    plt.savefig(path, format='pdf', bbox_inches='tight', metadata={'CreationDate': None})
    plt.close()


@dataclass(frozen=True)
class PlotConfig:
    values_column: str
    title: str
    out_filename: str


def plot_mlton_vs_mlton(data, type_name='tuple', out_dir='charts', use_new_analysis_style=USE_NEW_ANALYSIS_STYLE):
    print(f'Plotting file for {type_name} flattening (MLton vs MLton): {data}')
    df = load_df(data)
    configs = [
        PlotConfig(values_column='runTime',
                   title='Run time comparison', 
                   out_filename=f'{type_name}_mlton_run_mlton_vs_mlton'),
        PlotConfig(values_column='compileTime',
                   title='Compile time comparison',
                   out_filename=f'{type_name}_mlton_compile_mlton_vs_mlton'),
        PlotConfig(values_column='binarySize',
                   title='Binary size comparison',
                   out_filename=f'{type_name}_mlton_size_mlton_vs_mlton'),
    ]
    for c in configs:
        plot_mlton(df, values=c.values_column, title=c.title, out_filename=c.out_filename, out_dir=out_dir, use_new_analysis_style=use_new_analysis_style)


def plot_parallel_bench_vs_mlton(data, type_name='tuple', out_dir='charts', use_new_analysis_style=USE_NEW_ANALYSIS_STYLE):
    print(f'Plotting file for {type_name} flattening (MLton vs MLton - Parallel Bench): {data}')
    df = load_df(data)
    configs = [
        PlotConfig(values_column='test_results_secs',
                   title='Run time comparison', 
                   out_filename=f'{type_name}_parallel_bench_run_mlton_vs_mlton'),
        PlotConfig(values_column='binary_bytes',
                   title='Binary size comparison',
                   out_filename=f'{type_name}_parallel_bench_size_mlton_vs_mlton'),
    ]
    for c in configs:
        plot_parallel_bench(df, values=c.values_column, title=c.title, out_filename=c.out_filename, out_dir=out_dir, use_new_analysis_style=use_new_analysis_style)


def plot_parallel_bench_vs_mpl(data, type_name='tuple', out_dir='charts', use_new_analysis_style=USE_NEW_ANALYSIS_STYLE):
    print(f'Plotting file for {type_name} (MPL vs MPL): {data}')
    df = load_df(data)
    configs = [
        PlotConfig(values_column='test_results_secs',
                   title=f'{type_name.capitalize()} run time comparison across core counts', 
                   out_filename=f'{type_name}_parallel_bench_run_mpl_vs_mpl'),
        PlotConfig(values_column='binary_bytes',
                   title=f'{type_name.capitalize()} binary size comparison',
                   out_filename=f'{type_name}_parallel_bench_size_mpl_vs_mpl'),
    ]
    for c in configs:
        if c.values_column in ('binary_bytes', 'binarySize'):
            plot_parallel_bench_size(df, values=c.values_column, title=c.title, out_filename=c.out_filename, out_dir=out_dir, use_new_analysis_style=use_new_analysis_style)
        else:
            plot_parallel_bench_cores(df, values=c.values_column, title=c.title, out_filename=c.out_filename, out_dir=out_dir, use_new_analysis_style=use_new_analysis_style)


def generate_all_charts_tex(config: dict) -> str:
    types_order = ['tuple', 'con', 'aos', 'soa']
    found_types = []
    for sec_k, sec_v in config.items():
        if sec_k == 'output_directory' or not isinstance(sec_v, dict):
            continue
        for t in sec_v:
            if t not in METADATA_KEYS and t not in found_types:
                found_types.append(t)

    ordered_types = [t for t in types_order if t in found_types] + [t for t in found_types if t not in types_order]

    # Collect section entries per type
    type_entries = {}
    for sec_k, sec_v in config.items():
        if sec_k == 'output_directory' or not isinstance(sec_v, dict):
            continue
        suite = sec_v.get('suite', 'mlton')
        compiler = sec_v.get('compiler', 'mlton')
        for t, data_file in sec_v.items():
            if t in METADATA_KEYS:
                continue
            if t not in type_entries:
                type_entries[t] = []
            type_entries[t].append((suite, compiler, data_file))

    def entry_key(e):
        s, c, _ = e
        if s == 'mlton':
            return 0
        if s == 'parallel_bench' and c == 'mlton':
            return 1
        if s == 'parallel_bench' and c == 'mpl':
            return 2
        return 3

    sections_tex = []

    # 1. Figure sections (one per transformation type)
    for idx, t in enumerate(ordered_types):
        sec_parts = []
        if idx > 0:
            sec_parts.append(r'\clearpage')
        title = SECTION_TITLES.get(t, f'{t.capitalize()} Flattening')
        sec_parts.append(fr'\section{{{title}}}' + '\n')

        entries = type_entries.get(t, [])
        entries.sort(key=entry_key)

        for s, c, data_file in entries:
            if s == 'mlton':
                sec_parts.append(render_mlton_subsection(t, data_file))
            elif s == 'parallel_bench' and c == 'mlton':
                sec_parts.append(render_parallel_bench_mlton_subsection(t, data_file))
            elif s == 'parallel_bench' and c == 'mpl':
                sec_parts.append(render_parallel_bench_mpl_subsection(t, data_file))

        sections_tex.append('\n'.join(sec_parts))

    # 2. Data Tables section at the end of the document
    tables_parts = []
    has_any_tables = False
    for idx, t in enumerate(ordered_types):
        entries = type_entries.get(t, [])
        if not entries:
            continue
        entries.sort(key=entry_key)
        type_tbl_parts = []
        if idx > 0:
            type_tbl_parts.append(r'\clearpage')
        title = SECTION_TITLES.get(t, f'{t.capitalize()} Flattening')
        type_tbl_parts.append(fr'\subsection{{{title}}}' + '\n')

        for s, c, _ in entries:
            if s == 'mlton':
                type_tbl_parts.append(render_mlton_tables_subsection(t))
            elif s == 'parallel_bench' and c == 'mlton':
                type_tbl_parts.append(render_parallel_bench_mlton_tables_subsection(t))
            elif s == 'parallel_bench' and c == 'mpl':
                type_tbl_parts.append(render_parallel_bench_mpl_tables_subsection(t))

        tables_parts.append('\n'.join(type_tbl_parts))
        has_any_tables = True

    if has_any_tables:
        sections_tex.append(r'\clearpage' + '\n' + r'\section{Data Tables}' + '\n')
        sections_tex.append('\n'.join(tables_parts))

    body = '\n'.join(sections_tex)
    return f"{DOCUMENT_PREAMBLE}\n{body}\n{DOCUMENT_POSTAMBLE}"


def process_config(config: dict, use_new_analysis_style=USE_NEW_ANALYSIS_STYLE):
    out_dir = config["output_directory"]
    os.makedirs(out_dir, exist_ok=True)

    timestamp = datetime.now()
    chart_info_path = os.path.join(out_dir, "chart_info.md")
    print(f'Saving run info to {chart_info_path}')
    with open(chart_info_path, "w", encoding="utf-8") as f:
        f.write(f"Data generated at {timestamp} using the following config:\n\n{json.dumps(config, indent=2)}\n")

    for section_key, section_val in config.items():
        if section_key == "output_directory":
            continue
        if not isinstance(section_val, dict):
            continue

        suite = section_val.get("suite", "mlton")
        compiler = section_val.get("compiler", "mlton")

        for type_name, data_file in section_val.items():
            if type_name in METADATA_KEYS:
                continue

            if suite == "mlton":
                plot_mlton_vs_mlton(data_file, type_name, out_dir=out_dir, use_new_analysis_style=use_new_analysis_style)
            elif suite == "parallel_bench":
                if compiler == "mpl":
                    plot_parallel_bench_vs_mpl(data_file, type_name, out_dir=out_dir, use_new_analysis_style=use_new_analysis_style)
                elif compiler == "mlton":
                    plot_parallel_bench_vs_mlton(data_file, type_name, out_dir=out_dir, use_new_analysis_style=use_new_analysis_style)
                else:
                    raise ValueError(f"Unknown compiler for parallel_bench: {compiler}")
            else:
                raise ValueError(f"Unknown suite: {suite}")

    all_charts_tex_path = os.path.join(out_dir, "all_charts.tex")
    print(f'Saving all_charts TeX file to {all_charts_tex_path}')
    with open(all_charts_tex_path, "w", encoding="utf-8") as f:
        f.write(generate_all_charts_tex(config))


