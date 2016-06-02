import numba
from numpy import dot, zeros_like, random, cos, pi, sin
from numpy.core.umath import exp, sqrt, isnan


@numba.jit(nopython=True, nogil=True)
def f_random_fluctuation(constant, agent):
    for i in range(agent.size):
        angle = random.uniform(0, 2 * pi)
        magnitude = random.uniform(0, constant.f_random_fluctuation_max)
        agent.force[i][0] += magnitude * cos(angle)
        agent.force[i][1] += magnitude * sin(angle)


@numba.jit(nopython=True, nogil=True)
def f_adjust(constant, agent):
    force = (agent.mass / constant.tau_adj) * \
            (agent.goal_velocity * agent.target_direction - agent.velocity)
    agent.force += force
    # agent.force_adjust += force


@numba.jit(nopython=True, nogil=True)
def f_soc_iw(h_iw, n_iw, a, b):
    return exp(h_iw / b) * a * n_iw


@numba.jit(nopython=True, nogil=True)
def f_c_iw(v_iw, t_iw, n_iw, h_iw, mu, kappa):
    return h_iw * (mu * n_iw - kappa * dot(v_iw, t_iw) * t_iw)


@numba.jit(nopython=True, nogil=True)
def f_c_ij(h_ij, n_ij, v_ij, t_ij, mu, kappa):
    return h_ij * (mu * n_ij - kappa * dot(v_ij, t_ij) * t_ij)


@numba.jit(nopython=True, nogil=True)
def f_soc_ij(x_ij, v_ij, r_ij, k, tau_0):
    """
    About
    -----
    Social interaction force between two agents `i` and `j`. [1]

    References
    ----------
    [1] http://motion.cs.umn.edu/PowerLaw/
    """
    force = zeros_like(x_ij)

    a = dot(v_ij, v_ij)
    b = - dot(x_ij, v_ij)
    c = dot(x_ij, x_ij) - r_ij ** 2
    d = sqrt(b ** 2 - a * c)

    # Avoid zero division zero divisions.
    # No interaction if tau cannot be defined.
    if isnan(d) or d < 1.49e-08 or abs(a) < 1.49e-08:
        return force

    tau = (b - d) / a  # Time-to-collision
    tau_max = 999.0

    if tau <= 0 or tau > tau_max:
        return force

    # Force is returned negative as repulsive force
    m = 2.0  # Exponent in power law
    force -= k / (a * tau ** m) * exp(-tau / tau_0) * (m / tau + 1 / tau_0) * \
             (v_ij - (v_ij * b + x_ij * a) / d)

    return force