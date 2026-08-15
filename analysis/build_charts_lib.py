import json
import os
from dataclasses import dataclass
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd

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


def safe_std(all_abs_ratios):
    arr = np.atleast_1d(all_abs_ratios)
    if len(arr) <= 1:
        return 0.0
    return np.std(arr, ddof=1)


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
def plot_parallel_bench(df, values='test_results_secs', title='', out_filename='', out_dir='charts'):
    # Infer the name of the test config by removing the -baseline version
    configs = set(df[COMPILER_NAME_FIELD_PARALLEL].dropna().unique())
    if 'mlton-baseline' not in configs:
        raise ValueError(f"Baseline 'mlton-baseline' not found in compiler configurations: {configs}")
    configs.remove('mlton-baseline')
    assert len(configs) == 1, f"Expected exactly 1 test configuration after removing 'mlton-baseline', found {len(configs)}: {configs}"
    test_key = next(iter(configs))

    # Remove columns we don't care about
    filtered = df[['bench', COMPILER_NAME_FIELD_PARALLEL, values, CHECKSUM_FIELD_PARALLEL]]
    # Remove benchmarks with identical binaries
    filtered = filtered[filtered.groupby('bench')[CHECKSUM_FIELD_PARALLEL].transform('nunique') > 1]
    # Drop older duplicate runs before pivoting
    filtered = filtered.drop_duplicates(subset=['bench', COMPILER_NAME_FIELD_PARALLEL], keep='last')

    pivot = filtered.pivot(index='bench', columns=COMPILER_NAME_FIELD_PARALLEL, values=values)
    # Calculate the ratio (<1 is good, >1 is bad) between pairs of trials
    all_abs_ratios = pivot.apply(lambda row:
                              np.array(row[test_key]) / np.array(row['mlton-baseline']),
                              axis=1)
    mean_abs_ratios = all_abs_ratios.apply(np.mean)
    std_abs_ratios = all_abs_ratios.apply(safe_std)
    # Convert to relative_pct (<0% is good, >0% is bad)
    relative_pct = (mean_abs_ratios - 1) * 100
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
    path = os.path.join(out_dir, f'{out_filename}.pdf')
    print(f'Saving chart to {path}')
    plt.savefig(path, format='pdf', bbox_inches='tight')
    plt.close()


