import json
import os
from dataclasses import dataclass
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
CHARTS_ROOT = 'charts/'


def load_df(fname):
    df = pd.read_json(os.path.join(DATA_ROOT, fname), lines=True)
    df.set_index('bench')
    return df


# Plots data from the MLton benchmark suite
def plot_mlton(df, values='runTime', title='', out_filename='', abbrevs=('MLton0', 'MLton1')):
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
    textstr = f'Geomean: {geomean_pct:+.1f}\\%'
    props = dict(boxstyle='square,pad=0.5', facecolor='white', alpha=0.9, edgecolor='black', linewidth=0.5)
    ax.text(0.95, 0.95, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', horizontalalignment='right', bbox=props)
    
    ax.set_title(title)
    ax.set_xlabel('Benchmark name')
    ax.set_ylabel(r'Relative \% $\frac{\mathrm{test}}{\mathrm{base}} - 1 \times 100\%$')
    ax.yaxis.set_major_formatter(ticker.PercentFormatter())
    os.makedirs(CHARTS_ROOT, exist_ok=True)
    path = os.path.join(CHARTS_ROOT, f'{out_filename}.pdf')
    print(f'Saving chart to {path}')
    plt.savefig(path, format='pdf', bbox_inches='tight')
    plt.close()


@dataclass(frozen=True)
class PlotConfig:
    values_column: str
    title: str
    out_filename: str


def plot_mlton_vs_mlton(data, type_name='tuple'):
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
        plot_mlton(df, values=c.values_column, title=c.title, out_filename=c.out_filename)


# Generate all MLton-vs-MLton tuple flattening charts
def plot_mlton_tuple_flattening():
    data = 'fix_hashes4:big-mpl:99fe634ab:20260719_202336.jsonl'
    plot_mlton_vs_mlton(data, 'tuple')


def plot_mlton_con_flattening():
    data = 'run_con1:big-mpl:1cae85c45:20260719_222637.jsonl'
    plot_mlton_vs_mlton(data, 'con')


def process_config(config: dict):
    if "mlton_benchmarks_mlton_vs_mlton" in config:
        for type_name, data_file in config["mlton_benchmarks_mlton_vs_mlton"].items():
            plot_mlton_vs_mlton(data_file, type_name)


