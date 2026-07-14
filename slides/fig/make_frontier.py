"""Tailored slide chart: the capacity-rating (rho) cost--feasibility frontier.
Data from progress/results-ledger.md (issue-time rebuild): rho10 0.89x, rho15 0.62x
(conservative headline), rho20 0.48x (cheapest clean), rho25 0.40x (loses burst5)."""
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt

rho  = [10, 15, 20, 25]
cost = [0.89, 0.62, 0.48, 0.40]
feas = [True, True, True, False]

plt.rcParams.update({'font.size': 11, 'font.family': 'sans-serif',
                     'axes.spines.top': False, 'axes.spines.right': False})
fig, ax = plt.subplots(figsize=(5.1, 3.7))
ax.plot(rho, cost, '-', color='#9aa0a6', lw=1.6, zorder=1)
for r, c, f in zip(rho, cost, feas):
    if f: ax.plot(r, c, 'o', ms=11, color='#137a63', zorder=3)   # feasible: teal circle
    else: ax.plot(r, c, 'X', ms=14, color='#d1495b', zorder=3)   # infeasible: red X (shape != colour-only)
ax.axhline(1.0, ls='--', lw=1, color='#9aa0a6')
ax.text(26.6, 1.0, 'static\nfleet', va='center', ha='left', fontsize=9, color='#5f6368')
ax.annotate(r'$0.62\times$' '\nconservative\nheadline', (15, 0.62), xytext=(15, 0.83),
            ha='center', fontsize=9.5, fontweight='bold', color='#137a63',
            arrowprops=dict(arrowstyle='-', color='#137a63', lw=0.8))
ax.annotate(r'$0.48\times$ cheapest clean', (20, 0.48), xytext=(20.4, 0.60),
            ha='left', fontsize=9, color='#137a63')
ax.annotate('loses burst5', (25, 0.40), xytext=(24.4, 0.52), ha='right', fontsize=9,
            color='#d1495b', arrowprops=dict(arrowstyle='-', color='#d1495b', lw=0.8))
ax.set_xlabel(r'capacity rating $\rho$  (img/s per worker)')
ax.set_ylabel(r'GPU-time vs. static fleet ($\times$)')
ax.set_xticks(rho); ax.set_ylim(0.30, 1.10); ax.set_xlim(8, 28)
ax.set_title(r'Cost falls with $\rho$ --- until the feasibility frontier', fontsize=11)
ax.grid(axis='y', alpha=0.25)
fig.tight_layout(); fig.savefig('/home/gio/tese/slides/fig/cost_frontier.pdf', bbox_inches='tight')
print('saved cost_frontier.pdf')
