#!/usr/bin/env python3
"""
Generate publication-ready figures for spatial transcriptomics GPU benchmark paper.

Three figures:
- Figure 7: Overall speedup comparison across platforms (bar chart, log scale)
- Figure 8: Per-step speedup for Visium HD 8um (horizontal bar, log scale)
- Figure 9: Concordance metrics across platforms (grouped bar chart)

All figures saved as PNG (300 DPI) in current directory.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rcParams
import os

# Configure matplotlib for publication-quality figures
rcParams['font.family'] = 'serif'
rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
rcParams['font.size'] = 11
rcParams['axes.labelsize'] = 11
rcParams['axes.titlesize'] = 12
rcParams['xtick.labelsize'] = 10
rcParams['ytick.labelsize'] = 10
rcParams['legend.fontsize'] = 10
rcParams['figure.dpi'] = 100  # Screen DPI; will save at 300
rcParams['savefig.dpi'] = 300
rcParams['savefig.bbox'] = 'tight'
rcParams['lines.linewidth'] = 1.5
rcParams['patch.linewidth'] = 1.0
rcParams['axes.linewidth'] = 1.0
rcParams['xtick.major.width'] = 1.0
rcParams['ytick.major.width'] = 1.0
rcParams['xtick.major.size'] = 5
rcParams['ytick.major.size'] = 5


def figure_7_spatial_speedup():
    """
    Figure 7: End-to-end speedup across three Visium platforms.
    Bar chart with CPU (blue) and GPU (orange) times, annotated speedup values.
    Y-axis log scale.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    # Data
    platforms = ['Visium v1\n(2,695 spots)', 'Visium HD 8 µm\n(393,543 bins)', 'Visium HD 2 µm\n(389,492 bins)']
    cpu_times = [10.0, 4068, 1042]
    gpu_times = [6.0, 79, 97]
    speedups = [1.7, 51.6, 10.8]

    x = np.arange(len(platforms))
    width = 0.35

    # Create bars
    bars1 = ax.bar(x - width/2, cpu_times, width, label='CPU', color='#1f77b4', alpha=0.8, edgecolor='black', linewidth=0.8)
    bars2 = ax.bar(x + width/2, gpu_times, width, label='GPU', color='#ff7f0e', alpha=0.8, edgecolor='black', linewidth=0.8)

    # Set y-axis to log scale
    ax.set_yscale('log')

    # Labels and formatting
    ax.set_ylabel('Wall time (s)', fontsize=11, fontweight='bold')
    ax.set_xlabel('Platform', fontsize=11, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(platforms, fontsize=10)
    ax.legend(loc='upper left', frameon=True, fancybox=False, edgecolor='black', fontsize=10)

    # Add speedup annotations above each platform group
    for i, speedup in enumerate(speedups):
        ax.text(i, max(cpu_times[i], gpu_times[i]) * 2.5, f'{speedup}×',
                ha='center', va='bottom', fontsize=11, fontweight='bold', color='darkred')

    # Grid and styling
    ax.grid(True, which='both', axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    # Y-axis limits
    ax.set_ylim(1, 10000)

    plt.tight_layout()
    plt.savefig('fig7_spatial_speedup.png', dpi=300, bbox_inches='tight')
    print("✓ Saved fig7_spatial_speedup.png")
    plt.close()


def figure_8_spatial_perstep():
    """
    Figure 8: Per-step speedup for Visium HD 8um (horizontal bar chart, log scale).
    GPU-accelerated steps in color, CPU-only (parity) steps in gray.
    Highlight co_occurrence (3,272x) with distinct color.
    """
    fig, ax = plt.subplots(figsize=(11, 7))

    # Data: step name, CPU time, GPU time, speedup
    steps = [
        'co_occurrence',
        'pca',
        'normalization',
        'moran_i',
        'geary_c',
        'umap',
        'hvg_selection',
        'expression_neighbors',
        'leiden',
        'spatial_neighbors',
        'nhood_enrichment',
    ]

    speedups_list = [3272, 257, 176, 162, 163, 159, 76, 20, 16, 1.0, 1.0]

    # Identify GPU-accelerated vs CPU-only steps
    colors = []
    for speedup in speedups_list:
        if speedup > 1.5:  # GPU-accelerated
            if speedup >= 1000:  # co_occurrence
                colors.append('#d62728')  # Dark red for extreme case
            else:
                colors.append('#2ca02c')  # Green for GPU-accelerated
        else:
            colors.append('#7f7f7f')  # Gray for CPU-only / parity

    # Sort by speedup (descending)
    sorted_indices = np.argsort(speedups_list)[::-1]
    steps_sorted = [steps[i] for i in sorted_indices]
    speedups_sorted = [speedups_list[i] for i in sorted_indices]
    colors_sorted = [colors[i] for i in sorted_indices]

    y_pos = np.arange(len(steps_sorted))

    # Create horizontal bars
    bars = ax.barh(y_pos, speedups_sorted, color=colors_sorted, alpha=0.8, edgecolor='black', linewidth=0.8)

    # Set x-axis to log scale
    ax.set_xscale('log')

    # Labels and formatting
    ax.set_xlabel('Speedup (log scale)', fontsize=11, fontweight='bold')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(steps_sorted, fontsize=10)
    ax.set_xlim(0.5, 10000)

    # Add vertical line at parity (x=1)
    ax.axvline(x=1, color='black', linestyle='--', linewidth=1.2, alpha=0.7, label='CPU = GPU parity')

    # Add speedup values as text on the bars
    for i, (speedup, bar) in enumerate(zip(speedups_sorted, bars)):
        if speedup >= 1.5:
            label_x = speedup * 1.2
            ax.text(label_x, bar.get_y() + bar.get_height()/2, f'{speedup:.0f}×',
                    va='center', ha='left', fontsize=9, fontweight='bold')
        else:
            ax.text(speedup * 0.8, bar.get_y() + bar.get_height()/2, '1.0×',
                    va='center', ha='right', fontsize=9, color='white', fontweight='bold')

    # Legend
    green_patch = mpatches.Patch(color='#2ca02c', alpha=0.8, label='GPU-accelerated')
    red_patch = mpatches.Patch(color='#d62728', alpha=0.8, label='Extreme speedup (co_occurrence)')
    gray_patch = mpatches.Patch(color='#7f7f7f', alpha=0.8, label='CPU-only / parity')
    ax.legend(handles=[green_patch, red_patch, gray_patch], loc='lower right', frameon=True,
              fancybox=False, edgecolor='black', fontsize=9)

    # Grid and styling
    ax.grid(True, which='both', axis='x', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    plt.tight_layout()
    plt.savefig('fig8_spatial_perstep.png', dpi=300, bbox_inches='tight')
    print("✓ Saved fig8_spatial_perstep.png")
    plt.close()


def figure_9_spatial_concordance():
    """
    Figure 9: Concordance metrics across three Visium platforms.
    Grouped bar chart with 5 metrics (x-axis) and three platform groups (colors).
    Highlight HD 2um cluster ARI outlier (0.080).
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    # Data: metrics x platforms
    metrics = ['Moran ρ', 'Geary ρ', 'SVG top-50', 'SVG FDR<0.05', 'Cluster ARI']

    visium_values = [1.0000, 1.0000, 1.000, 1.000, 0.856]
    hd8um_values = [0.9999, 0.9995, 1.000, 0.999, 0.974]
    hd2um_values = [1.0000, 0.9999, 1.000, 0.982, 0.080]

    x = np.arange(len(metrics))
    width = 0.25

    # Create bars
    bars1 = ax.bar(x - width, visium_values, width, label='Visium v1',
                   color='#1f77b4', alpha=0.8, edgecolor='black', linewidth=0.8)
    bars2 = ax.bar(x, hd8um_values, width, label='Visium HD 8 µm',
                   color='#2ca02c', alpha=0.8, edgecolor='black', linewidth=0.8)
    bars3 = ax.bar(x + width, hd2um_values, width, label='Visium HD 2 µm',
                   color='#ff7f0e', alpha=0.8, edgecolor='black', linewidth=0.8)

    # Labels and formatting
    ax.set_ylabel('Concordance value', fontsize=11, fontweight='bold')
    ax.set_xlabel('Metric', fontsize=11, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=10)
    ax.set_ylim(0, 1.1)
    ax.legend(loc='lower left', frameon=True, fancybox=False, edgecolor='black', fontsize=10)

    # Add value labels on bars (except those very close to 1.0)
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            if height < 0.95 or height < 0.9:  # Show labels for non-perfect bars
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.3f}',
                        ha='center', va='bottom', fontsize=8)

    # Highlight the HD 2um cluster ARI outlier with a box around it
    outlier_bar = bars3[-1]  # Last bar of HD 2um (Cluster ARI)
    rect = mpatches.Rectangle((outlier_bar.get_x() - 0.02, -0.05),
                              outlier_bar.get_width() + 0.04, 0.15,
                              linewidth=2.0, edgecolor='red', facecolor='none',
                              linestyle='--', zorder=5)
    ax.add_patch(rect)

    # Annotate the outlier
    ax.text(outlier_bar.get_x() + outlier_bar.get_width()/2, 0.15,
            'Algorithmic\ndifference',
            ha='center', va='bottom', fontsize=9, color='red', fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.3, edgecolor='red'))

    # Grid and styling
    ax.grid(True, which='major', axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    # Add horizontal line at y=0.95 (high concordance threshold)
    ax.axhline(y=0.95, color='gray', linestyle=':', linewidth=1.0, alpha=0.5)
    ax.text(-0.5, 0.95, 'High concordance threshold', fontsize=8, color='gray', va='center')

    plt.tight_layout()
    plt.savefig('fig9_spatial_concordance.png', dpi=300, bbox_inches='tight')
    print("✓ Saved fig9_spatial_concordance.png")
    plt.close()


def main():
    """Generate all three figures."""
    print("Generating publication-ready spatial transcriptomics figures...")
    print()

    figure_7_spatial_speedup()
    figure_8_spatial_perstep()
    figure_9_spatial_concordance()

    print()
    print("All figures generated successfully!")
    print()
    print("Files created:")
    print("  - fig7_spatial_speedup.png")
    print("  - fig8_spatial_perstep.png")
    print("  - fig9_spatial_concordance.png")
    print()
    print("Specifications:")
    print("  - Resolution: 300 DPI (publication quality)")
    print("  - Format: PNG")
    print("  - Style: Clean, serif fonts, minimal gridlines")


if __name__ == '__main__':
    main()