# Plots run time data across core counts (procs) from the parallel-ml-bench suite
def plot_parallel_bench_cores(df, values='test_results_secs', title='', out_filename='', abbrevs=None, out_dir='charts'):
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

    # 3. Calculate the base-vs-test ratio for each core-count, plus a stddev
    all_abs_ratios = pivot.apply(
        lambda row: np.array(row[test_key]) / np.array(row[base_key]),
        axis=1
    )
    mean_abs_ratios = all_abs_ratios.apply(np.mean)
    std_abs_ratios = all_abs_ratios.apply(safe_std)

    results_df = pd.DataFrame({
        'bench': [idx[0] for idx in pivot.index],
        'procs': [idx[1] for idx in pivot.index],
        'mean_ratio': mean_abs_ratios.values,
        'std_ratio': std_abs_ratios.values,
        'relative_pct': (mean_abs_ratios.values - 1) * 100,
        'std_pct': std_abs_ratios.values * 100,
    })

    # 5. Add an additional series for the geomean speedup at each core count
    geomean_per_proc = results_df.groupby('procs')['mean_ratio'].apply(
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
        ax.errorbar(
            bench_data['procs'],
            bench_data['relative_pct'],
            yerr=bench_data['std_pct'],
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
    path = os.path.join(out_dir, f'{out_filename}.pdf')
    print(f'Saving chart to {path}')
    plt.savefig(path, format='pdf', bbox_inches='tight')
    plt.close()


# Plots binary size comparison (using procs=1 as binary size is independent of core count)
def plot_parallel_bench_size(df, values='binary_bytes', title='', out_filename='', abbrevs=None, out_dir='charts'):
    # Filter for procs == 1 if procs column exists
    if 'procs' in df.columns:
        df_size = df[df['procs'] == 1].copy()
    else:
        df_size = df.copy()

    # Filter benchmarks with differing binary hash
    filtered = df_size[df_size.groupby('bench')[CHECKSUM_FIELD_PARALLEL].transform('nunique') > 1]
    if filtered.empty:
        print("No benchmarks with differing binary hash found.")
        return

    base_key, test_key = infer_configs(filtered, abbrevs)
    filtered = filtered[filtered[COMPILER_NAME_FIELD_PARALLEL].isin([base_key, test_key])]
    filtered = filtered.drop_duplicates(subset=['bench', COMPILER_NAME_FIELD_PARALLEL], keep='last')

    pivot = filtered.pivot(index='bench', columns=COMPILER_NAME_FIELD_PARALLEL, values=values)
    pivot = pivot.dropna(subset=[base_key, test_key])
    if pivot.empty:
        print("No matching benchmark runs found for comparison.")
        return

    abs_ratio = pivot[test_key] / pivot[base_key]
    relative_pct = (abs_ratio - 1) * 100

    fig, ax = plt.subplots(figsize=(8, 5))
    relative_pct.plot(kind='bar', ax=ax, color='tab:blue', alpha=0.85, edgecolor='black', linewidth=0.5)

    # Calculate absolute geomean
    abs_geomean = np.exp(np.mean(np.log(abs_ratio.dropna())))
    geomean_pct = (abs_geomean - 1) * 100

    textstr = fr'Geomean: {geomean_pct:+.1f}\%'
    props = dict(boxstyle='square,pad=0.5', facecolor='white', alpha=0.9, edgecolor='black', linewidth=0.5)
    ax.text(0.95, 0.95, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', horizontalalignment='right', bbox=props)

    ax.axhline(0, color='grey', linestyle='--', linewidth=0.8, alpha=0.7)
    if title:
        ax.set_title(title)
    ax.set_xlabel('Benchmark name')
    ax.set_ylabel(r'Relative \% $\frac{\mathrm{test}}{\mathrm{base}} - 1 \times 100\%$')
    ax.yaxis.set_major_formatter(ticker.PercentFormatter())
    plt.xticks(rotation=0)
    plt.tight_layout()
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f'{out_filename}.pdf')
    print(f'Saving chart to {path}')
    plt.savefig(path, format='pdf', bbox_inches='tight')
    plt.close()


def load_df(fname):
    df = pd.read_json(os.path.join(DATA_ROOT, fname), lines=True)
    df.set_index('bench')
    return df


# Plots data from the MLton benchmark suite
def plot_mlton(df, values='runTime', title='', out_filename='', abbrevs=('MLton0', 'MLton1'), out_dir='charts'):
    # Remove columns we don't care about
    filtered = df[['bench', 'compilerAbbrev', values, 'binaryChecksum']]
    # Remove benchmarks with identical binaries
    filtered = df[filtered.groupby('bench')['binaryChecksum'].transform('nunique') > 1]
    pivot = filtered.pivot(index='bench', columns='compilerAbbrev', values=values)
    # Calculate the ratio (<1 is good, >1 is bad)
    abs_ratio = pivot[abbrevs[1]] / pivot[abbrevs[0]]
    # Convert to relative_pct (<0% is good, >0% is bad)
    pivot['relative_pct'] = (abs_ratio - 1) * 100
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
    path = os.path.join(out_dir, f'{out_filename}.pdf')
    print(f'Saving chart to {path}')
    plt.savefig(path, format='pdf', bbox_inches='tight')
    plt.close()


@dataclass(frozen=True)
class PlotConfig:
    values_column: str
    title: str
    out_filename: str


def plot_mlton_vs_mlton(data, type_name='tuple', out_dir='charts'):
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
        plot_mlton(df, values=c.values_column, title=c.title, out_filename=c.out_filename, out_dir=out_dir)


def plot_parallel_bench_vs_mlton(data, type_name='tuple', out_dir='charts'):
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
        plot_parallel_bench(df, values=c.values_column, title=c.title, out_filename=c.out_filename, out_dir=out_dir)


def plot_parallel_bench_vs_mpl(data, type_name='tuple', out_dir='charts'):
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
            plot_parallel_bench_size(df, values=c.values_column, title=c.title, out_filename=c.out_filename, out_dir=out_dir)
        else:
            plot_parallel_bench_cores(df, values=c.values_column, title=c.title, out_filename=c.out_filename, out_dir=out_dir)


def process_config(config: dict):
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
                plot_mlton_vs_mlton(data_file, type_name, out_dir=out_dir)
            elif suite == "parallel_bench":
                if compiler == "mpl":
                    plot_parallel_bench_vs_mpl(data_file, type_name, out_dir=out_dir)
                elif compiler == "mlton":
                    plot_parallel_bench_vs_mlton(data_file, type_name, out_dir=out_dir)
                else:
                    raise ValueError(f"Unknown compiler for parallel_bench: {compiler}")
            else:
                raise ValueError(f"Unknown suite: {suite}")
