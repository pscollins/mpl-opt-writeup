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


def safe_std(all_abs_ratios):
    arr = np.atleast_1d(all_abs_ratios)
    if len(arr) <= 1:
        return 0.0
    return np.std(arr, ddof=1)


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


def load_df(fname):
    df = pd.read_json(os.path.join(DATA_ROOT, fname), lines=True)
    df.set_index('bench')
    return df


# Plots data from the MLton benchmark suite
def plot_mlton(df, values='runTime', title='', out_filename='', abbrevs=('MLton0', 'MLton1'), out_dir='charts'):
    # Remove columns we don't care about
    filtered = df[['bench', 'compilerAbbrev', values, 'binaryChecksum']]
    # Remove benchmarks witn identical binaries
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

        for type_name, data_file in section_val.items():
            if type_name in METADATA_KEYS:
                continue

            if suite == "mlton":
                plot_mlton_vs_mlton(data_file, type_name, out_dir=out_dir)
            elif suite == "parallel_bench":
                plot_parallel_bench_vs_mlton(data_file, type_name, out_dir=out_dir)
            else:
                raise ValueError(f"Unknown suite: {suite}")



