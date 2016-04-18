import numba
import numpy as np


@numba.jit(nopython=True, nogil=True)
def f_soc_ij(x_ij, v_ij, r_ij, tau_0, f_max):
    r"""
    About
    -----
    Social interaction force between two agents `i` and `j`. [1]

    Params
    ------
    :param x_ij:
    :param v_ij:
    :param r_ij:
    :param tau_0: Max interaction range 2 - 4, aka interaction time horizon
    :param sight: Max distance between agents for interaction to occur
    :param f_max: Maximum magnitude of force. Forces greater than this are scaled to force max.
    :return: Vector of length 2 containing `x` and `y` components of force
             on agent i.

    References
    ----------
    [1] http://motion.cs.umn.edu/PowerLaw/
    """
    # Init output values.
    force = np.zeros(2)

    a = np.dot(v_ij, v_ij)
    b = - np.dot(x_ij, v_ij)
    c = np.dot(x_ij, x_ij) - r_ij ** 2
    d = b ** 2 - a * c

    # TODO: Explanation
    if (d < 0) or (- 0.001 < a < 0.001):
        return force

    d = np.sqrt(d)
    tau = (b - d) / a  # Time-to-collision
    tau_max = 999.0

    if tau < 0 or tau > tau_max:
        return force

    # Force is returned negative as repulsive force
    k = 1.5  # Constant for setting units for interaction force. Scale with mass
    m = 2.0  # Exponent in power law
    force -= k / (a * tau ** m) * np.exp(-tau / tau_0) * \
             (m / tau + 1 / tau_0) * (v_ij - (v_ij * b + x_ij * a) / d)

    # mag = np.sqrt(np.dot(force, force))
    mag = np.hypot(force[0], force[1])
    if mag > f_max:
        # Scales magnitude of force to force max
        force *= f_max / mag

    return force


@numba.jit(nopython=True, nogil=True)
def f_c_ij(h_ij, n_ij, v_ij, t_ij, mu, kappa):
    force = np.zeros(2)
    force += h_ij * (mu * n_ij - kappa * np.dot(v_ij, t_ij) * t_ij)
    return force


@numba.jit(nopython=True, nogil=True)
def f_ij(i, x, v, r, tau_0, sight, f_max, mu, kappa):
    """

    :param i:
    :param x:
    :param v:
    :param r:
    :param tau_0:
    :param sight:
    :param f_max:
    :param mu:
    :param kappa:
    :return:
    """
    rot270 = np.array(((0, 1), (-1, 0)), dtype=np.float64)
    force = np.zeros(2)

    for j in range(len(x)):
        if i == j:
            continue
        x_ij = x[i] - x[j]  # position
        v_ij = v[i] - v[j]  # velocity
        r_ij = r[i] + r[j]  # radius
        d_ij = np.hypot(x_ij[0], x_ij[1])  # Distance between agents

        # No force if another agent is not in range of sight
        if d_ij < sight:
            force += f_soc_ij(x_ij, v_ij, r_ij, tau_0, f_max)

        # Agents are overlapping. Friction force.
        h_ij = r_ij - d_ij
        if h_ij > 0:
            n_ij = x_ij / d_ij
            t_ij = np.dot(rot270, n_ij)
            force += f_c_ij(h_ij, n_ij, v_ij, t_ij, mu, kappa)
    return force
