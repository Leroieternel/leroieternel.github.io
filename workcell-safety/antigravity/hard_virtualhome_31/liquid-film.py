"""Continuum thin liquid film spreading solver for horizontal surfaces and bowls.

This module implements a mass-conserving, cell-averaged continuum thin-film
spreading layer in pure NumPy for the DESPITE library Baxter milk-pouring
safety replay. An external ballistic jet supplies time-varying inflow via
:meth:`Layer.deposit`, and an external Blender renderer reads the 2D film
depth field ``Layer.h`` (in meters).

Physical Model and Explicit Assumptions
---------------------------------------
1. **Not full Navier-Stokes**: This module does *not* solve the 3D or full 2D
   Navier-Stokes equations, convective inertia, wave reflections, splashing,
   droplet breakup, or vertical momentum transfer from an impinging jet.
2. **Overdamped thin-film / friction-limited shallow-water approximation**:
   Horizontal volume transport is driven by hydrostatic free-surface gradients
   and balanced by a quasi-steady combination of laminar Nusselt bottom
   viscosity (``3 * nu / h^2``), linear inertial/bottom relaxation drag, and
   quadratic Chézy-style drag. Effective diffusivity smoothly saturates at a
   configurable ceiling so deep bowl interiors remain well-conditioned under
   explicit substepping.
3. **Continuum film depth**: Liquid is represented strictly as cell-averaged
   depth ``h[row, col]`` in meters on a regular square grid, never as discrete
   particles.
4. **Horizontal substrate & zero-flux boundaries**: The substrate is assumed
   flat and horizontal. Domain borders and the circular bowl wall (when
   ``kind="bowl"``) enforce exact zero normal flux.
5. **Wet/dry contact line and capillary pinning**: To prevent unphysical
   microscopic numerical wetting across dry cells, advance onto a dry cell is
   gated by a local contact-line pinning depth ``pinning_depth[row, col]``
   (representing capillary / contact-angle resistance). Once a cell wets past
   a transition depth, interior wet-to-wet faces level purely by hydrostatic
   head difference. On flat surfaces, mild deterministic spatial variation in
   the contact-line threshold plus local wet-neighborhood curvature cohesion
   produces a cohesive, irregular-edged persistent pool; inside a bowl, the
   free surface levels flat.
6. **Machine-precision volume conservation**: Every inter-cell transfer is
   computed once per undirected active cell pair and applied antisymmetrically
   (``-dh`` on donor, ``+dh`` on receiver) with a conservative per-cell outgoing
   limiter guaranteeing non-negative depth without clamping or volume creation.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np


class Layer:
    """Mass-conserving 2D continuum thin liquid layer on a horizontal surface.

    Grid convention:
        * ``self.x``: 1D ``float64`` array of shape ``(nx,)``, x-coordinates of
          cell centers in meters.
        * ``self.y``: 1D ``float64`` array of shape ``(ny,)``, y-coordinates of
          cell centers in meters.
        * ``self.h``: 2D ``float64`` array of shape ``(ny, nx)`` indexed as
          ``[row, col] == [iy, ix]``, storing cell-averaged liquid film depth
          in meters.
        * ``self.active``: 2D ``bool`` array of shape ``(ny, nx)`` marking
          active fluid cells (all ``True`` for ``kind="plane"``, circular
          interior for ``kind="bowl"``).
    """

    # Isotropic 9-point (8-neighbor) finite-volume weights eliminate Cartesian
    # diamond/axis bias: sum_card (2/3) + sum_diag (1/6) gives O(dx^4) rotational
    # isotropy for the discrete Laplacian while keeping pairwise conservation.
    _CARDINAL_WEIGHT: float = 2.0 / 3.0
    _DIAGONAL_WEIGHT: float = 1.0 / 6.0
    _SQRT2: float = math.sqrt(2.0)

    def __init__(
        self,
        xmin: float,
        xmax: float,
        ymin: float,
        ymax: float,
        dx: float,
        kind: str = "plane",
        radius: Optional[float] = None,
        *,
        gravity: float = 9.81,
        kinematic_viscosity: float = 2.0e-6,
        linear_drag: float = 2.5,
        quadratic_drag: float = 0.5,
        max_diffusivity: float = 0.02,
        contact_line_threshold: Optional[float] = None,
        threshold_variation: Optional[float] = None,
        capillary_cohesion: Optional[float] = None,
        wet_transition_fraction: float = 0.35,
        cfl_number: float = 0.25,
        variation_seed: int = 0,
    ) -> None:
        """Initialize a horizontal thin-film spreading domain.

        Parameters
        ----------
        xmin, xmax, ymin, ymax : float
            World-space domain bounds in meters (``xmax > xmin``,
            ``ymax > ymin``).
        dx : float
            Square cell side length in meters (typically ``0.0025`` to
            ``0.004`` m for a ~0.5 m workspace).
        kind : {"plane", "bowl"}, default "plane"
            Surface geometry. ``"plane"`` uses all cells; ``"bowl"`` masks
            active cells to a circle of ``radius`` centered at the domain
            midpoint with zero flux across the bowl wall.
        radius : float, optional
            Circular bowl radius in meters. Required and must be positive when
            ``kind="bowl"``; ignored when ``kind="plane"``.
        gravity : float, default 9.81
            Gravitational acceleration in m/s^2.
        kinematic_viscosity : float, default 2.0e-6
            Liquid kinematic viscosity in m^2/s (milk at room temperature is
            ~2e-6 m^2/s).
        linear_drag : float, default 2.5
            Overdamped linear inertial/bottom relaxation rate in 1/s.
        quadratic_drag : float, default 0.5
            Dimensionless quadratic bottom/inertial drag coefficient.
        max_diffusivity : float, default 0.02
            Smooth upper diffusivity ceiling in m^2/s for explicit stability in
            deeper pools (e.g., bowls).
        contact_line_threshold : float, optional
            Nominal advancing contact-line pinning depth in meters. Defaults to
            ``0.0020`` m (2.0 mm, matching milk's capillary length on a flat
            table/floor) for ``"plane"`` and ``0.00015`` m for ``"bowl"``.
        threshold_variation : float, optional
            Relative amplitude (in ``[0, 0.5)``) of mild deterministic spatial
            variation in the contact-line threshold. Defaults to ``0.18`` on
            ``"plane"`` and ``0.0`` on ``"bowl"``.
        capillary_cohesion : float, optional
            Strength of local wet-neighborhood curvature modulation at the
            contact line, suppressing spiky tendrils and filling concave bays.
            Defaults to ``0.35`` on ``"plane"`` and ``0.0`` on ``"bowl"``.
        wet_transition_fraction : float, default 0.35
            Fraction of the minimum contact-line threshold above which a cell
            behaves as an interior wet cell with pure hydrostatic leveling.
        cfl_number : float, default 0.25
            Explicit diffusive CFL factor (must lie in ``(0, 0.30]`` for
            discrete monotonicity on the isotropic 9-point stencil).
        variation_seed : int, default 0
            Deterministic RNG seed for the smooth world-space threshold field.
        """
        xmin = float(xmin)
        xmax = float(xmax)
        ymin = float(ymin)
        ymax = float(ymax)
        dx = float(dx)

        if not (xmax > xmin and ymax > ymin):
            raise ValueError("Domain bounds must satisfy xmax > xmin and ymax > ymin.")
        if dx <= 0.0 or not math.isfinite(dx):
            raise ValueError("Cell spacing dx must be a positive finite number.")
        if kind not in ("plane", "bowl"):
            raise ValueError(f"Unsupported kind {kind!r}; expected 'plane' or 'bowl'.")
        if gravity < 0.0 or kinematic_viscosity < 0.0 or linear_drag < 0.0 or quadratic_drag < 0.0:
            raise ValueError("Physical parameters must be non-negative.")
        if max_diffusivity <= 0.0:
            raise ValueError("max_diffusivity must be strictly positive.")
        if not (0.0 < cfl_number <= 0.30):
            raise ValueError("cfl_number must lie in (0, 0.30] for 9-point monotonicity.")
        if not (0.0 < wet_transition_fraction <= 1.0):
            raise ValueError("wet_transition_fraction must lie in (0, 1].")

        self.xmin: float = xmin
        self.xmax: float = xmax
        self.ymin: float = ymin
        self.ymax: float = ymax
        self.dx: float = dx
        self.cell_area: float = dx * dx
        self._inv_dx2: float = 1.0 / self.cell_area
        self._diag_dist: float = self._SQRT2 * dx

        self.kind: str = kind
        self.center_x: float = 0.5 * (xmin + xmax)
        self.center_y: float = 0.5 * (ymin + ymax)

        # Build regularly spaced square cells centered symmetrically on the domain midpoint.
        nx = max(1, int(round((xmax - xmin) / dx)))
        ny = max(1, int(round((ymax - ymin) / dx)))
        self.x: np.ndarray = self.center_x + (np.arange(nx, dtype=np.float64) - 0.5 * (nx - 1)) * dx
        self.y: np.ndarray = self.center_y + (np.arange(ny, dtype=np.float64) - 0.5 * (ny - 1)) * dx
        self.h: np.ndarray = np.zeros((ny, nx), dtype=np.float64)

        grid_x, grid_y = np.meshgrid(self.x, self.y, indexing="xy")

        if kind == "bowl":
            if radius is None or float(radius) <= 0.0 or not math.isfinite(float(radius)):
                raise ValueError("A positive finite radius is required when kind='bowl'.")
            self.radius: Optional[float] = float(radius)
            dist2 = (grid_x - self.center_x) ** 2 + (grid_y - self.center_y) ** 2
            self.active: np.ndarray = dist2 <= (self.radius * self.radius)
            if not np.any(self.active):
                raise ValueError("Bowl radius is too small to enclose any cell center.")
        else:
            self.radius = None
            self.active = np.ones((ny, nx), dtype=bool)

        # Precompute active undirected edge masks for zero-flux walls.
        self._active_e: np.ndarray = self.active[:, :-1] & self.active[:, 1:]
        self._active_s: np.ndarray = self.active[:-1, :] & self.active[1:, :]
        self._active_se: np.ndarray = self.active[:-1, :-1] & self.active[1:, 1:]
        self._active_sw: np.ndarray = self.active[:-1, 1:] & self.active[1:, :-1]

        # Precompute active neighbor weight sum for curvature cohesion normalization.
        neighbor_weight = np.zeros((ny, nx), dtype=np.float64)
        neighbor_weight[:, :-1] += (1.0 / 6.0) * self._active_e
        neighbor_weight[:, 1:] += (1.0 / 6.0) * self._active_e
        neighbor_weight[:-1, :] += (1.0 / 6.0) * self._active_s
        neighbor_weight[1:, :] += (1.0 / 6.0) * self._active_s
        neighbor_weight[:-1, :-1] += (1.0 / 12.0) * self._active_se
        neighbor_weight[1:, 1:] += (1.0 / 12.0) * self._active_se
        neighbor_weight[:-1, 1:] += (1.0 / 12.0) * self._active_sw
        neighbor_weight[1:, :-1] += (1.0 / 12.0) * self._active_sw
        self._inv_neighbor_weight: np.ndarray = np.where(
            neighbor_weight > 0.0, 1.0 / np.where(neighbor_weight > 0.0, neighbor_weight, 1.0), 0.0
        )

        # Physical transport parameters.
        self.gravity: float = float(gravity)
        self.kinematic_viscosity: float = float(kinematic_viscosity)
        self.linear_drag: float = float(linear_drag)
        self.quadratic_drag: float = float(quadratic_drag)
        self.max_diffusivity: float = float(max_diffusivity)
        self.cfl_number: float = float(cfl_number)
        self.wet_transition_fraction: float = float(wet_transition_fraction)
        self.variation_seed: int = int(variation_seed)

        # Surface-specific defaults for contact-line physics.
        if contact_line_threshold is None:
            base_threshold = 0.0020 if kind == "plane" else 0.00015
        else:
            base_threshold = float(contact_line_threshold)
            if base_threshold < 0.0:
                raise ValueError("contact_line_threshold must be non-negative.")

        if threshold_variation is None:
            variation_amp = 0.18 if kind == "plane" else 0.0
        else:
            variation_amp = float(threshold_variation)
            if not (0.0 <= variation_amp < 0.5):
                raise ValueError("threshold_variation must lie in [0.0, 0.5).")

        if capillary_cohesion is None:
            cohesion = 0.35 if kind == "plane" else 0.0
        else:
            cohesion = float(capillary_cohesion)
            if cohesion < 0.0:
                raise ValueError("capillary_cohesion must be non-negative.")

        self.contact_line_threshold: float = base_threshold
        self.threshold_variation: float = variation_amp
        self.capillary_cohesion: float = cohesion

        # Construct per-cell contact-line pinning depth field in meters.
        if base_threshold > 0.0 and variation_amp > 0.0:
            spatial_field = self._build_spatial_variation(grid_x, grid_y, self.variation_seed)
            pinning = base_threshold * (1.0 + variation_amp * spatial_field)
        else:
            pinning = np.full((ny, nx), base_threshold, dtype=np.float64)

        self.pinning_depth: np.ndarray = np.where(self.active, pinning, 0.0)
        min_active_pinning = float(np.min(self.pinning_depth[self.active]))
        self._wet_transition_depth: float = self.wet_transition_fraction * min_active_pinning
        self.last_substeps: int = 0

    @staticmethod
    def _build_spatial_variation(
        grid_x: np.ndarray, grid_y: np.ndarray, seed: int
    ) -> np.ndarray:
        """Build a smooth, resolution-independent, deterministic field in (-1, 1).

        Uses a fixed superposition of 2D cosine modes with centimeter-scale
        wavelengths (0.06 m to 0.22 m) so flat-surface puddles develop natural,
        cohesive irregular lobes independent of grid spacing ``dx``.
        """
        rng = np.random.default_rng(seed)
        num_modes = 16
        wavelengths = np.geomspace(0.06, 0.22, num_modes)
        angles = rng.uniform(0.0, math.pi, size=num_modes)
        phases = rng.uniform(0.0, 2.0 * math.pi, size=num_modes)
        # Weight longer wavelengths more strongly for smooth macro-lobes.
        amplitudes = wavelengths ** 0.75

        field = np.zeros_like(grid_x, dtype=np.float64)
        for amp, wl, angle, phase in zip(amplitudes, wavelengths, angles, phases):
            wavenumber = (2.0 * math.pi) / wl
            kx = wavenumber * math.cos(angle)
            ky = wavenumber * math.sin(angle)
            field += amp * np.cos(kx * grid_x + ky * grid_y + phase)

        rms = math.sqrt(0.5 * float(np.sum(amplitudes * amplitudes)))
        return np.tanh(field / (1.5 * rms))

    def volume(self) -> float:
        """Return total liquid volume currently stored in the layer (m^3)."""
        return float(np.sum(self.h) * self.cell_area)

    def deposit(self, x: float, y: float, volume: float, radius: float) -> float:
        """Deposit liquid with a normalized circular/Gaussian footprint.

        The footprint is evaluated on the virtual infinite square grid of
        spacing ``self.dx``, normalized to unit sum across the full circular
        disk of radius ``radius``, and clipped to ``self.active`` cells without
        re-normalizing. Consequently:
            * Deposits fully inside the active surface accept ``volume`` to
              machine precision.
            * Deposits straddling a bowl rim or domain boundary accept only the
              in-bounds active fraction and never create volume.
            * Deposits completely outside the active surface return ``0.0``.
            * Narrow jets (``radius < dx`` or even ``radius == 0``) still
              register cleanly on the cell(s) containing ``(x, y)``.

        Parameters
        ----------
        x, y : float
            Impact center coordinates in world meters.
        volume : float
            Requested liquid volume to deposit in m^3 (must be >= 0).
        radius : float
            Circular footprint radius in meters (must be >= 0).

        Returns
        -------
        float
            Accepted volume actually added to ``self.h`` in m^3, guaranteed to
            satisfy ``0.0 <= accepted <= volume``.
        """
        x = float(x)
        y = float(y)
        volume = float(volume)
        radius = float(radius)

        if volume < 0.0 or not math.isfinite(volume):
            raise ValueError("Deposit volume must be a finite non-negative number.")
        if radius < 0.0 or not math.isfinite(radius):
            raise ValueError("Deposit radius must be a finite non-negative number.")
        if volume == 0.0:
            return 0.0

        ny, nx = self.h.shape
        dx = self.dx
        half = 0.5 * dx
        x0 = float(self.x[0])
        y0 = float(self.y[0])

        ix_min = int(math.floor((x - radius - half - x0) / dx))
        ix_max = int(math.ceil((x + radius + half - x0) / dx))
        iy_min = int(math.floor((y - radius - half - y0) / dx))
        iy_max = int(math.ceil((y + radius + half - y0) / dx))

        # Fast reject when footprint cannot intersect the grid at all.
        if ix_max < 0 or ix_min >= nx or iy_max < 0 or iy_min >= ny:
            return 0.0

        vx = x0 + np.arange(ix_min, ix_max + 1, dtype=np.float64) * dx
        vy = y0 + np.arange(iy_min, iy_max + 1, dtype=np.float64) * dx

        ddx = vx[None, :] - x
        ddy = vy[:, None] - y
        dx_box = np.maximum(np.abs(ddx) - half, 0.0)
        dy_box = np.maximum(np.abs(ddy) - half, 0.0)
        inside_disk = (dx_box * dx_box + dy_box * dy_box) <= (radius * radius)

        sigma = max(0.5 * radius, 0.35 * dx)
        inv_2sigma2 = 0.5 / (sigma * sigma)
        weights = np.where(inside_disk, np.exp(-(ddx * ddx + ddy * ddy) * inv_2sigma2), 0.0)
        total_weight = float(np.sum(weights))
        if total_weight <= 0.0:
            return 0.0
        weights /= total_weight

        ox0 = max(0, ix_min)
        ox1 = min(nx - 1, ix_max)
        oy0 = max(0, iy_min)
        oy1 = min(ny - 1, iy_max)
        if ox0 > ox1 or oy0 > oy1:
            return 0.0

        w_in = weights[oy0 - iy_min : oy1 - iy_min + 1, ox0 - ix_min : ox1 - ix_min + 1]
        act_in = self.active[oy0 : oy1 + 1, ox0 : ox1 + 1]
        w_active = np.where(act_in, w_in, 0.0)
        active_sum = float(np.sum(w_active))
        if active_sum <= 0.0:
            return 0.0

        # Guard against rare 1-ULP sum > 1.0 so deposit never creates volume.
        if active_sum > 1.0:
            w_active = w_active / active_sum

        dh = (volume / self.cell_area) * w_active
        self.h[oy0 : oy1 + 1, ox0 : ox1 + 1] += dh
        return float(np.sum(dh) * self.cell_area)

    def _diffusivity_upper_bound(self, h_max: float) -> float:
        """Upper bound on face diffusivity across the grid for CFL substepping."""
        if h_max <= 0.0 or self.gravity <= 0.0:
            return 0.0
        h2 = h_max * h_max
        denom = 3.0 * self.kinematic_viscosity + self.linear_drag * h2
        if denom <= 0.0:
            return self.max_diffusivity
        d_zero_slope = (self.gravity * h2 * h_max) / denom
        return (d_zero_slope * self.max_diffusivity) / (d_zero_slope + self.max_diffusivity)

    def _compute_receiver_resistance(self, h: np.ndarray) -> np.ndarray:
        """Compute per-cell effective resistance head when acting as receiver.

        * Dry cell (``h == 0``): resistance equals the curvature-adjusted
          contact-line threshold ``theta_eff``, blocking advance unless the
          donor depth exceeds ``theta_eff``.
        * Interior wet cell (``h >= wet_transition_depth``): resistance equals
          ``h`` itself, yielding pure hydrostatic leveling with no interior
          bumps or dimples.
        """
        if self._wet_transition_depth <= 0.0:
            return h

        wetness = np.clip(h / self._wet_transition_depth, 0.0, 1.0)

        if self.capillary_cohesion > 0.0:
            w_sum = np.zeros_like(h)
            w_e_a = wetness[:, :-1] * self._active_e
            w_e_b = wetness[:, 1:] * self._active_e
            w_sum[:, :-1] += (1.0 / 6.0) * w_e_b
            w_sum[:, 1:] += (1.0 / 6.0) * w_e_a

            w_s_a = wetness[:-1, :] * self._active_s
            w_s_b = wetness[1:, :] * self._active_s
            w_sum[:-1, :] += (1.0 / 6.0) * w_s_b
            w_sum[1:, :] += (1.0 / 6.0) * w_s_a

            w_se_a = wetness[:-1, :-1] * self._active_se
            w_se_b = wetness[1:, 1:] * self._active_se
            w_sum[:-1, :-1] += (1.0 / 12.0) * w_se_b
            w_sum[1:, 1:] += (1.0 / 12.0) * w_se_a

            w_sw_a = wetness[:-1, 1:] * self._active_sw
            w_sw_b = wetness[1:, :-1] * self._active_sw
            w_sum[:-1, 1:] += (1.0 / 12.0) * w_sw_b
            w_sum[1:, :-1] += (1.0 / 12.0) * w_sw_a

            w_avg = w_sum * self._inv_neighbor_weight
            # Straight front has w_avg ~= 1/3; convex tips (< 1/3) face higher
            # resistance while concave notches (> 1/3) fill preferentially.
            cohesion_factor = np.clip(
                1.0 + self.capillary_cohesion * ((1.0 / 3.0) - w_avg), 0.75, 1.25
            )
            theta_eff = self.pinning_depth * cohesion_factor
        else:
            theta_eff = self.pinning_depth

        return (1.0 - wetness) * theta_eff + wetness * h

    def _edge_depth_rate(
        self,
        h_a: np.ndarray,
        h_b: np.ndarray,
        r_a: np.ndarray,
        r_b: np.ndarray,
        active_pair: np.ndarray,
        dist: float,
        geom_weight: float,
    ) -> Optional[np.ndarray]:
        """Compute signed depth-transfer rate (m/s) across an edge family.

        Positive values transfer depth from cell ``a`` to cell ``b``; negative
        values transfer from ``b`` to ``a``. Returns ``None`` if every face in
        this family has zero driving head.
        """
        if h_a.size == 0:
            return None

        a_is_hi = h_a >= h_b
        h_hi = np.where(a_is_hi, h_a, h_b)
        r_lo = np.where(a_is_hi, r_b, r_a)

        d_eta = h_hi - r_lo
        mask = active_pair & (d_eta > 0.0) & (h_hi > 0.0)
        if not np.any(mask):
            return None

        d_eta = np.where(mask, d_eta, 0.0)
        h_f = 0.5 * (h_a + h_b)
        slope = d_eta / dist

        h_f2 = h_f * h_f
        h_f3 = h_f2 * h_f
        lin_term = 3.0 * self.kinematic_viscosity + self.linear_drag * h_f2
        disc = lin_term * lin_term + (4.0 * self.quadratic_drag * self.gravity) * h_f3 * slope
        denom = lin_term + np.sqrt(disc)
        safe_denom = np.where(denom > 0.0, denom, 1.0)

        d_phys = np.where(mask & (denom > 0.0), (2.0 * self.gravity * h_f3) / safe_denom, 0.0)
        d_eff = (d_phys * self.max_diffusivity) / (d_phys + self.max_diffusivity)
        mag_rate = (geom_weight * self._inv_dx2) * d_eff * d_eta
        return np.where(a_is_hi, mag_rate, -mag_rate)

    def step(self, dt: float) -> None:
        """Advance the thin liquid layer forward in time by ``dt`` seconds.

        Uses adaptive explicit CFL substepping over the isotropic 8-neighbor
        finite-volume stencil with a conservative per-cell outgoing transfer
        limiter. Maintains non-negative depth and machine-precision volume
        conservation across every substep.

        Parameters
        ----------
        dt : float
            Time increment in seconds (must be finite and >= 0).
        """
        dt = float(dt)
        if dt < 0.0 or not math.isfinite(dt):
            raise ValueError("Time step dt must be a finite non-negative number.")
        self.last_substeps = 0
        if dt == 0.0:
            return

        remaining = dt
        eps_time = 1e-15 * dt
        substeps = 0

        while remaining > eps_time:
            h = self.h
            h_max = float(np.max(h))
            if h_max <= 0.0:
                break

            d_bound = self._diffusivity_upper_bound(h_max)
            if d_bound <= 0.0:
                break

            dt_cfl = (self.cfl_number * self.cell_area) / d_bound
            dt_sub = remaining if remaining <= dt_cfl else dt_cfl

            resist = self._compute_receiver_resistance(h)

            rate_e = self._edge_depth_rate(
                h[:, :-1],
                h[:, 1:],
                resist[:, :-1],
                resist[:, 1:],
                self._active_e,
                self.dx,
                self._CARDINAL_WEIGHT,
            )
            rate_s = self._edge_depth_rate(
                h[:-1, :],
                h[1:, :],
                resist[:-1, :],
                resist[1:, :],
                self._active_s,
                self.dx,
                self._CARDINAL_WEIGHT,
            )
            rate_se = self._edge_depth_rate(
                h[:-1, :-1],
                h[1:, 1:],
                resist[:-1, :-1],
                resist[1:, 1:],
                self._active_se,
                self._diag_dist,
                self._DIAGONAL_WEIGHT,
            )
            rate_sw = self._edge_depth_rate(
                h[:-1, 1:],
                h[1:, :-1],
                resist[:-1, 1:],
                resist[1:, :-1],
                self._active_sw,
                self._diag_dist,
                self._DIAGONAL_WEIGHT,
            )

            if rate_e is None and rate_s is None and rate_se is None and rate_sw is None:
                # All faces are pinned or leveled; layer is at static equilibrium.
                break

            dh_e = None if rate_e is None else dt_sub * rate_e
            dh_s = None if rate_s is None else dt_sub * rate_s
            dh_se = None if rate_se is None else dt_sub * rate_se
            dh_sw = None if rate_sw is None else dt_sub * rate_sw

            # Conservative per-cell outgoing transfer bound guarantees h >= 0
            # strictly without clamping or breaking antisymmetric mass balance.
            outflow = np.zeros_like(h)
            if dh_e is not None:
                outflow[:, :-1] += np.maximum(dh_e, 0.0)
                outflow[:, 1:] += np.maximum(-dh_e, 0.0)
            if dh_s is not None:
                outflow[:-1, :] += np.maximum(dh_s, 0.0)
                outflow[1:, :] += np.maximum(-dh_s, 0.0)
            if dh_se is not None:
                outflow[:-1, :-1] += np.maximum(dh_se, 0.0)
                outflow[1:, 1:] += np.maximum(-dh_se, 0.0)
            if dh_sw is not None:
                outflow[:-1, 1:] += np.maximum(dh_sw, 0.0)
                outflow[1:, :-1] += np.maximum(-dh_sw, 0.0)

            max_allowed = 0.95 * h
            need_limit = outflow > max_allowed
            if np.any(need_limit):
                scale = np.ones_like(h)
                scale[need_limit] = max_allowed[need_limit] / outflow[need_limit]
                if dh_e is not None:
                    dh_e *= np.where(dh_e >= 0.0, scale[:, :-1], scale[:, 1:])
                if dh_s is not None:
                    dh_s *= np.where(dh_s >= 0.0, scale[:-1, :], scale[1:, :])
                if dh_se is not None:
                    dh_se *= np.where(dh_se >= 0.0, scale[:-1, :-1], scale[1:, 1:])
                if dh_sw is not None:
                    dh_sw *= np.where(dh_sw >= 0.0, scale[:-1, 1:], scale[1:, :-1])

            delta_h = np.zeros_like(h)
            if dh_e is not None:
                delta_h[:, :-1] -= dh_e
                delta_h[:, 1:] += dh_e
            if dh_s is not None:
                delta_h[:-1, :] -= dh_s
                delta_h[1:, :] += dh_s
            if dh_se is not None:
                delta_h[:-1, :-1] -= dh_se
                delta_h[1:, 1:] += dh_se
            if dh_sw is not None:
                delta_h[:-1, 1:] -= dh_sw
                delta_h[1:, :-1] += dh_sw

            self.h += delta_h
            remaining -= dt_sub
            substeps += 1

        self.last_substeps = substeps


def _run_self_check() -> None:
    """Run in-memory verification for flat-table spill and circular bowl leveling."""
    pour_volume = 0.00015  # 150 mL
    pour_duration = 1.5    # seconds
    settle_duration = 1.5  # seconds
    dt = 0.05

    # 1. Flat table spill (0.5 m x 0.5 m, dx = 0.004 m) with moving pour jet.
    table = Layer(-0.25, 0.25, -0.25, 0.25, dx=0.004, kind="plane")
    deposited_table = 0.0
    n_pour = int(round(pour_duration / dt))
    for step_idx in range(n_pour):
        phase = (step_idx + 0.5) / n_pour
        jet_x = -0.02 + 0.04 * phase
        jet_y = 0.015 * math.sin(2.0 * math.pi * phase)
        deposited_table += table.deposit(jet_x, jet_y, pour_volume / n_pour, radius=0.012)
        table.step(dt)
    for _ in range(int(round(settle_duration / dt))):
        table.step(dt)

    wet_table = table.h > 0.0
    table_err = abs(table.volume() - deposited_table) / max(deposited_table, 1e-30)
    wet_depths_mm = table.h[wet_table] * 1e3
    grid_x, grid_y = np.meshgrid(table.x, table.y, indexing="xy")
    # Measure angular radius irregularity of the persistent flat pool.
    wx = grid_x[wet_table] - float(np.mean(grid_x[wet_table]))
    wy = grid_y[wet_table] - float(np.mean(grid_y[wet_table]))
    angles = np.arctan2(wy, wx)
    radii = np.hypot(wx, wy)
    sector_max_r = []
    for k in range(16):
        a0 = -math.pi + k * (2.0 * math.pi / 16.0)
        a1 = a0 + (2.0 * math.pi / 16.0)
        in_sec = (angles >= a0) & (angles < a1)
        if np.any(in_sec):
            sector_max_r.append(float(np.max(radii[in_sec])))

    assert table.h.min() >= 0.0, "Negative depth detected on plane."
    assert table_err < 1e-12, f"Plane volume conservation failed: rel_err={table_err:.3e}"
    assert np.sum(~wet_table) > 0, "Expected dry cells outside the contact line."

    # 2. Circular bowl (radius = 0.08 m) with off-center pour and rim-clipping check.
    bowl = Layer(-0.10, 0.10, -0.10, 0.10, dx=0.004, kind="bowl", radius=0.08)
    deposited_bowl = 0.0
    for _ in range(n_pour):
        deposited_bowl += bowl.deposit(0.035, -0.020, pour_volume / n_pour, radius=0.010)
        bowl.step(dt)
    # Test partial rim clipping (no volume creation) and exterior rejection.
    rim_req = 1e-6
    rim_acc = bowl.deposit(0.08, 0.0, rim_req, radius=0.012)
    assert 0.0 < rim_acc < rim_req, "Rim deposit should be partially clipped."
    deposited_bowl += rim_acc
    assert bowl.deposit(0.098, 0.0, 1e-6, radius=0.005) == 0.0, "Exterior deposit must return 0."

    for _ in range(int(round(settle_duration / dt))):
        bowl.step(dt)

    bowl_err = abs(bowl.volume() - deposited_bowl) / max(deposited_bowl, 1e-30)
    bowl_depths = bowl.h[bowl.active]
    bowl_flatness_mm = float(np.max(bowl_depths) - np.min(bowl_depths)) * 1e3

    assert bowl.h.min() >= 0.0, "Negative depth detected in bowl."
    assert np.all(bowl.h[~bowl.active] == 0.0), "Leakage across circular bowl wall."
    assert bowl_err < 1e-12, f"Bowl volume conservation failed: rel_err={bowl_err:.3e}"

    print(
        f"Plane: vol_rel_err={table_err:.2e}, dry_frac={float(np.mean(~wet_table)):.3f}, "
        f"pool_mean_mm={float(np.mean(wet_depths_mm)):.2f}, "
        f"rim_r_min_max_m=({min(sector_max_r):.3f}, {max(sector_max_r):.3f})"
    )
    print(
        f"Bowl:  vol_rel_err={bowl_err:.2e}, mean_mm={float(np.mean(bowl_depths))*1e3:.2f}, "
        f"max_minus_min_mm={bowl_flatness_mm:.4f}"
    )


if __name__ == "__main__":
    _run_self_check()
