# Constraint Programming Equations for skripsi-mining.py

This document presents the mathematical formulation of all constraints in the `skripsi-recode.py` script, which uses Constraint Programming (CP) with Google OR-Tools CP-SAT to schedule mining activities for four locations (Blok 4 Central, RM 8, Rampdown A Selatan, RC 6 Central) over three months (April, Mei, Juni 2025). The goal is to maximize total progress (meters) while respecting equipment, waste capacity, priority, and activity constraints. The equations reflect the script’s implementation, including task scheduling and the merged `Location` class.

## Indices and Sets
- $t \in T = \{(\text{Apr}, 2025), (\text{Mei}, 2025), (\text{Jun}, 2025)\}$: Time periods (months).
- $v \in V = \{\text{Blok 4 Central}, \text{RM 8}, \text{Rampdown A Selatan}, \text{RC 6 Central}\}$: Locations.
- $V_B \subseteq V = \{\text{RM 8}\}$: Locations with blasting activity ($\text{activity\_type} = \text{"blasting"}$).
- $V_T \subseteq V = \{\text{Blok 4 Central}, \text{Rampdown A Selatan}, \text{RC 6 Central}\}$: Locations with tunneling activity ($\text{activity\_type} = \text{"tunneling"}$).
- $U_t \subseteq V$: Locations unavailable in month $t$ (e.g., RC 6 Central in April).

## Parameters
- $D_t$: Days per month ($D_{(\text{Apr}, 2025)} = 30, D_{(\text{Mei}, 2025)} = 31, D_{(\text{Jun}, 2025)} = 30$).
- $S_t = 2 \cdot D_t$: Shifts per month (2 shifts per day).
- $L_v$: Maximum progress for location $v$ (meters):
  - $L_{\text{Blok 4 Central}} = 37.7$
  - $L_{\text{RM 8}} = 26.5$
  - $L_{\text{Rampdown A Selatan}} = 147.8$
  - $L_{\text{RC 6 Central}} = 509.6$
- $\rho_v$: Progress rate for location $v$ (meters per unit):
  - $\rho_{\text{RM 8}} = 1.280 \, \text{m/blast}$
  - Others: $\rho_v = 0.405 \, \text{m/shift}$
- $W_v$: Waste capacity for location $v$ (tons/month):
  - $W_v = 7542.67 \cdot \frac{4}{2} = 15085.34$
- $P_v$: Waste per meter for location $v$ (tons/m):
  - $P_{\text{RM 8}} = 14.64$
  - Others: $P_v = 33.87$
- $\Gamma = 38.4$: Minimum tunneling progress per month (meters).
- $\epsilon = 1.0$: Progress tolerance (meters).
- $B_v$: Blast days for location $v$:
  - $B_{\text{RM 8}} = 3$
  - Others: $B_v = \text{None}$
- $M_{\text{JD}} = 2$: Maximum Jackleg Drill units.
- $M_{\text{WL}} = 4$: Maximum Wheel Loader units.
- $\pi_v$: Priority weight for location $v$:
  - $\pi_{\text{Blok 4 Central}} = 4$
  - $\pi_{\text{RM 8}} = 3$
  - $\pi_{\text{Rampdown A Selatan}} = 2$
  - $\pi_{\text{RC 6 Central}} = 1$
- $\omega_t$: Month weight for period $t$:
  - $\omega_{(\text{Apr}, 2025)} = 3$
  - $\omega_{(\text{Mei}, 2025)} = 2$
  - $\omega_{(\text{Jun}, 2025)} = 1$

## Variables
- $a_{t,v} \in \{0, 1\}$: Binary variable indicating if location $v$ is active in month $t$.
- $u_{t,v} \geq 0$: Integer number of units (blasts for blasting, shifts for tunneling) for location $v$ in month $t$.
- $l_{t,v} \geq 0$: Progress (meters) for location $v$ in month $t$.
- $s_{t,v} \in [0, S_t]$: Start shift for location $v$ in month $t$.
- $d_{t,v} \in [0, S_t]$: Duration in shifts for location $v$ in month $t$.
- $e_{t,v} \in [0, S_t]$: End shift for location $v$ in month $t$.
- $i_{t,v}$: Optional interval for location $v$ in month $t$, active if $a_{t,v} = 1$.
- $r_{t,v} \geq 0$: Cumulative units used by location $v$ up to month $t$.
- $h_{t,v} \in \{0, 1\}$: Binary variable indicating if location $v$ has sufficient remaining units in month $t$.
- $c_{t,v,w} \in \{0, 1\}$: Binary variable indicating if locations $v$ and $w$ ($ \pi_v > \pi_w $) satisfy the priority condition in month $t$.

## Objective Function
$$
\text{Maximize } Z = \sum_{t \in T} \sum_{v \in V} \pi_v \cdot \omega_t \cdot l_{t,v}
$$
- Maximizes the weighted sum of progress, prioritizing higher-priority locations ($ \pi_v $) and earlier months ($ \omega_t $).

## Constraints

1. **Progress Calculation**:
   $$
   l_{t,v} \cdot 1000 = u_{t,v} \cdot (\rho_v \cdot 1000) \quad \forall t \in T, \forall v \in V
   $$
   Relates progress (millimeters) to units (blasts or shifts) and progress rate, scaled by 1000 for integer arithmetic.

2. **Unit Bounds**:
   For blasting locations:
   $$
   u_{t,v} \leq \lfloor S_t / 1 \rfloor \quad \forall t \in T, \forall v \in V_B
   $$
   For tunneling locations:
   $$
   u_{t,v} \leq S_t \quad \forall t \in T, \forall v \in V_T
   $$

3. **Presence and Activity**:
   $$
   u_{t,v} > 0 \implies a_{t,v} = 1 \quad \forall t \in T, \forall v \in V
   $$
   $$
   u_{t,v} = 0 \implies a_{t,v} = 0 \quad \forall t \in T, \forall v \in V
   $$

4. **Task Scheduling**:
   $$
   d_{t,v} = u_{t,v} \quad \forall t \in T, \forall v \in V
   $$
   $$
   e_{t,v} = s_{t,v} + d_{t,v} \quad \forall t \in T, \forall v \in V
   $$
   $$
   i_{t,v} \text{ active} \iff a_{t,v} = 1 \quad \forall t \in T, \forall v \in V
   $$

5. **Unavailability**:
   $$
   a_{t,v} = 0, \quad l_{t,v} = 0, \quad u_{t,v} = 0, \quad s_{t,v} = 0, \quad d_{t,v} = 0, \quad e_{t,v} = 0 \quad \forall t \in T, \forall v \in U_t
   $$
   (e.g., RC 6 Central in April).

6. **Jackleg Drill Allocation**:
   $$
   \sum_{v \in V} u_{t,v} \leq M_{\text{JD}} \cdot D_t \cdot 2 \quad \forall t \in T
   $$
   $$
   \text{Cumulative}(i_{t,v}, 1, M_{\text{JD}}) \quad \forall t \in T, \forall v \in V
   $$

7. **Wheel Loader Allocation**:
   $$
   \sum_{v \in V} a_{t,v} \leq M_{\text{WL}} \quad \forall t \in T
   $$

8. **Waste Capacity**:
   $$
   P_v \cdot l_{t,v} \leq W_v \quad \forall t \in T, \forall v \in V
   $$
   $$
   \sum_{v \in V} (P_v \cdot l_{t,v}) \leq \sum_{v \in V} W_v \quad \forall t \in T
   $$

9. **Maximum Cumulative Units**:
   $$
   \sum_{t \in T} u_{t,v} \leq \lceil L_v / \rho_v \rceil \quad \forall v \in V
   $$

10. **Priority for Tunneling Locations**:
    For $v, w \in V_T$, $\pi_v > \pi_w$:
    $$
    r_{t,v} = \lceil L_v / \rho_v \rceil - \sum_{\tau \leq t} u_{\tau,v} \quad \forall t \in T, \forall v \in V_T
    $$
    $$
    r_{t,v} \geq S_t \implies h_{t,v} = 1 \quad \forall t \in T, \forall v \in V_T
    $$
    $$
    r_{t,v} < S_t \implies h_{t,v} = 0 \quad \forall t \in T, \forall v \in V_T
    $$
    $$
    (h_{t,v} = 1) \land (a_{t,v} = 1) \implies c_{t,v,w} = 1 \quad \forall t \in T, \forall v, w \in V_T, \pi_v > \pi_w
    $$
    $$
    (h_{t,v} = 0) \lor (a_{t,v} = 0) \implies c_{t,v,w} = 0 \quad \forall t \in T, \forall v, w \in V_T, \pi_v > \pi_w
    $$
    $$
    c_{t,v,w} = 1 \implies u_{t,v} \geq u_{t,w} \quad \forall t \in T, \forall v, w \in V_T, \pi_v > \pi_w
    $$

## Notes
- **Progress Scaling**: Progress is scaled by 1000 (millimeters) for integer arithmetic.
- **Priority**: Applies only to tunneling locations, ensuring higher-priority locations get more shifts when feasible.
- **Minimum Progress**: Implied by output check (≥ 38.4 m/month for tunneling) but not a hard constraint.
- **Task Scheduling**: Supports mid-month starts via $ s_{t,v} $, $ d_{t,v} $, $ e_{t,v} $.
- **Expected Output**: Matches provided April 2025 data (e.g., Blok 4 Central: 24.300 m, RM 8: 25.600 m, Rampdown A Selatan: 16.200 m, total: 66.100 m, Optimal 120/120 shifts).